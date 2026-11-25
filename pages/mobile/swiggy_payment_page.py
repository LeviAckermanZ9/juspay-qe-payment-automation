"""Page Object for Swiggy Android Payment Sheet across Card, UPI, and Netbanking."""

from __future__ import annotations

import re

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import Settings
from pages.mobile.base_mobile_page import BaseMobilePage


class SwiggyPaymentPage(BaseMobilePage):
    """Automates Swiggy payment method selection, amount integrity, validations, and 2FA checks."""

    PAYMENT_AMOUNT_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*amount.*|.*total.*|.*payable.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*(?:Pay|Total).*?(?:\\u20b9|Rs\\.?)\\s*[0-9,]+.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*(?:\\u20b9|Rs\\.?)\\s*[0-9,]+.*")'),
    ]

    ADD_CARD_OPTION_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "Add New Card"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Add New Card")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Credit & Debit Cards")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Credit.*Debit.*Card.*|.*Add.*Card.*")'),
    ]

    CARD_NUMBER_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Card Number")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Card Number")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*card_number.*|.*cardNumber.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText").instance(0)'),
    ]

    EXPIRY_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Valid Through (MM/YY)")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Valid Through")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("MM/YY")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*expiry.*|.*exp.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText").instance(1)'),
    ]
    CARD_EXPIRY_LOCATORS = EXPIRY_LOCATORS

    CARD_CVV_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("CVV")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("CVV")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*cvv.*|.*cvc.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText").instance(2)'),
    ]

    CARD_HOLDER_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Name on Card")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Name on Card")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*card_name.*|.*holder.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().className("android.widget.EditText").instance(3)'),
    ]

    PAY_BUTTON_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^Proceed$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Proceed")'),
        (AppiumBy.ACCESSIBILITY_ID, "Proceed"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^Pay(?:\\s+.*)?$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Proceed to Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Verify and Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*pay_button.*|.*submit.*|.*proceed.*")'),
    ]
    PROCEED_CARD_LOCATORS = PAY_BUTTON_LOCATORS

    CARD_ERROR_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*(?:invalid|valid card|check card|incorrect|not valid|card details|something went wrong).*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*error.*|.*snackbar_text.*")'),
    ]

    RBI_SHEET_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Save your card as per RBI guidelines")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Save Card & Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Pay without saving")'),
    ]

    PAY_WITHOUT_SAVING_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Pay without saving")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Pay without saving.*")'),
        (AppiumBy.ACCESSIBILITY_ID, "Pay without saving"),
    ]

    ADD_CARD_FORM_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Add New Card")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Card Number")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Credit & Debit Cards")'),
    ]

    CARD_2FA_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*(?:Enter OTP|One Time Password|Submit OTP|Resend OTP|Verified by Visa|Mastercard SecureCode|RuPay PaySecure).*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*(?:otp|acs|3ds).*")'),
        (AppiumBy.CLASS_NAME, "android.webkit.WebView"),
    ]

    ADD_UPI_ID_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "Add New UPI ID"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Add New UPI ID")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Enter UPI ID")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Add.*UPI.*ID.*")'),
    ]

    UPI_INPUT_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Enter UPI ID.*|.*example@.*|.*UPI ID.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*upi.*|.*vpa.*")'),
    ]

    UPI_VERIFY_AND_PAY_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Verify and Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Verify & Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Verify.*Pay.*|.*Pay.*")'),
    ]

    UPI_COLLECT_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Approve payment.*|.*Open your UPI.*|.*Waiting for.*|.*Collect request.*|.*Payment expires.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*timer.*|.*collect.*")'),
    ]

    NETBANKING_OPTION_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "Netbanking"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^Net\\s*banking$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Netbanking")'),
    ]

    NETBANKING_2FA_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Customer ID.*|.*User ID.*|.*NetBanking.*|.*Password.*|.*Login.*")'),
        (AppiumBy.CLASS_NAME, "android.webkit.WebView"),
    ]

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        super().__init__(driver, timeout_sec=settings.default_timeout_sec)
        self.settings = settings

    def capture_payable_amount(self) -> float:
        """Capture payable total displayed on the Swiggy mobile payment sheet."""
        amount_el = self.find_resilient_element(self.PAYMENT_AMOUNT_LOCATORS, timeout=10.0)
        raw_text = amount_el.text or amount_el.get_attribute("content-desc") or ""
        amount = self.extract_amount(raw_text)
        self.logger.info("Captured Swiggy payment sheet payable amount: %.2f", amount)
        return amount

    def assert_amount_integrity(self, expected_amount: float) -> None:
        """Assert that the payment sheet amount matches the Cart To Pay amount."""
        gateway_amount = self.capture_payable_amount()
        assert abs(gateway_amount - expected_amount) < 0.01, (
            f"Mobile amount mismatch: cart={expected_amount:.2f}, payment={gateway_amount:.2f}"
        )

    def select_add_new_card(self) -> None:
        """Scroll to and tap the Credit/Debit Card entry option."""
        try:
            self.scroll_to_text("Add New Card")
        except TimeoutException:
            pass
        self.click_resilient(self.ADD_CARD_OPTION_LOCATORS, timeout=10.0)

    def enter_card_details(
        self,
        card_number: str,
        expiry: str,
        cvv: str,
        card_holder: str,
    ) -> None:
        """Fill mobile card fields with masked logging and safe keyboard dismissal."""
        self.send_keys_resilient(self.CARD_NUMBER_LOCATORS, card_number, mask_log=True)
        self.send_keys_resilient(self.CARD_EXPIRY_LOCATORS, expiry, mask_log=True)
        self.send_keys_resilient(self.CARD_CVV_LOCATORS, cvv, mask_log=True)

        try:
            self.send_keys_resilient(
                self.CARD_HOLDER_LOCATORS,
                card_holder,
                mask_log=False,
                timeout=3.0,
            )
        except TimeoutException:
            self.logger.info("Cardholder name field not required on current mobile card form.")

        self.hide_keyboard_safe()

    def _handle_rbi_tokenization_sheet(self, timeout: float = 4.0) -> bool:
        """Click 'Pay without saving' if Swiggy's RBI card-tokenization bottom sheet appears."""
        if not self._is_any_displayed(self.RBI_SHEET_INDICATORS, timeout=timeout):
            return False

        try:
            pay_without_saving_btn = self.find_resilient_element(
                self.PAY_WITHOUT_SAVING_LOCATORS, timeout=timeout
            )
            if pay_without_saving_btn.is_displayed():
                self.logger.info("Dismissing RBI tokenization sheet via 'Pay without saving'")
                pay_without_saving_btn.click()
                return True
        except TimeoutException:
            self.logger.info("RBI sheet detected without visible 'Pay without saving' button.")
        return False

    def submit_card_payment(self) -> tuple[str, list[str]]:
        """Capture current activity/contexts, tap Proceed/Pay, and bypass save-card prompt."""
        pre_activity = self.driver.current_activity or ""
        pre_contexts = list(self.driver.contexts)
        self.click_resilient(self.PAY_BUTTON_LOCATORS, timeout=10.0)
        self._handle_rbi_tokenization_sheet(timeout=4.0)
        return pre_activity, pre_contexts

    def assert_card_2fa_otp_screen_reached(
        self,
        pre_activity: str,
        pre_contexts: list[str],
    ) -> None:
        """Assert arrival at the 3DS/OTP screen via WebView/activity transition or OTP elements."""
        try:
            self.wait_for_text_or_element(
                text_substring="OTP",
                locators=self.CARD_2FA_INDICATORS,
                timeout=self.timeout_sec,
            )
            self.logger.info("Confirmed 3DS/OTP UI element on mobile payment screen.")
            return
        except TimeoutException:
            post_activity = self.driver.current_activity or ""
            post_contexts = list(self.driver.contexts)
            webview_added = any("WEBVIEW" in ctx.upper() for ctx in post_contexts) and (
                len(post_contexts) > len(pre_contexts)
            )
            if post_activity != pre_activity or webview_added:
                self.logger.info(
                    "Confirmed 2FA transition (activity=%s->%s, contexts=%s)",
                    pre_activity,
                    post_activity,
                    post_contexts,
                )
                return

        raise AssertionError("Did not observe 3DS/OTP screen or WebView/activity transition.")

    def assert_invalid_card_error(self) -> None:
        """Click Proceed, bypass RBI save-card sheet if shown, and assert error or no 2FA."""
        proceed_btn = self.find_resilient_element(self.PROCEED_CARD_LOCATORS, timeout=5.0)
        enabled_attr = str(proceed_btn.get_attribute("enabled") or "").strip().lower()
        is_proceed_enabled = proceed_btn.is_enabled() and enabled_attr != "false"

        if is_proceed_enabled:
            self.logger.info("Proceed button is enabled; tapping Proceed to trigger card validation")
            proceed_btn.click()
            self._handle_rbi_tokenization_sheet(timeout=4.0)
        else:
            self.logger.info("Proceed button remained disabled for invalid card input")

        # 1. Check inline error / dialog / snackbar elements (wait up to 5s post-submit).
        try:
            error_el = self.find_resilient_element(self.CARD_ERROR_LOCATORS, timeout=5.0)
            if error_el.is_displayed():
                self.logger.info("Confirmed inline invalid-card error: %s", error_el.text)
                return
        except TimeoutException:
            pass

        # 2. Check Android Toast message (Toasts require presence_of_element_located).
        try:
            toast_el = WebDriverWait(self.driver, 3.0).until(
                EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.Toast"))
            )
            toast_text = (toast_el.text or toast_el.get_attribute("name") or "").strip()
            if re.search(
                r"invalid|valid card|check card|incorrect|not valid|card details|something went wrong",
                toast_text,
                re.I,
            ):
                self.logger.info("Confirmed Android Toast invalid-card message: %s", toast_text)
                return
        except TimeoutException:
            pass

        # 3. Confirm no bank OTP/2FA challenge launched and screen stayed on native checkout.
        if self._is_any_displayed(self.CARD_2FA_INDICATORS, timeout=2.0):
            raise AssertionError("Invalid card unexpectedly navigated to the 2FA/OTP screen.")

        try:
            form_el = self.find_resilient_element(self.ADD_CARD_FORM_INDICATORS, timeout=4.0)
            if form_el.is_displayed():
                self.logger.info(
                    "Confirmed checkout stayed on Swiggy native card/checkout screen without 2FA."
                )
                return
        except TimeoutException:
            pass

        raise AssertionError(
            "Expected inline error, toast, or native checkout block without 2FA for invalid card."
        )

    def _is_any_displayed(
        self,
        locators: list[tuple[str, str]],
        timeout: float = 1.5,
    ) -> bool:
        """Return True if any candidate locator is currently visible."""
        for by, locator in locators:
            if self.is_displayed(by, locator, timeout=timeout):
                return True
        return False

    def select_add_new_upi_id(self) -> None:
        """Select Add New UPI ID (staying inside Swiggy without launching external UPI apps)."""
        try:
            self.scroll_to_text("Add New UPI ID")
        except TimeoutException:
            pass
        self.click_resilient(self.ADD_UPI_ID_LOCATORS, timeout=10.0)

    def submit_upi_id(self, upi_id: str) -> None:
        """Enter UPI VPA with masked logging and tap Verify and Pay."""
        self.send_keys_resilient(self.UPI_INPUT_LOCATORS, upi_id, mask_log=True)
        self.hide_keyboard_safe()
        self.click_resilient(self.UPI_VERIFY_AND_PAY_LOCATORS, timeout=10.0)

    def assert_upi_collect_timer_screen(self) -> None:
        """Assert transition to the UPI collect request approval timer screen."""
        indicator = self.wait_for_text_or_element(
            text_substring="Approve",
            locators=self.UPI_COLLECT_INDICATORS,
            timeout=self.timeout_sec,
        )
        assert indicator.is_displayed(), "Expected UPI collect approval timer screen."
        self.logger.info("Confirmed mobile UPI collect timer screen.")

    def select_netbanking_and_submit(self, bank_name: str) -> tuple[str, list[str]]:
        """Select Netbanking, choose target bank, and tap Pay toward bank 2FA."""
        pre_activity = self.driver.current_activity or ""
        pre_contexts = list(self.driver.contexts)

        try:
            self.scroll_to_text("Netbanking")
        except TimeoutException:
            pass
        self.click_resilient(self.NETBANKING_OPTION_LOCATORS, timeout=10.0)

        try:
            self.scroll_to_text(bank_name)
        except TimeoutException:
            pass
        bank_locators: list[tuple[str, str]] = [
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{bank_name}")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().descriptionContains("{bank_name}")'),
        ]
        self.logger.info("Selecting mobile Netbanking bank: %s", bank_name)
        self.click_resilient(bank_locators, timeout=10.0)

        try:
            self.click_resilient(self.PAY_BUTTON_LOCATORS, timeout=4.0)
        except TimeoutException:
            self.logger.info("Bank tap initiated redirect directly without secondary Pay CTA.")

        return pre_activity, pre_contexts

    def assert_netbanking_2fa_screen(
        self,
        pre_activity: str,
        pre_contexts: list[str],
    ) -> None:
        """Assert transition to bank Netbanking login / 2FA authentication screen."""
        try:
            self.wait_for_text_or_element(
                text_substring="NetBanking",
                locators=self.NETBANKING_2FA_INDICATORS,
                timeout=self.timeout_sec,
            )
            self.logger.info("Confirmed mobile Netbanking 2FA screen.")
            return
        except TimeoutException:
            post_activity = self.driver.current_activity or ""
            post_contexts = list(self.driver.contexts)
            if post_activity != pre_activity or len(post_contexts) > len(pre_contexts):
                self.logger.info(
                    "Confirmed Netbanking 2FA transition (activity=%s->%s)",
                    pre_activity,
                    post_activity,
                )
                return

        raise AssertionError("Did not reach bank Netbanking authentication screen.")

    def submit_2fa_otp(self, otp: str) -> None:
        """Enter the retrieved 2FA OTP into native or WebView ACS field and submit."""
        otp_input_locators: list[tuple[str, str]] = [
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Enter OTP.*|.*OTP.*")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*otp.*")'),
            (AppiumBy.CLASS_NAME, "android.widget.EditText"),
        ]
        otp_submit_locators: list[tuple[str, str]] = [
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^(?:Submit|Verify|Confirm|Pay).*")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*submit.*|.*verify.*|.*confirm.*")'),
        ]
        self.send_keys_resilient(otp_input_locators, otp, mask_log=True)
        self.click_resilient(otp_submit_locators, timeout=10.0)

    def assert_order_confirmed(self) -> None:
        """Assert final Swiggy order confirmation screen after 2FA submission."""
        confirmation_locators: list[tuple[str, str]] = [
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*(?:Order Confirmed|Order Placed|Preparing your order|Payment Successful|Thank you).*")'),
            (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*order_confirmed.*|.*order_status.*|.*tracking.*")'),
        ]
        confirmation_el = self.wait_for_text_or_element(
            text_substring="Order",
            locators=confirmation_locators,
            timeout=max(self.timeout_sec, 20.0),
        )
        assert confirmation_el.is_displayed(), "Expected final Swiggy order confirmation screen."
        self.logger.info("Confirmed end-to-end order placement screen.")
