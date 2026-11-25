"""End-to-end Web payment completion tests through 2FA/OTP on Razorpay Sandbox."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import Settings
from pages.web.razorpay_demo_page import (
    LiveGatewayTestCardUnsupportedError,
    RazorpayDemoPage,
)

pytestmark = [pytest.mark.web, pytest.mark.e2e, pytest.mark.regression]


def test_razorpay_sandbox_card_e2e_confirmation(settings: Settings, web_page: Page) -> None:
    """Complete Razorpay Demo Card checkout past 2FA and assert 'pay_...' Payment ID."""
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
        payment_id = demo_page.complete_sandbox_2fa_and_assert_confirmation(
            otp=settings.sandbox_test_otp
        )
    except LiveGatewayTestCardUnsupportedError as exc:
        pytest.skip(
            f"{exc} Provide a Razorpay test-mode URL in RAZORPAY_DEMO_URL to execute full 2FA E2E."
        )

    assert payment_id.startswith("pay_"), f"Expected 'pay_...' Payment ID, got {payment_id!r}"
