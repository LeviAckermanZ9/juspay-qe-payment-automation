"""Page Object for Swiggy Android Cart & Bill Details workflow."""

from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException

from config.settings import Settings
from pages.mobile.base_mobile_page import BaseMobilePage


class SwiggyCartPage(BaseMobilePage):
    """Automates Swiggy cart navigation, overlay dismissal, To Pay capture, and payment entry."""

    OPTIONAL_OVERLAY_DISMISS_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "Close"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)Not Now|Maybe Later|Skip|Dismiss|Got it")'),
        (AppiumBy.ID, "in.swiggy.android:id/close_btn"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*close.*|.*dismiss.*")'),
    ]

    VIEW_CART_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "View Cart"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("View Cart")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("View Cart")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^Cart$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*cart.*")'),
    ]

    EMPTY_CART_INDICATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("cart is empty")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Your cart is empty")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Browse Restaurants")'),
    ]

    QUICK_ADD_ITEM_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^ADD$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Add")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*add_button.*|.*add_to_cart.*")'),
    ]

    FIRST_RESTAURANT_OR_FOOD_TAB: list[tuple[str, str]] = [
        (AppiumBy.ACCESSIBILITY_ID, "Food"),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i)^Food$")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*restaurant.*|.*card.*")'),
    ]

    TO_PAY_AMOUNT_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*to_pay.*|.*grand_total.*|.*payable.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*(?:\\u20b9|Rs\\.?)\\s*[0-9,]+.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("To Pay")'),
    ]

    PROCEED_TO_PAY_LOCATORS: list[tuple[str, str]] = [
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Proceed to Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Select Payment Method")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches("(?i).*Proceed.*Pay.*|.*Pay.*")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().descriptionContains("Proceed to Pay")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceIdMatches(".*proceed_to_pay.*|.*checkout_cta.*")'),
    ]

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        super().__init__(driver, timeout_sec=settings.default_timeout_sec)
        self.settings = settings
        self.to_pay_amount: float = 0.0

    def dismiss_optional_overlays(self) -> None:
        """Dismiss promotional bottom sheets or permission dialogs if displayed."""
        for by, locator in self.OPTIONAL_OVERLAY_DISMISS_LOCATORS:
            try:
                element = self.find_visible(by, locator, timeout=2.0)
                self.logger.info("Dismissing optional Swiggy overlay via %s=%s", by, locator)
                element.click()
                return
            except TimeoutException:
                continue

    def open_cart_or_populate(self) -> None:
        """Open existing Swiggy cart, or add a quick item if the cart is empty."""
        self.dismiss_optional_overlays()

        try:
            self.click_resilient(self.VIEW_CART_LOCATORS, timeout=8.0)
        except TimeoutException:
            self._populate_quick_cart_item()
            self.click_resilient(self.VIEW_CART_LOCATORS, timeout=10.0)

        if self._is_cart_empty():
            self._populate_quick_cart_item()
            self.click_resilient(self.VIEW_CART_LOCATORS, timeout=10.0)

    def _is_cart_empty(self) -> bool:
        """Check whether the opened cart screen indicates an empty cart."""
        for by, locator in self.EMPTY_CART_INDICATORS:
            if self.is_displayed(by, locator, timeout=2.5):
                self.logger.info("Detected empty cart indicator: %s", locator)
                return True
        return False

    def _populate_quick_cart_item(self) -> None:
        """Navigate to food listing and add the first available item to the cart."""
        self.logger.info("Attempting quick item add to populate Swiggy cart")
        try:
            self.click_resilient(self.FIRST_RESTAURANT_OR_FOOD_TAB, timeout=6.0)
        except TimeoutException:
            pass

        self.click_resilient(self.QUICK_ADD_ITEM_LOCATORS, timeout=10.0)

    def capture_to_pay_amount(self) -> float:
        """Locate the Bill Details 'To Pay' row and capture the numeric payable amount."""
        try:
            self.scroll_to_text("To Pay")
        except TimeoutException:
            self.logger.info("'To Pay' section already in view or non-scrollable layout.")

        amount_el = self.find_resilient_element(self.TO_PAY_AMOUNT_LOCATORS, timeout=10.0)
        raw_text = amount_el.text or amount_el.get_attribute("content-desc") or ""
        self.to_pay_amount = self.extract_amount(raw_text)
        assert self.to_pay_amount > 0, f"Expected positive To Pay amount, got {self.to_pay_amount}"
        self.logger.info("Captured Swiggy Cart To Pay amount: %.2f", self.to_pay_amount)
        return self.to_pay_amount

    def proceed_to_payment_sheet(self) -> None:
        """Tap Proceed to Pay / Select Payment Method CTA to enter the payment sheet."""
        self.logger.info("Proceeding from Swiggy Cart to payment selection sheet")
        self.click_resilient(self.PROCEED_TO_PAY_LOCATORS, timeout=12.0)

    def open_cart_and_proceed_to_payment(self) -> float:
        """Execute Cart opening, To Pay capture, and navigation to the payment sheet."""
        self.open_cart_or_populate()
        amount = self.capture_to_pay_amount()
        self.proceed_to_payment_sheet()
        return amount
