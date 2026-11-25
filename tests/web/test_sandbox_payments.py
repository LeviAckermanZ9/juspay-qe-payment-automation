"""Deterministic Playwright regression tests against Razorpay Public Demo checkout."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import Settings
from pages.web.razorpay_demo_page import (
    LiveGatewayTestCardUnsupportedError,
    RazorpayDemoPage,
)

pytestmark = [pytest.mark.web, pytest.mark.regression]


@pytest.mark.p0
def test_sandbox_card_to_otp(settings: Settings, web_page: Page) -> None:
    """Verify Razorpay Demo Card checkout transitions cleanly to the 2FA OTP screen."""
    settings.validate_for_suite("web")
    demo_page = RazorpayDemoPage(web_page, settings)
    demo_page.open_demo_and_launch_checkout()

    payable_amount = demo_page.capture_modal_amount()
    assert payable_amount > 0, f"Expected positive sandbox payable amount, got {payable_amount}"

    demo_page.pay_with_card(
        card_number=settings.test_card_number,
        expiry=settings.test_card_expiry,
        cvv=settings.test_card_cvv,
        card_holder=settings.test_card_holder,
    )
    try:
        demo_page.assert_otp_screen_reached()
    except LiveGatewayTestCardUnsupportedError as exc:
        pytest.skip(
            f"{exc} Provide a Razorpay test-mode URL in RAZORPAY_DEMO_URL to assert 3DS/OTP."
        )


@pytest.mark.p0
def test_sandbox_upi_payment_flow(settings: Settings, web_page: Page) -> None:
    """Verify Razorpay Demo UPI flow reaches the UPI QR or collect approval screen."""
    settings.validate_for_suite("web")
    demo_page = RazorpayDemoPage(web_page, settings)
    demo_page.open_demo_and_launch_checkout()

    payable_amount = demo_page.capture_modal_amount()
    assert payable_amount > 0, f"Expected positive sandbox payable amount, got {payable_amount}"

    demo_page.pay_with_upi_to_collect_screen(settings.test_upi_id)


@pytest.mark.p1
def test_sandbox_netbanking_to_bank_page(settings: Settings, web_page: Page) -> None:
    """Verify Razorpay Demo Netbanking flow reaches the simulated bank 2FA screen."""
    settings.validate_for_suite("web")
    demo_page = RazorpayDemoPage(web_page, settings)
    demo_page.open_demo_and_launch_checkout()
    demo_page.pay_with_netbanking_to_bank_page(settings.test_netbanking_bank)


@pytest.mark.p2
def test_sandbox_invalid_card_error(settings: Settings, web_page: Page) -> None:
    """Verify Razorpay Demo checkout surfaces an inline error for malformed card input."""
    settings.validate_for_suite("web")
    demo_page = RazorpayDemoPage(web_page, settings)
    demo_page.open_demo_and_launch_checkout()

    demo_page.pay_with_card(
        card_number=settings.test_invalid_card_number,
        expiry=settings.test_card_expiry,
        cvv=settings.test_card_cvv,
        card_holder=settings.test_card_holder,
    )
    demo_page.assert_invalid_card_error()
