"""Android ADB SMS inbox OTP retrieval and regex extraction utilities."""

from __future__ import annotations

import re
import subprocess
import threading
import time

from utils.logger import get_logger

logger = get_logger("otp_helper")

_OTP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:otp|one[\s-]*time[\s-]*password|verification[\s-]*code|auth(?:entication)?[\s-]*code)"
        r"\b[^0-9\n]{0,45}?\b(?:is|:|-)?\s*(\d{4,8})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{4,8})\s+(?:is\s+(?:the|your)\s+)?"
        r"(?:otp|one[\s-]*time[\s-]*password|verification[\s-]*code)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:code|pin|passcode)\s*(?:is|:|-)\s*(\d{4,8})\b", re.IGNORECASE),
)

_OTP_CONTEXT_HINT_RE = re.compile(
    r"\b(?:otp|one[\s-]*time|password|verification|txn|transaction|payment)\b",
    re.IGNORECASE,
)
_STANDALONE_DIGITS_RE = re.compile(r"\b(\d{4,8})\b")

_ROW_SPLIT_RE = re.compile(r"(?=^Row:\s*\d+\s+)", re.MULTILINE)
_ORDERED_ROW_RE = re.compile(
    r"^Row:\s*\d+\s+_id=([^,]*),\s*address=([^,]*),\s*date=(\d+),\s*body=(.*)$",
    re.DOTALL,
)


def extract_otp_from_text(message_body: str) -> str | None:
    """Extract a 4-to-8 digit OTP from an Indian bank or payment gateway SMS body."""
    if not message_body:
        return None

    for pattern in _OTP_PATTERNS:
        match = pattern.search(message_body)
        if match:
            return match.group(1)

    if _OTP_CONTEXT_HINT_RE.search(message_body):
        fallback = _STANDALONE_DIGITS_RE.search(message_body)
        if fallback:
            return fallback.group(1)

    return None


def get_device_timestamp_ms(udid: str) -> int:
    """Query the Android device epoch time in milliseconds to eliminate host clock skew."""
    if not udid.strip():
        return int(time.time() * 1000)

    try:
        result = subprocess.run(
            ["adb", "-s", udid.strip(), "shell", "date", "+%s"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        raw_epoch = result.stdout.strip()
        if result.returncode == 0 and raw_epoch.isdigit():
            device_ms = int(raw_epoch) * 1000
            logger.info("Resolved Android device clock timestamp: %d ms", device_ms)
            return device_ms
    except (subprocess.SubprocessError, ValueError) as exc:
        logger.warning("Could not query Android device clock (%s); falling back to host clock", exc)

    return int(time.time() * 1000)


def parse_sms_inbox_rows(raw_output: str) -> list[dict[str, str]]:
    """Parse Android 'content query' SMS inbox rows into structured dictionaries."""
    rows: list[dict[str, str]] = []
    for chunk in _ROW_SPLIT_RE.split(raw_output.strip()):
        record = chunk.strip()
        if not record.startswith("Row:"):
            continue

        ordered_match = _ORDERED_ROW_RE.match(record)
        if ordered_match:
            rows.append(
                {
                    "_id": ordered_match.group(1).strip(),
                    "address": ordered_match.group(2).strip(),
                    "date": ordered_match.group(3).strip(),
                    "body": ordered_match.group(4).strip(),
                }
            )
            continue

        # Fallback parser if an Android build returns projected columns in a different order.
        id_match = re.search(r"\b_id=([^,\n]+)", record)
        addr_match = re.search(r"\baddress=([^,\n]*)", record)
        date_match = re.search(r"\bdate=(\d+)", record)
        body_match = re.search(r"\bbody=(.*)$", record, re.DOTALL)
        if date_match and body_match:
            rows.append(
                {
                    "_id": id_match.group(1).strip() if id_match else "",
                    "address": addr_match.group(1).strip() if addr_match else "",
                    "date": date_match.group(1).strip(),
                    "body": body_match.group(1).strip(),
                }
            )
    return rows


def fetch_latest_sms_otp(
    udid: str,
    min_timestamp_ms: int,
    sender_filter: str | None = None,
    timeout: float = 30.0,
    poll_interval: float = 2.0,
) -> str:
    """Poll Android SMS inbox via ADB for an OTP message arriving at or after min_timestamp_ms."""
    if not udid.strip():
        raise ValueError("ANDROID_UDID is required to query SMS inbox via ADB.")

    sender_regex = re.compile(sender_filter, re.IGNORECASE) if sender_filter else None
    cmd = [
        "adb",
        "-s",
        udid.strip(),
        "shell",
        "content",
        "query",
        "--uri",
        "content://sms/inbox",
        "--projection",
        "_id:address:date:body",
    ]

    deadline = time.monotonic() + timeout
    wait_event = threading.Event()
    last_error = ""
    last_row_count = 0

    logger.info(
        "Polling ADB SMS inbox on device=%s (min_timestamp_ms=%d, timeout=%.1fs)",
        udid,
        min_timestamp_ms,
        timeout,
    )

    while True:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if result.returncode != 0:
            last_error = (result.stderr or result.stdout or "").strip()
        else:
            rows = parse_sms_inbox_rows(result.stdout)
            last_row_count = len(rows)

            matching_rows: list[tuple[int, dict[str, str]]] = []
            for row in rows:
                try:
                    row_date_ms = int(row.get("date", "0"))
                except ValueError:
                    continue
                if row_date_ms < min_timestamp_ms:
                    continue

                address = row.get("address", "")
                if sender_regex is not None and not sender_regex.search(address):
                    continue

                matching_rows.append((row_date_ms, row))

            matching_rows.sort(key=lambda item: item[0], reverse=True)
            for row_date_ms, row in matching_rows:
                otp = extract_otp_from_text(row.get("body", ""))
                if otp:
                    logger.info(
                        "Extracted masked OTP (digits=%d) from sender=%s at date=%d",
                        len(otp),
                        row.get("address", "unknown"),
                        row_date_ms,
                    )
                    return otp

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        wait_event.wait(min(poll_interval, remaining))

    raise TimeoutError(
        f"Timed out after {timeout:.1f}s waiting for SMS OTP on device={udid!r} "
        f"(min_timestamp_ms={min_timestamp_ms}, sender_filter={sender_filter!r}, "
        f"rows_seen={last_row_count}, last_error={last_error!r})"
    )
