"""Page Object for BookMyShow payment sheet across Card, UPI, and Netbanking flows."""

from __future__ import annotations

import re

from playwright.sync_api import FrameLocator, Page, TimeoutError as PlaywrightTimeoutError

from config.settings import Settings
from pages.web.base_web_page import BaseWebPage


class BmsPaymentPage(BaseWebPage):
    """Handles BMS payment method selection, gateway iframes, validations, and 2FA arrival."""

    PAYMENT_IFRAME_SELECTORS = [
        "iframe[src*='juspay']",
        "iframe[src*='pay']",
        "iframe[name*='payment' i]",
        "iframe[id*='payment' i]",
    ]

    PAYABLE_AMOUNT_SELECTORS = [
        "[data-testid*='payable-amount']",
        "[data-testid*='amount']",
        "button:has-text('Pay')",
        "text=/Pay\\s*(?:Rs\\.?|INR|\\u20b9)?\\s*[0-9,]+/",
    ]

    CARD_TAB_SELECTORS = [
        "role=tab[name='Debit/Credit Card']",
        "role=button[name='Debit/Credit Card']",
        "text=Credit/Debit Card",
        "text=Debit/Credit Card",
        "[data-testid*='card']",
    ]

    CARD_NUMBER_SELECTORS = [
        "placeholder=Card Number",
        "placeholder=Enter Card Number",
        "label=Card Number",
        "input[name='card_number']",
        "input[autocomplete='cc-number']",
        "input[data-testid*='card-number']",
    ]

    CARD_EXPIRY_SELECTORS = [
        "placeholder=MM / YY",
        "placeholder=MM/YY",
        "placeholder=Expiry",
        "label=Expiry",
        "input[autocomplete='cc-exp']",
        "input[name*='exp' i]",
    ]

    CARD_CVV_SELECTORS = [
        "placeholder=CVV",
        "label=CVV",
        "input[autocomplete='cc-csc']",
        "input[name*='cvv' i]",
    ]

    CARD_HOLDER_SELECTORS = [
        "placeholder=Name on Card",
        "placeholder=Cardholder Name",
        "label=Name on Card",
        "input[autocomplete='cc-name']",
        "input[name*='name' i]",
    ]

    PAY_CTA_SELECTORS = [
        "role=button[name='MAKE PAYMENT']",
        "role=button[name='Pay Now']",
        "button:has-text('Pay')",
        "button[type='submit']",
    ]

    CARD_ERROR_SELECTORS = [
        "text=/invalid card|enter a valid card|card number is invalid/i",
        "[role='alert']",
        "[class*='error' i]",
        "[data-testid*='error']",
    ]

    CARD_2FA_INDICATORS = [
        "iframe[src*='acs' i]",
        "iframe[src*='3ds' i]",
        "iframe[src*='otp' i]",
        "placeholder=Enter OTP",
        "input[name*='otp' i]",
        "text=/Enter OTP|One Time Password|3D Secure|Authentication/i",
    ]

    UPI_TAB_SELECTORS = [
        "role=tab[name='UPI']",
        "role=button[name='UPI']",
        "text=UPI",
        "[data-testid*='upi']",
    ]

    UPI_INPUT_SELECTORS = [
        "placeholder=Enter UPI ID",
        "placeholder=example@upi",
        "label=UPI ID",
        "input[name*='vpa' i]",
        "input[name*='upi' i]",
    ]

    UPI_SUBMIT_SELECTORS = [
        "role=button[name='Verify & Pay']",
        "role=button[name='Pay']",
        "button:has-text('Verify')",
        "button:has-text('Pay')",
    ]

    UPI_COLLECT_INDICATORS = [
        "text=/Approve payment|Open your UPI app|Waiting for payment|Collect request|Scan QR/i",
        "[data-testid*='upi-timer']",
        "[data-testid*='qr']",
    ]

    NETBANKING_TAB_SELECTORS = [
        "role=tab[name='Net Banking']",
        "role=button[name='Net Banking']",
        "text=Net Banking",
        "text=Netbanking",
        "[data-testid*='netbanking']",
    ]

    NETBANKING_SUBMIT_SELECTORS = [
        "role=button[name='MAKE PAYMENT']",
        "role=button[name='Pay']",
        "button:has-text('Pay')",
    ]

    BANK_2FA_INDICATORS = [
        "text=/Customer ID|User ID|NetBanking|Login to|Password/i",
        "input[name*='cust' i]",
        "input[type='password']",
    ]

    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, timeout_ms=settings.default_timeout_ms)
        self.settings = settings
        self._payment_surface: Page | FrameLocator | None = None

    def get_payment_surface(self) -> Page | FrameLocator:
        """Return the payment gateway iframe if present, or fall back to main page."""
        if self._payment_surface is not None:
            return self._payment_surface

        try:
            self._payment_surface = self.switch_to_payment_frame(
                self.PAYMENT_IFRAME_SELECTORS, timeout=5000
            )
        except PlaywrightTimeoutError:
            self.logger.info("Payment sheet rendered inline without cross-origin iframe.")
            self._payment_surface = self.page
        return self._payment_surface

    def capture_payable_amount(self) -> float:
        """Extract the payable amount displayed on the payment sheet."""
        surface = self.get_payment_surface()
        amount_locator = self.find_resilient_locator(
            surface, self.PAYABLE_AMOUNT_SELECTORS, timeout=6000
        )
        raw_text = amount_locator.inner_text(timeout=3000)
        amount = self.extract_amount(raw_text)
        self.logger.info("Captured payment gateway payable amount: %.2f", amount)
        return amount

    def assert_amount_integrity(self, expected_amount: float) -> None:
        """Assert that the payment gateway amount matches the checkout summary amount."""
        gateway_amount = self.capture_payable_amount()
        assert abs(gateway_amount - expected_amount) < 0.01, (
            f"Amount mismatch: summary={expected_amount:.2f}, gateway={gateway_amount:.2f}"
        )

    def select_card_payment(self) -> None:
        """Select the Credit/Debit Card payment method."""
        surface = self.get_payment_surface()
        card_tab = self.find_resilient_locator(surface, self.CARD_TAB_SELECTORS)
        card_tab.click(timeout=self.timeout_ms)

    def assert_pay_cta_blocked_when_empty(self) -> None:
        """Verify that the Card Pay CTA is disabled or blocks progression when inputs are empty."""
        surface = self.get_payment_surface()
        pay_btn = self.find_resilient_locator(surface, self.PAY_CTA_SELECTORS, timeout=5000)
        if not pay_btn.is_enabled():
            self.logger.info("Pay CTA is disabled while card fields are empty.")
            return

        current_url = self.page.url
        pay_btn.click(timeout=self.timeout_ms)
        assert self.page.url == current_url, "Checkout progressed despite empty card fields."

    def enter_card_details(
        self,
        card_number: str,
        expiry: str,
        cvv: str,
        card_holder: str,
    ) -> None:
        """Fill card form fields with masked logging for all sensitive values."""
        surface = self.get_payment_surface()

        number_el = self.find_resilient_locator(surface, self.CARD_NUMBER_SELECTORS)
        self.logger.info("Entering card number: ***")
        number_el.fill(card_number, timeout=self.timeout_ms)

        expiry_el = self.find_resilient_locator(surface, self.CARD_EXPIRY_SELECTORS)
        self.logger.info("Entering card expiry: ***")
        expiry_el.fill(expiry, timeout=self.timeout_ms)

        cvv_el = self.find_resilient_locator(surface, self.CARD_CVV_SELECTORS)
        self.logger.info("Entering card CVV: ***")
        cvv_el.fill(cvv, timeout=self.timeout_ms)

        try:
            holder_el = self.find_resilient_locator(
                surface, self.CARD_HOLDER_SELECTORS, timeout=3000
            )
            self.logger.info("Entering cardholder name")
            holder_el.fill(card_holder, timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            self.logger.info("Cardholder name field not required on current form.")

    def submit_card_payment(self) -> None:
        """Click the Card Pay CTA to initiate 3DS/OTP authentication."""
        surface = self.get_payment_surface()
        pay_btn = self.find_resilient_locator(surface, self.PAY_CTA_SELECTORS)
        assert pay_btn.is_enabled(), "Expected Card Pay CTA to be enabled after entering details."
        self.logger.info("Submitting card payment toward 2FA/OTP screen")
        pay_btn.click(timeout=self.timeout_ms)

    def assert_card_2fa_otp_screen_reached(self, initial_url: str) -> None:
        """Assert arrival at the bank 3DS / OTP authentication screen."""
        try:
            self.find_resilient_locator(self.page, self.CARD_2FA_INDICATORS, timeout=self.timeout_ms)
            self.logger.info("Confirmed 3DS/OTP indicator visible on page.")
            return
        except PlaywrightTimeoutError:
            new_url = self.wait_for_url_change(initial_url, timeout=self.timeout_ms)
            assert re.search(r"acs|3ds|otp|auth|bank|juspay|razorpay", new_url, re.IGNORECASE), (
                f"Expected redirect to 2FA/3DS gateway URL, got: {new_url}"
            )

    def assert_invalid_card_error(self) -> None:
        """Assert that an inline validation error appears and 2FA is not reached."""
        surface = self.get_payment_surface()
        try:
            error_el = self.find_resilient_locator(surface, self.CARD_ERROR_SELECTORS, timeout=5000)
        except PlaywrightTimeoutError:
            error_el = self.find_resilient_locator(self.page, self.CARD_ERROR_SELECTORS, timeout=5000)

        assert error_el.is_visible(), "Expected inline error message for invalid card number."
        self.logger.info("Verified inline invalid-card error: %s", error_el.inner_text())

    def select_upi_payment(self) -> None:
        """Select the UPI payment option."""
        surface = self.get_payment_surface()
        upi_tab = self.find_resilient_locator(surface, self.UPI_TAB_SELECTORS)
        upi_tab.click(timeout=self.timeout_ms)

    def submit_upi_id(self, upi_id: str) -> None:
        """Enter the UPI VPA and initiate verification/collect request."""
        surface = self.get_payment_surface()
        upi_input = self.find_resilient_locator(surface, self.UPI_INPUT_SELECTORS)
        self.logger.info("Entering UPI VPA: ***")
        upi_input.fill(upi_id, timeout=self.timeout_ms)

        submit_btn = self.find_resilient_locator(surface, self.UPI_SUBMIT_SELECTORS)
        submit_btn.click(timeout=self.timeout_ms)

    def assert_upi_collect_or_qr_initiated(self) -> None:
        """Assert transition to the UPI collect approval timer or QR view."""
        surface = self.get_payment_surface()
        try:
            indicator = self.find_resilient_locator(
                surface, self.UPI_COLLECT_INDICATORS, timeout=self.timeout_ms
            )
        except PlaywrightTimeoutError:
            indicator = self.find_resilient_locator(
                self.page, self.UPI_COLLECT_INDICATORS, timeout=self.timeout_ms
            )
        assert indicator.is_visible(), "Expected UPI collect timer or QR view to be visible."
        self.logger.info("Confirmed UPI payment initiation state.")

    def select_netbanking_and_submit(self, bank_name: str) -> str:
        """Select Netbanking, choose the target bank, and submit toward the bank portal."""
        initial_url = self.page.url
        surface = self.get_payment_surface()

        nb_tab = self.find_resilient_locator(surface, self.NETBANKING_TAB_SELECTORS)
        nb_tab.click(timeout=self.timeout_ms)

        bank_option = self.find_resilient_locator(
            surface,
            [
                f"role=button[name='{bank_name}']",
                f"text={bank_name}",
                f"label={bank_name}",
                f"[data-testid*='{bank_name.lower()}']",
            ],
        )
        self.logger.info("Selecting Netbanking bank: %s", bank_name)
        bank_option.click(timeout=self.timeout_ms)

        submit_btn = self.find_resilient_locator(surface, self.NETBANKING_SUBMIT_SELECTORS)
        submit_btn.click(timeout=self.timeout_ms)
        return initial_url

    def assert_netbanking_redirect(self, initial_url: str) -> None:
        """Assert redirect away from merchant checkout to a bank 2FA login portal."""
        new_url = self.wait_for_url_change(initial_url, timeout=self.timeout_ms)
        assert new_url != initial_url, "Expected redirect away from merchant checkout."
        self.logger.info("Verified Netbanking redirect to external gateway: %s", new_url)
        assert self._has_bank_login_or_external_domain(new_url), (
            f"Unexpected destination URL after Netbanking submit: {new_url}"
        )

    def _has_bank_login_or_external_domain(self, url: str) -> bool:
        """Verify either bank domain redirect or bank authentication form presence."""
        if "bookmyshow.com" not in url.lower():
            return True
        try:
            self.find_resilient_locator(self.page, self.BANK_2FA_INDICATORS, timeout=5000)
            return True
        except PlaywrightTimeoutError:
            return False
