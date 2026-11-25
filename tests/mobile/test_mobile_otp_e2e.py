"""Android ADB SMS OTP retrieval and gated end-to-end mobile payment tests."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from config.settings import Settings, get_settings
from pages.mobile.swiggy_cart_page import SwiggyCartPage
from pages.mobile.swiggy_payment_page import SwiggyPaymentPage
from utils.otp_helper import fetch_latest_sms_otp, get_device_timestamp_ms

if TYPE_CHECKING:
    from appium.webdriver.webdriver import WebDriver

pytestmark = [pytest.mark.mobile, pytest.mark.e2e]


def test_adb_sms_otp_inbox_retrieval_on_emulator(settings: Settings) -> None:
    """Inject a simulated bank SMS into the Android emulator and verify ADB OTP polling."""
    assert settings.android_udid, "ANDROID_UDID must be set in .env to run ADB SMS OTP test."

    min_timestamp_ms = get_device_timestamp_ms(settings.android_udid) - 2000
    sms_text = "Your OTP for Juspay QE payment is 739204. Do not share."
    inject_cmd = [
        "adb",
        "-s",
        settings.android_udid,
        "emu",
        "sms",
        "send",
        "JUSPAY",
        sms_text,
    ]
    result = subprocess.run(
        inject_cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"Failed to inject emulator SMS via ADB: {(result.stderr or result.stdout).strip()}"
    )

    extracted_otp = fetch_latest_sms_otp(
        udid=settings.android_udid,
        min_timestamp_ms=min_timestamp_ms,
        sender_filter="JUSPAY",
        timeout=float(settings.otp_poll_timeout_seconds),
    )
    assert extracted_otp == "739204", f"Expected OTP '739204', got {extracted_otp!r}"


@pytest.mark.skipif(
    not get_settings().enable_live_otp_e2e,
    reason="ENABLE_LIVE_OTP_E2E is false; skipping real-money checkout",
)
def test_mobile_live_otp_e2e_order_confirmation(
    settings: Settings,
    appium_driver: WebDriver,
) -> None:
    """Execute full live Swiggy Card payment using ADB SMS OTP and assert order confirmation."""
    cart_page = SwiggyCartPage(appium_driver, settings)
    cart_amount = cart_page.open_cart_and_proceed_to_payment()

    payment_page = SwiggyPaymentPage(appium_driver, settings)
    payment_page.assert_amount_integrity(cart_amount)
    payment_page.select_add_new_card()
    payment_page.enter_card_details(
        card_number=settings.test_card_number,
        expiry=settings.test_card_expiry,
        cvv=settings.test_card_cvv,
        card_holder=settings.test_card_holder,
    )

    checkout_start_ms = get_device_timestamp_ms(settings.android_udid) - 2000
    pre_activity, pre_contexts = payment_page.submit_card_payment()
    payment_page.assert_card_2fa_otp_screen_reached(pre_activity, pre_contexts)

    live_otp = fetch_latest_sms_otp(
        udid=settings.android_udid,
        min_timestamp_ms=checkout_start_ms,
        timeout=float(settings.otp_poll_timeout_seconds),
    )
    payment_page.submit_2fa_otp(live_otp)
    payment_page.assert_order_confirmed()
