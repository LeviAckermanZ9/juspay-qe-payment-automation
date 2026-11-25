"""Page Object for the Razorpay Public Demo checkout modal (Checkout v2)."""

from __future__ import annotations

import re
import threading
import time

from playwright.sync_api import (
    Error as PlaywrightError,
    FrameLocator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from config.settings import Settings
from pages.web.base_web_page import BaseWebPage


class LiveGatewayTestCardUnsupportedError(RuntimeError):
    """Raised when a live production gateway declines or blocks a sandbox test card."""


class RazorpayDemoPage(BaseWebPage):
    """Automates Razorpay Demo checkout inside the visible razorpay-checkout-frame."""

    LAUNCH_DEMO_CTA_SELECTORS = [
        "role=button[name='Pay with Razorpay']",
        "role=button[name='Pay Now']",
        "role=button[name='Try Checkout']",
        "button.razorpay-payment-button",
        "text=Pay with Razorpay",
    ]

    CHECKOUT_IFRAME_SELECTORS = [
        "iframe.razorpay-checkout-frame",
        "iframe[src*='api.razorpay.com']",
    ]

    HYDRATION_READY_SELECTORS = [
        "testid=contactNumber",
        "testid=card",
    ]

    CONTACT_INPUT_SELECTORS = [
        "testid=contactNumber",
        "placeholder=Mobile number",
        "placeholder=Phone number",
        "input[name='contact']",
        "input[type='tel']",
    ]

    EMAIL_INPUT_SELECTORS = [
        "placeholder=Enter Email",
        "placeholder=Email",
        "input[name='email']",
        "input[type='email']",
    ]

    PROCEED_CONTACT_SELECTORS = [
        "role=button[name='Continue']",
        "role=button[name='Proceed']",
        "button:has-text('Continue')",
        "button[type='submit']",
    ]

    MODAL_AMOUNT_SELECTORS = [
        "[data-testid='amount']",
        "#amount",
        "text=/\\u20b9\\s*[1-9][0-9,]*/",
        "text=Price Summary",
    ]

    CARD_METHOD_SELECTORS = [
        "testid=card",
        "[data-value='card']",
        "role=button[name='Cards']",
        "role=button[name='Card']",
        "text=Cards",
        "text=Card",
    ]

    CARD_NUMBER_SELECTORS = [
        "input[name='card.number']",
        "placeholder=Card Number",
        "placeholder=Card number",
        "label=Card Number",
        "input[name='card[number]']",
        "input[autocomplete='cc-number']",
    ]

    CARD_EXPIRY_SELECTORS = [
        "input[name='card.expiry']",
        "placeholder=MM / YY",
        "placeholder=MM/YY",
        "input[name='card[expiry]']",
        "input[autocomplete='cc-exp']",
    ]

    CARD_CVV_SELECTORS = [
        "input[name='card.cvv']",
        "placeholder=CVV",
        "input[name='card[cvv]']",
        "input[autocomplete='cc-csc']",
    ]

    CARD_HOLDER_SELECTORS = [
        "input[name='card.name']",
        "placeholder=Enter name on card",
        "placeholder=Card Holder's Name",
        "placeholder=Name on Card",
        "input[name='card[name]']",
        "input[autocomplete='cc-name']",
    ]

    PAY_SUBMIT_SELECTORS = [
        "role=button[name='Continue']",
        "role=button[name='Pay Now']",
        "button:has-text('Continue')",
        "button[type='submit']",
    ]

    SKIP_SAVE_CARD_SELECTORS = [
        "role=button[name='Maybe later']",
        "role=button[name='Skip']",
        "text=Maybe later",
        "text=Continue without saving",
        "text=Pay without Saving",
    ]

    OTP_INPUT_SELECTORS = [
        "input[autocomplete='one-time-code']",
        "input[name*='otp' i]",
        "input[id*='otp' i]",
        "input[placeholder*='OTP' i]",
        "input[aria-label*='OTP' i]",
    ]

    OTP_SUBMIT_SELECTORS = [
        "role=button[name='Verify']",
        "role=button[name='Submit']",
        "role=button[name='Pay']",
        "role=button[name='Continue']",
        "button:has-text('Verify')",
        "button:has-text('Submit')",
        "button[type='submit']",
    ]

    ACS_SUCCESS_BUTTON_SELECTORS = [
        "role=button[name='Success']",
        "role=button[name='Authorize']",
        "role=button[name='Approve']",
        "button:has-text('Success')",
        "button:has-text('Authorize')",
        "button:has-text('Approve')",
        "input[value='Success']",
    ]

    CONFIRMATION_INDICATORS = [
        "text=/Payment Successful|Thank you|Payment ID|pay_[A-Za-z0-9]+/i",
        "text=/pay_[A-Za-z0-9]+/",
    ]

    OTP_SCREEN_SELECTORS = [
        "placeholder=Enter OTP",
        "input[name='otp']",
        "role=button[name='Success']",
        "text=/Enter OTP|One Time Password|Verify OTP|3D Secure/i",
    ]

    DECLINED_INDICATORS = [
        "text=/Payment could not be completed|The server encountered an error|Payment declined|Test cards are not|cannot be processed/i",
    ]

    CARD_ERROR_SELECTORS = [
        "text=/invalid card|invalid number|enter a valid card|valid card number|please enter/i",
        "[role='alert']",
        ".error",
        "[class*='error' i]",
    ]

    NETBANKING_METHOD_SELECTORS = [
        "testid=netbanking",
        "[data-value='netbanking']",
        "role=button[name='Netbanking']",
        "text=Netbanking",
    ]

    UPI_METHOD_SELECTORS = [
        "testid=upi",
        "[data-value='upi']",
        "role=button[name='UPI']",
        "text=UPI",
    ]

    UPI_INPUT_SELECTORS = [
        "input[name='vpa']",
        "input[name*='vpa' i]",
        "input[name*='upi' i]",
        "placeholder=Enter UPI ID",
        "placeholder=UPI ID / Number",
        "input[placeholder*='UPI' i]",
    ]

    UPI_COLLECT_INDICATORS = [
        "text=/Scan the QR|Approve payment|Open your UPI|Collect request|Waiting for|UPI QR|Pay with Google Pay UPI/i",
        "[data-testid*='upi-qr']",
        "[data-testid*='upi-timer']",
    ]

    BANK_DEMO_INDICATORS = [
        "role=button[name='Success']",
        "role=button[name='Failure']",
        "text=/Complete your payment|Scan the QR|mobile banking app|Success|Failure|Razorpay Bank|Demo Bank|Customer ID|User ID|NetBanking/i",
    ]

    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, timeout_ms=settings.default_timeout_ms)
        self.settings = settings
        self._checkout_frame: FrameLocator | None = None

    def open_demo_and_launch_checkout(self) -> FrameLocator:
        """Open Razorpay Demo page, launch modal, and switch to hydrated checkout iframe."""
        self.logger.info(
            "Navigating to URL (wait_until=domcontentloaded): %s",
            self.settings.razorpay_demo_url,
        )
        self.page.goto(
            self.settings.razorpay_demo_url,
            wait_until="domcontentloaded",
            timeout=max(self.timeout_ms, 45000),
        )
        # Allow checkout.js script bindings to settle before clicking Pay with Razorpay.
        try:
            self.page.wait_for_load_state("load", timeout=15000)
        except PlaywrightTimeoutError:
            self.logger.info("Proceeding after domcontentloaded while auxiliary assets settle.")

        launch_btn = self.find_resilient_locator(
            self.page,
            self.LAUNCH_DEMO_CTA_SELECTORS,
            timeout=max(self.timeout_ms, 20000),
        )
        launch_btn.scroll_into_view_if_needed(timeout=self.timeout_ms)
        launch_btn.click(timeout=self.timeout_ms)

        try:
            self._checkout_frame = self.switch_to_payment_frame(
                self.CHECKOUT_IFRAME_SELECTORS, timeout=12000
            )
        except PlaywrightTimeoutError:
            self.logger.info("Checkout iframe did not appear on initial click; retrying launch CTA.")
            launch_btn.click(timeout=self.timeout_ms)
            self._checkout_frame = self.switch_to_payment_frame(
                self.CHECKOUT_IFRAME_SELECTORS, timeout=15000
            )
        # Wait for Checkout v2 React app inside iframe to render controls before interacting.
        self.find_resilient_locator(
            self._checkout_frame, self.HYDRATION_READY_SELECTORS, timeout=20000
        )
        self._complete_contact_step_if_present(self._checkout_frame)
        return self._checkout_frame

    def _get_frame(self) -> FrameLocator:
        """Return the active Razorpay checkout FrameLocator."""
        if self._checkout_frame is None:
            self._checkout_frame = self.switch_to_payment_frame(self.CHECKOUT_IFRAME_SELECTORS)
        return self._checkout_frame

    def _complete_contact_step_if_present(self, frame: FrameLocator) -> None:
        """Complete the Razorpay Checkout v2 contact overlay if displayed."""
        try:
            contact_el = self.find_resilient_locator(
                frame, self.CONTACT_INPUT_SELECTORS, timeout=4000
            )
        except PlaywrightTimeoutError:
            return

        mobile = self.settings.test_recipient_mobile
        if mobile == "9876543210":
            mobile = "9820098200"

        self.logger.info("Completing Razorpay contact overlay step")
        contact_el.click(timeout=self.timeout_ms)
        contact_el.fill("", timeout=self.timeout_ms)
        contact_el.press_sequentially(mobile, delay=20)

        # Typing 10 valid digits may auto-submit; click Continue only if overlay remains open.
        try:
            proceed_btn = self.find_resilient_locator(
                frame, self.PROCEED_CONTACT_SELECTORS, timeout=1500
            )
            proceed_btn.click(timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            pass

        try:
            frame.locator("#overlay-backdrop").wait_for(state="hidden", timeout=10000)
        except PlaywrightTimeoutError:
            self.logger.info("Contact overlay backdrop remained open or is not present.")

    def capture_modal_amount(self) -> float:
        """Capture payable amount shown inside the Razorpay checkout modal."""
        frame = self._get_frame()
        # Wait for the Price Summary header inside the modal to finish rendering.
        frame.get_by_text("Price Summary").first.wait_for(state="visible", timeout=8000)

        for candidate in frame.locator("text=/\\u20b9/").all()[:6]:
            try:
                normalized = candidate.inner_text(timeout=1000).replace("\n", " ").strip()
                match = re.search(r"\u20b9\s*([1-9][0-9,]*(?:\.\d{1,2})?)", normalized)
                if match:
                    amount = float(match.group(1).replace(",", ""))
                    self.logger.info("Captured Razorpay modal payable amount: %.2f", amount)
                    return amount
            except (PlaywrightTimeoutError, ValueError):
                continue

        # Fallback to parent container of the currency symbol if digit is in a sibling span.
        currency_parent = frame.locator("text=/\\u20b9/").first.locator("..").locator("..")
        raw_text = currency_parent.inner_text(timeout=3000).replace("\n", " ")
        match = re.search(r"\u20b9\s*([1-9][0-9,]*(?:\.\d{1,2})?)", raw_text)
        if not match:
            raise ValueError(f"Could not extract positive modal amount from {raw_text!r}")
        amount = float(match.group(1).replace(",", ""))
        self.logger.info("Captured Razorpay modal payable amount: %.2f", amount)
        return amount

    def pay_with_card(
        self,
        card_number: str,
        expiry: str,
        cvv: str,
        card_holder: str,
    ) -> None:
        """Select Card inside Razorpay modal, fill card details across steps, and submit."""
        frame = self._get_frame()
        if frame.locator("#overlay-backdrop").is_visible():
            self._complete_contact_step_if_present(frame)
        card_method = self.find_resilient_locator(frame, self.CARD_METHOD_SELECTORS)
        card_method.click(timeout=self.timeout_ms)

        self.logger.info("Entering sandbox card number: ***")
        try:
            card_num_input = self.find_resilient_locator(
                frame, self.CARD_NUMBER_SELECTORS, timeout=4000
            )
        except PlaywrightTimeoutError:
            self.logger.info("Card form did not expand on first click; retrying Card tab selection.")
            card_method.click(timeout=self.timeout_ms)
            card_num_input = self.find_resilient_locator(frame, self.CARD_NUMBER_SELECTORS)
        card_num_input.fill(card_number, timeout=self.timeout_ms)
        self.logger.info("Entering sandbox card expiry: ***")
        self.find_resilient_locator(frame, self.CARD_EXPIRY_SELECTORS).fill(
            expiry, timeout=self.timeout_ms
        )
        self.logger.info("Entering sandbox card CVV: ***")
        self.find_resilient_locator(frame, self.CARD_CVV_SELECTORS).fill(
            cvv, timeout=self.timeout_ms
        )

        # If inline card validation error already surfaced (negative flow), stop before step 2.
        try:
            self.find_resilient_locator(frame, self.CARD_ERROR_SELECTORS, timeout=1500)
            return
        except PlaywrightTimeoutError:
            pass

        pay_btn = self.find_resilient_locator(frame, self.PAY_SUBMIT_SELECTORS)
        pay_btn.click(timeout=self.timeout_ms)

        # Checkout v2 reveals cardholder name and email on step 2 for valid card numbers.
        self._complete_card_holder_and_email_if_prompted(frame, card_holder)
        self._skip_save_card_if_prompted(frame)

    def _complete_card_holder_and_email_if_prompted(
        self,
        frame: FrameLocator,
        card_holder: str,
    ) -> None:
        """Fill cardholder name and email if step 2 of Checkout v2 card form appears."""
        filled_step2 = False
        try:
            holder_el = self.find_resilient_locator(frame, self.CARD_HOLDER_SELECTORS, timeout=2500)
            self.logger.info("Entering cardholder name on step 2")
            holder_el.fill(card_holder, timeout=self.timeout_ms)
            filled_step2 = True
        except PlaywrightTimeoutError:
            pass

        try:
            email_el = self.find_resilient_locator(frame, self.EMAIL_INPUT_SELECTORS, timeout=2000)
            email_el.fill(self.settings.test_recipient_email, timeout=self.timeout_ms)
            filled_step2 = True
        except PlaywrightTimeoutError:
            pass

        if filled_step2:
            pay_btn = self.find_resilient_locator(frame, self.PAY_SUBMIT_SELECTORS)
            pay_btn.click(timeout=self.timeout_ms)

    def _skip_save_card_if_prompted(
        self, frame: FrameLocator, timeout_ms: int = 7000
    ) -> bool:
        """Dismiss optional save-card prompt if Razorpay presents it after clicking Continue."""
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        wait_event = threading.Event()
        while time.monotonic() < deadline:
            try:
                skip_btn = self._find_quick_visible(
                    frame, self.SKIP_SAVE_CARD_SELECTORS, per_selector_ms=350
                )
                if skip_btn is not None:
                    self.logger.info("Dismissing Razorpay save-card prompt.")
                    skip_btn.click(timeout=self.timeout_ms)
                    return True
            except PlaywrightError:
                pass
            if self._is_live_card_declined():
                return False
            remaining = deadline - time.monotonic()
            if remaining > 0:
                wait_event.wait(min(0.4, remaining))
        return False

    def assert_otp_screen_reached(self) -> None:
        """Assert arrival at the 2FA/OTP screen or fail clearly if live gateway declines test card."""
        deadline = time.monotonic() + max(self.timeout_ms / 1000.0, 15.0)
        wait_event = threading.Event()
        frame = self._get_frame()

        while time.monotonic() < deadline:
            if self._is_live_card_declined():
                raise LiveGatewayTestCardUnsupportedError(
                    "Razorpay Demo runs in live production mode and declined the public test "
                    "card before 3DS/OTP authentication."
                )

            for surface in self._discover_active_2fa_surfaces():
                if isinstance(surface, Page) and surface.is_closed():
                    continue
                try:
                    otp_el = self._find_quick_visible(
                        surface, self.OTP_SCREEN_SELECTORS, per_selector_ms=350
                    )
                    if otp_el is not None and otp_el.is_visible():
                        self.logger.info("Confirmed Razorpay Demo 2FA/OTP screen.")
                        return
                except PlaywrightError as exc:
                    if not self._is_transient_surface_error(exc):
                        raise

            self._skip_save_card_if_prompted(frame, timeout_ms=700)
            remaining = deadline - time.monotonic()
            if remaining > 0:
                wait_event.wait(min(0.5, remaining))

        raise AssertionError("Did not reach Razorpay Demo OTP/2FA screen.")

    def complete_sandbox_2fa_and_assert_confirmation(self, otp: str) -> str:
        """Complete test-mode 2FA across dynamic popups/iframes and return Payment ID."""
        deadline = time.monotonic() + max(self.timeout_ms / 1000.0, 20.0)
        wait_event = threading.Event()
        completed_2fa = False

        while time.monotonic() < deadline:
            existing_payment_id = self._extract_payment_id_from_host()
            if existing_payment_id:
                self.logger.info(
                    "Confirmed Razorpay E2E Payment ID on host page: %s",
                    existing_payment_id,
                )
                return existing_payment_id

            if self._is_live_card_declined():
                raise LiveGatewayTestCardUnsupportedError(
                    "Razorpay Demo runs in live production mode and rejected the non-live test "
                    "card before 2FA/confirmation."
                )

            if self._submit_2fa_on_surfaces(otp):
                completed_2fa = True
                break

            remaining = deadline - time.monotonic()
            if remaining > 0:
                wait_event.wait(min(0.5, remaining))

        if not completed_2fa:
            existing_payment_id = self._extract_payment_id_from_host()
            if existing_payment_id:
                self.logger.info(
                    "Confirmed Razorpay E2E Payment ID on host page: %s",
                    existing_payment_id,
                )
                return existing_payment_id
            raise AssertionError(
                "Could not locate test-mode OTP input, Mock Bank Success CTA, or confirmation."
            )

        confirmation_el = self._wait_for_confirmation_element()
        raw_text = confirmation_el.inner_text(timeout=3000)
        page_text = self.page.locator("body").inner_text(timeout=3000)
        combined = f"{raw_text}\n{page_text}"

        match = re.search(r"\b(pay_[A-Za-z0-9]+)\b", combined)
        if not match:
            raise AssertionError(
                f"Payment confirmation displayed without a valid 'pay_...' Payment ID: {raw_text!r}"
            )

        payment_id = match.group(1)
        self.logger.info("Confirmed Razorpay E2E Payment ID: %s", payment_id)
        return payment_id

    @staticmethod
    def _is_transient_surface_error(exc: PlaywrightError) -> bool:
        """Return True if a PlaywrightError indicates a closed popup or detached frame."""
        message = str(exc)
        transient_markers = (
            "Target page, context or browser has been closed",
            "Target closed",
            "Frame was detached",
            "Execution context was destroyed",
        )
        return any(marker in message for marker in transient_markers)

    def _discover_active_2fa_surfaces(self) -> list[Page | FrameLocator]:
        """Dynamically collect open popups, checkout/nested iframes, and the host page."""
        surfaces: list[Page | FrameLocator] = []
        open_pages = [pg for pg in self.page.context.pages if not pg.is_closed()]

        # Prioritize newly opened bank/ACS popup windows over the merchant host page.
        for open_page in reversed(open_pages):
            if open_page != self.page:
                surfaces.append(open_page)

        if not self.page.is_closed():
            checkout_frame_sel = "iframe.razorpay-checkout-frame:visible"
            try:
                if self.page.locator(checkout_frame_sel).count() > 0:
                    checkout_fl = self.page.frame_locator(checkout_frame_sel).first
                    # Check nested bank/ACS iframes inside the checkout modal first.
                    nested = checkout_fl.locator("iframe:visible")
                    for idx in range(min(nested.count(), 3)):
                        surfaces.append(nested.nth(idx).content_frame)
                    surfaces.append(checkout_fl)
            except PlaywrightError as exc:
                if not self._is_transient_surface_error(exc):
                    raise

            try:
                other_iframes = self.page.locator(
                    "iframe:visible:not([src*='stripe']):not([src*='hcaptcha'])"
                    ":not([src*='sardine']):not([src*='online-metrix'])"
                )
                for idx in range(min(other_iframes.count(), 3)):
                    surfaces.append(other_iframes.nth(idx).content_frame)
            except PlaywrightError as exc:
                if not self._is_transient_surface_error(exc):
                    raise

            surfaces.append(self.page)

        return surfaces

    def _extract_payment_id_from_host(self) -> str | None:
        """Return generated 'pay_...' Payment ID if host page already shows confirmation."""
        if self.page.is_closed():
            return None
        try:
            body_text = self.page.locator("body").inner_text(timeout=1000)
        except (PlaywrightTimeoutError, PlaywrightError):
            return None

        match = re.search(r"\b(pay_[A-Za-z0-9]+)\b", body_text)
        return match.group(1) if match else None

    def _is_live_card_declined(self) -> bool:
        """Check host page, checkout iframe, and popups for live-mode decline or error."""
        if self.page.is_closed():
            return False

        surfaces_to_check: list[Page | FrameLocator] = []
        try:
            checkout_loc = self.page.locator("iframe.razorpay-checkout-frame:visible")
            if checkout_loc.count() > 0:
                surfaces_to_check.append(
                    self.page.frame_locator("iframe.razorpay-checkout-frame:visible").first
                )
        except PlaywrightError as exc:
            if not self._is_transient_surface_error(exc):
                raise

        surfaces_to_check.append(self.page)
        for open_page in self.page.context.pages:
            if not open_page.is_closed() and open_page != self.page:
                surfaces_to_check.append(open_page)

        for surface in surfaces_to_check:
            try:
                if self._find_quick_visible(surface, self.DECLINED_INDICATORS, per_selector_ms=400) is not None:
                    self.logger.info("Detected live-mode gateway rejection/error indicator.")
                    return True
            except (PlaywrightTimeoutError, PlaywrightError):
                continue

        return False

    def _find_quick_visible(
        self,
        surface: Page | FrameLocator,
        selectors: list[str],
        per_selector_ms: int = 350,
    ):
        """Probe candidate selectors quickly within a single polling iteration."""
        for selector in selectors:
            candidate = self._build_locator(surface, selector)
            try:
                candidate.wait_for(state="visible", timeout=per_selector_ms)
                return candidate
            except PlaywrightTimeoutError:
                continue
        return None

    def _submit_2fa_on_surfaces(self, otp: str) -> bool:
        """Prioritize Mock Bank 'Success' or OTP submission across active non-closed surfaces."""
        for surface in self._discover_active_2fa_surfaces():
            if isinstance(surface, Page) and surface.is_closed():
                continue

            # 1. Prioritize Mock Bank ACS 'Success' / 'Authorize' / 'Approve' button.
            try:
                success_btn = self._find_quick_visible(
                    surface, self.ACS_SUCCESS_BUTTON_SELECTORS
                )
                if success_btn is not None:
                    self.logger.info("Clicking Mock Bank ACS confirmation button")
                    try:
                        success_btn.click(timeout=self.timeout_ms)
                    except PlaywrightError as exc:
                        if self._is_transient_surface_error(exc):
                            self.logger.info(
                                "Popup/frame closed immediately after clicking ACS confirmation"
                            )
                            return True
                        raise
                    return True
            except PlaywrightError as exc:
                if self._is_transient_surface_error(exc):
                    self.logger.info("Transient surface closed while checking ACS button; continuing")
                    continue
                raise

            # 2. Otherwise check for an inline or popup 2FA OTP input.
            try:
                otp_input = self._find_quick_visible(surface, self.OTP_INPUT_SELECTORS)
                if otp_input is not None:
                    self.logger.info("Entering sandbox 2FA OTP: ***")
                    otp_input.fill(otp, timeout=self.timeout_ms)
                    submit_btn = self.find_resilient_locator(
                        surface, self.OTP_SUBMIT_SELECTORS, timeout=4000
                    )
                    try:
                        submit_btn.click(timeout=self.timeout_ms)
                    except PlaywrightError as exc:
                        if self._is_transient_surface_error(exc):
                            self.logger.info(
                                "Popup/frame closed immediately after submitting OTP"
                            )
                            return True
                        raise
                    return True
            except PlaywrightTimeoutError:
                continue
            except PlaywrightError as exc:
                if self._is_transient_surface_error(exc):
                    self.logger.info("Transient surface closed while checking OTP; continuing")
                    continue
                raise

        return False

    def _wait_for_confirmation_element(self):
        """Wait for post-2FA payment confirmation banner or Payment ID on host page."""
        try:
            return self.find_resilient_locator(
                self.page, self.CONFIRMATION_INDICATORS, timeout=self.timeout_ms
            )
        except (PlaywrightTimeoutError, PlaywrightError):
            try:
                frame = self.switch_to_payment_frame(self.CHECKOUT_IFRAME_SELECTORS, timeout=5000)
                return self.find_resilient_locator(
                    frame, self.CONFIRMATION_INDICATORS, timeout=8000
                )
            except PlaywrightError as exc:
                if self._is_transient_surface_error(exc):
                    return self.find_resilient_locator(
                        self.page, self.CONFIRMATION_INDICATORS, timeout=8000
                    )
                raise

    def assert_invalid_card_error(self) -> None:
        """Assert inline validation error on malformed card input inside checkout modal."""
        frame = self._get_frame()
        error_el = self.find_resilient_locator(frame, self.CARD_ERROR_SELECTORS, timeout=6000)
        assert error_el.is_visible(), "Expected inline error message for malformed card input."
        self.logger.info("Confirmed Razorpay invalid card error: %s", error_el.inner_text())

    def pay_with_netbanking_to_bank_page(self, bank_name: str) -> None:
        """Select Netbanking and a bank in Razorpay modal, then assert bank portal/simulator."""
        initial_url = self.page.url
        frame = self._get_frame()
        if frame.locator("#overlay-backdrop").is_visible():
            self._complete_contact_step_if_present(frame)
        nb_method = self.find_resilient_locator(frame, self.NETBANKING_METHOD_SELECTORS)
        nb_method.click(timeout=self.timeout_ms)

        bank_display_candidates = [
            f"text={bank_name} Bank",
            f"text={bank_name}",
            f"role=button[name='{bank_name}']",
            f"label={bank_name}",
        ]
        bank_option = self.find_resilient_locator(frame, bank_display_candidates)
        self.logger.info("Selecting Netbanking bank: %s", bank_name)
        bank_option.click(timeout=self.timeout_ms)

        try:
            pay_btn = self.find_resilient_locator(frame, self.PAY_SUBMIT_SELECTORS, timeout=3000)
            pay_btn.click(timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            pass

        # Checkout v2 may prompt for email after bank selection.
        try:
            email_el = self.find_resilient_locator(frame, self.EMAIL_INPUT_SELECTORS, timeout=2500)
            email_el.fill(self.settings.test_recipient_email, timeout=self.timeout_ms)
            pay_btn = self.find_resilient_locator(frame, self.PAY_SUBMIT_SELECTORS, timeout=3000)
            pay_btn.click(timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            pass

        self._assert_bank_simulator_visible(frame, initial_url)

    def _assert_bank_simulator_visible(self, frame: FrameLocator, initial_url: str) -> None:
        """Verify bank authentication screen in popup, redirected page, or checkout iframe."""
        for open_page in self.page.context.pages:
            if open_page.url != initial_url and "razorpay.com/demo" not in open_page.url:
                self.logger.info("Confirmed Netbanking redirect to bank portal: %s", open_page.url)
                return
            try:
                bank_el = self.find_resilient_locator(
                    open_page, self.BANK_DEMO_INDICATORS, timeout=4000
                )
                if bank_el.is_visible():
                    self.logger.info("Confirmed Netbanking authentication screen on page.")
                    return
            except PlaywrightTimeoutError:
                continue

        if self.page.url != initial_url:
            assert re.search(r"bank|hdfc|icici|sbi|axis|kotak|acs|auth", self.page.url, re.IGNORECASE), (
                f"Unexpected Netbanking redirect URL: {self.page.url}"
            )
            return

        bank_el = self.find_resilient_locator(frame, self.BANK_DEMO_INDICATORS, timeout=10000)
        assert bank_el.is_visible(), "Expected Razorpay Netbanking authentication screen."

    def pay_with_upi_to_collect_screen(self, upi_id: str) -> None:
        """Select UPI inside Razorpay modal, submit VPA if shown, and assert QR/collect screen."""
        frame = self._get_frame()
        if frame.locator("#overlay-backdrop").is_visible():
            self._complete_contact_step_if_present(frame)

        upi_method = self.find_resilient_locator(frame, self.UPI_METHOD_SELECTORS)
        upi_method.click(timeout=self.timeout_ms)

        try:
            upi_input = self.find_resilient_locator(frame, self.UPI_INPUT_SELECTORS, timeout=3000)
            self.logger.info("Entering Razorpay UPI VPA: ***")
            upi_input.fill(upi_id, timeout=self.timeout_ms)
            try:
                email_el = self.find_resilient_locator(
                    frame, self.EMAIL_INPUT_SELECTORS, timeout=1500
                )
                email_el.fill(self.settings.test_recipient_email, timeout=self.timeout_ms)
            except PlaywrightTimeoutError:
                pass
            submit_btn = self.find_resilient_locator(frame, self.PAY_SUBMIT_SELECTORS, timeout=4000)
            submit_btn.click(timeout=self.timeout_ms)
        except PlaywrightTimeoutError:
            self.logger.info("UPI QR / app intent panel active without explicit VPA input.")

        collect_el = self.find_resilient_locator(frame, self.UPI_COLLECT_INDICATORS, timeout=10000)
        assert collect_el.is_visible(), "Expected Razorpay UPI QR or collect approval screen."
        self.logger.info("Confirmed Razorpay UPI 2FA/collect screen.")
