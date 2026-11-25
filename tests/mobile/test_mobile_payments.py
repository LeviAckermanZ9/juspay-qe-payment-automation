"""Prioritized Appium Android tests for Swiggy payment flows up to 2FA/OTP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from config.settings import Settings
from pages.mobile.swiggy_cart_page import SwiggyCartPage
from pages.mobile.swiggy_payment_page import SwiggyPaymentPage

if TYPE_CHECKING:
    from appium.webdriver.webdriver import WebDriver

pytestmark = [pytest.mark.mobile, pytest.mark.regression]


@pytest.mark.p0
@pytest.mark.smoke
def test_mobile_card_reaches_2fa_otp(settings: Settings, appium_driver: WebDriver) -> None:
    """Verify Swiggy Card checkout validates amount integrity and reaches 3DS/OTP."""
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
    pre_activity, pre_contexts = payment_page.submit_card_payment()
    payment_page.assert_card_2fa_otp_screen_reached(pre_activity, pre_contexts)


@pytest.mark.p0
def test_mobile_upi_payment_initiation(settings: Settings, appium_driver: WebDriver) -> None:
    """Verify Swiggy Add New UPI ID flow enters VPA and transitions to collect timer."""
    cart_page = SwiggyCartPage(appium_driver, settings)
    cart_amount = cart_page.open_cart_and_proceed_to_payment()

    payment_page = SwiggyPaymentPage(appium_driver, settings)
    payment_page.assert_amount_integrity(cart_amount)
    payment_page.select_add_new_upi_id()
    payment_page.submit_upi_id(settings.test_upi_id)
    payment_page.assert_upi_collect_timer_screen()


@pytest.mark.p1
def test_mobile_netbanking_redirect(settings: Settings, appium_driver: WebDriver) -> None:
    """Verify Swiggy Netbanking flow selects bank and transitions to bank 2FA screen."""
    cart_page = SwiggyCartPage(appium_driver, settings)
    cart_amount = cart_page.open_cart_and_proceed_to_payment()

    payment_page = SwiggyPaymentPage(appium_driver, settings)
    payment_page.assert_amount_integrity(cart_amount)
    pre_activity, pre_contexts = payment_page.select_netbanking_and_submit(
        settings.test_netbanking_bank
    )
    payment_page.assert_netbanking_2fa_screen(pre_activity, pre_contexts)


@pytest.mark.p2
def test_mobile_invalid_card_validation(settings: Settings, appium_driver: WebDriver) -> None:
    """Verify Swiggy Card form surfaces an inline error for an invalid Luhn card number."""
    cart_page = SwiggyCartPage(appium_driver, settings)
    cart_page.open_cart_and_proceed_to_payment()

    payment_page = SwiggyPaymentPage(appium_driver, settings)
    payment_page.select_add_new_card()
    payment_page.enter_card_details(
        card_number=settings.test_invalid_card_number,
        expiry=settings.test_card_expiry,
        cvv=settings.test_card_cvv,
        card_holder=settings.test_card_holder,
    )
    payment_page.assert_invalid_card_error()
