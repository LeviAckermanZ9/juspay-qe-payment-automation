"""Centralized configuration loader backed by environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env if present; environment variables already set in the shell take precedence.
load_dotenv(dotenv_path=ENV_FILE, override=False)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Convert common truthy/falsy strings into a boolean."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    """Safely parse an integer environment value with a fallback default."""
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"Expected integer configuration value, got {value!r}") from exc


@dataclass
class Settings:
    """Typed application settings for Web, Mobile, and Payment test suites."""

    # Web configuration
    razorpay_demo_url: str = "https://razorpay.com/demo/"
    web_base_url: str = "https://razorpay.com/demo/"
    sandbox_base_url: str = "https://razorpay.com/demo/"
    browser: str = "chromium"
    browser_channel: str = ""
    headless: bool = False
    default_timeout_ms: int = 15000

    # Payment and checkout test data (public test defaults for sandbox runs)
    test_card_number: str = "4111111111111111"
    test_card_expiry: str = "12/28"
    test_card_cvv: str = "123"
    test_card_holder: str = "Test User"
    test_invalid_card_number: str = "4111111111111112"
    test_upi_id: str = "success@razorpay"
    test_netbanking_bank: str = "HDFC"
    test_otp_code: str = "123456"
    sandbox_test_otp: str = "123456"
    otp_poll_timeout_seconds: int = 30
    enable_live_otp_e2e: bool = False
    test_recipient_name: str = "QA Test User"
    test_recipient_email: str = "qa.test@example.com"
    test_recipient_mobile: str = "9820098200"
    test_sender_name: str = "QA Automation"

    # Mobile / Appium configuration
    appium_server_url: str = "http://127.0.0.1:4723"
    android_udid: str = ""
    android_platform_version: str = "14.0"
    app_package: str = "in.swiggy.android"
    app_activity: str = ""
    app_wait_activity: str = "in.swiggy.android.*"
    apk_path: str = ""
    no_reset: bool = True
    auto_grant_permissions: bool = True

    @property
    def default_timeout_sec(self) -> float:
        """Return default timeout in seconds for WebDriverWait."""
        return self.default_timeout_ms / 1000.0

    @classmethod
    def from_env(cls) -> Settings:
        """Construct a Settings instance from current environment variables."""
        load_dotenv(dotenv_path=ENV_FILE, override=False)
        razorpay_url = os.getenv("RAZORPAY_DEMO_URL", "https://razorpay.com/demo/").strip()

        return cls(
            razorpay_demo_url=razorpay_url,
            web_base_url=os.getenv("WEB_BASE_URL", razorpay_url).strip(),
            sandbox_base_url=os.getenv("SANDBOX_BASE_URL", razorpay_url).strip(),
            browser=os.getenv("BROWSER", "chromium").strip().lower(),
            browser_channel=os.getenv("BROWSER_CHANNEL", "").strip().lower(),
            headless=_parse_bool(os.getenv("HEADLESS"), default=False),
            default_timeout_ms=_parse_int(os.getenv("DEFAULT_TIMEOUT_MS"), default=15000),
            test_card_number=os.getenv("TEST_CARD_NUMBER", "4111111111111111").strip(),
            test_card_expiry=os.getenv("TEST_CARD_EXPIRY", "12/28").strip(),
            test_card_cvv=os.getenv("TEST_CARD_CVV", "123").strip(),
            test_card_holder=os.getenv("TEST_CARD_HOLDER", "Test User").strip(),
            test_invalid_card_number=os.getenv(
                "TEST_INVALID_CARD_NUMBER", "4111111111111112"
            ).strip(),
            test_upi_id=os.getenv("TEST_UPI_ID", "success@razorpay").strip(),
            test_netbanking_bank=os.getenv("TEST_NETBANKING_BANK", "HDFC").strip(),
            test_otp_code=os.getenv("TEST_OTP_CODE", "123456").strip(),
            sandbox_test_otp=os.getenv("SANDBOX_TEST_OTP", "123456").strip(),
            otp_poll_timeout_seconds=_parse_int(
                os.getenv("OTP_POLL_TIMEOUT_SECONDS"), default=30
            ),
            enable_live_otp_e2e=_parse_bool(os.getenv("ENABLE_LIVE_OTP_E2E"), default=False),
            test_recipient_name=os.getenv("TEST_RECIPIENT_NAME", "QA Test User").strip(),
            test_recipient_email=os.getenv("TEST_RECIPIENT_EMAIL", "qa.test@example.com").strip(),
            test_recipient_mobile=os.getenv("TEST_RECIPIENT_MOBILE", "9820098200").strip(),
            test_sender_name=os.getenv("TEST_SENDER_NAME", "QA Automation").strip(),
            appium_server_url=os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723").strip(),
            android_udid=os.getenv("ANDROID_UDID", "").strip(),
            android_platform_version=os.getenv("ANDROID_PLATFORM_VERSION", "14.0").strip(),
            app_package=os.getenv("APP_PACKAGE", "in.swiggy.android").strip(),
            app_activity=os.getenv("APP_ACTIVITY", "").strip(),
            app_wait_activity=os.getenv("APP_WAIT_ACTIVITY", "in.swiggy.android.*").strip(),
            apk_path=os.getenv("APK_PATH", "").strip(),
            no_reset=_parse_bool(os.getenv("NO_RESET"), default=True),
            auto_grant_permissions=_parse_bool(os.getenv("AUTO_GRANT_PERMISSIONS"), default=True),
        )

    def validate_for_suite(self, suite: Literal["web", "mobile"]) -> None:
        """Validate that required configuration keys are populated for the target suite."""
        required_map: dict[str, list[tuple[str, str]]] = {
            "web": [
                ("RAZORPAY_DEMO_URL", self.razorpay_demo_url),
                ("BROWSER", self.browser),
            ],
            "mobile": [
                ("APPIUM_SERVER_URL", self.appium_server_url),
                ("ANDROID_UDID", self.android_udid),
                ("APP_PACKAGE", self.app_package),
                ("APP_ACTIVITY", self.app_activity),
            ],
        }
        if suite not in required_map:
            raise ValueError(f"Unsupported suite type: {suite!r}. Expected 'web' or 'mobile'.")

        missing = [env_key for env_key, val in required_map[suite] if not val]
        if missing:
            raise ValueError(
                f"Missing required {suite} configuration in environment/.env: {', '.join(missing)}"
            )


def get_settings() -> Settings:
    """Return a fresh Settings instance loaded from environment variables."""
    return Settings.from_env()
