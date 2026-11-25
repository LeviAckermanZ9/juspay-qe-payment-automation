"""Base Page Object for Appium Android mobile automation."""

from __future__ import annotations

import re

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import (
    InvalidElementStateException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import get_logger


class BaseMobilePage:
    """Base wrapper around Appium's WebDriver with explicit waits and masked logging."""

    def __init__(self, driver: WebDriver, timeout_sec: float = 15.0) -> None:
        self.driver = driver
        self.timeout_sec = timeout_sec
        self.logger = get_logger(self.__class__.__name__)

    def find_visible(
        self,
        by: str,
        locator: str,
        timeout: float | None = None,
    ) -> WebElement:
        """Wait explicitly until an element is visible and return it."""
        effective_timeout = timeout if timeout is not None else self.timeout_sec
        wait = WebDriverWait(self.driver, effective_timeout)
        return wait.until(EC.visibility_of_element_located((by, locator)))

    def find_resilient_element(
        self,
        locators: list[tuple[str, str]],
        timeout: float | None = None,
    ) -> WebElement:
        """Evaluate primary Android locators first and fall back to secondary selectors."""
        if not locators:
            raise ValueError("locators list must contain at least one (by, selector) tuple.")

        effective_timeout = timeout if timeout is not None else self.timeout_sec
        per_locator_timeout = max(2.0, effective_timeout / len(locators))
        attempted: list[str] = []

        for by, locator in locators:
            attempted.append(f"{by}={locator}")
            try:
                element = self.find_visible(by, locator, timeout=per_locator_timeout)
                self.logger.info("Matched resilient mobile locator: %s=%s", by, locator)
                return element
            except TimeoutException:
                continue

        raise TimeoutException(
            f"None of the resilient mobile locators became visible within "
            f"{effective_timeout:.1f}s: {attempted}"
        )

    def click_element(
        self,
        by: str,
        locator: str,
        timeout: float | None = None,
    ) -> None:
        """Wait until an element is clickable and tap it."""
        effective_timeout = timeout if timeout is not None else self.timeout_sec
        wait = WebDriverWait(self.driver, effective_timeout)
        element = wait.until(EC.element_to_be_clickable((by, locator)))
        self.logger.info("Tapping element (%s=%s)", by, locator)
        element.click()

    def click_resilient(
        self,
        locators: list[tuple[str, str]],
        timeout: float | None = None,
    ) -> None:
        """Locate an element using resilient fallback selectors and tap it."""
        element = self.find_resilient_element(locators, timeout=timeout)
        element.click()

    def send_keys(
        self,
        by: str,
        locator: str,
        value: str,
        mask_log: bool = False,
        clear_first: bool = True,
        timeout: float | None = None,
    ) -> None:
        """Wait for an input field to be visible and enter text."""
        element = self.find_visible(by, locator, timeout=timeout)
        logged_value = "***" if mask_log else value
        self.logger.info("Entering text into (%s=%s): %s", by, locator, logged_value)
        if clear_first:
            element.clear()
        element.send_keys(value)

    def send_keys_resilient(
        self,
        locators: list[tuple[str, str]],
        value: str,
        mask_log: bool = False,
        clear_first: bool = True,
        timeout: float | None = None,
    ) -> None:
        """Focus input via resilient selectors, handle wrapper/TextView nodes, and hide keyboard."""
        element = self.find_resilient_element(locators, timeout=timeout)
        logged_value = "***" if mask_log else value
        self.logger.info("Entering text into resilient mobile input: %s", logged_value)

        # Click first so floating-label/Material wrappers transfer focus to the underlying EditText.
        element.click()

        try:
            if clear_first:
                element.clear()
            element.send_keys(value)
        except InvalidElementStateException:
            self.logger.info(
                "Matched element is not directly editable; resolving focused EditText fallback"
            )
            self._send_keys_to_focused_fallback(value, clear_first=clear_first)
        finally:
            self.hide_keyboard_safe()

    def _send_keys_to_focused_fallback(self, value: str, clear_first: bool = True) -> None:
        """Type into the active focused EditText, or fall back to ActionChains if unavailable."""
        focused_candidates: list[tuple[str, str]] = [
            (AppiumBy.XPATH, "//android.widget.EditText[@focused='true']"),
            (AppiumBy.XPATH, "//*[@focused='true']"),
        ]
        for by, locator in focused_candidates:
            try:
                focused_el = self.find_visible(by, locator, timeout=2.0)
                if clear_first:
                    focused_el.clear()
                focused_el.send_keys(value)
                return
            except (TimeoutException, InvalidElementStateException):
                continue

        self.logger.info("Using ActionChains fallback for focused input entry")
        ActionChains(self.driver).send_keys(value).perform()

    def scroll_to_text(self, text: str) -> WebElement:
        """Scroll an Android scrollable container until an element containing text is visible."""
        escaped_text = text.replace('"', '\\"')
        ui_scrollable = (
            "new UiScrollable(new UiSelector().scrollable(true))"
            f'.scrollIntoView(new UiSelector().textContains("{escaped_text}"))'
        )
        self.logger.info("Scrolling to text: %s", text)
        return self.find_visible(AppiumBy.ANDROID_UIAUTOMATOR, ui_scrollable)

    def hide_keyboard_safe(self) -> None:
        """Dismiss the Android soft keyboard if open, ignoring inactive-keyboard errors."""
        try:
            self.driver.hide_keyboard()
            self.logger.info("Dismissed Android soft keyboard")
        except WebDriverException:
            pass

    def wait_for_text_or_element(
        self,
        text_substring: str | None = None,
        locators: list[tuple[str, str]] | None = None,
        timeout: float | None = None,
    ) -> WebElement:
        """Wait explicitly until either a text substring or any candidate locator is visible."""
        candidates: list[tuple[str, str]] = list(locators or [])
        if text_substring is not None:
            escaped = text_substring.replace('"', '\\"')
            candidates.insert(
                0,
                (
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{escaped}")',
                ),
            )
        if not candidates:
            raise ValueError("Provide at least one of 'text_substring' or 'locators'.")

        return self.find_resilient_element(candidates, timeout=timeout)

    def is_displayed(
        self,
        by: str,
        locator: str,
        timeout: float | None = 3.0,
    ) -> bool:
        """Return True if the element is visible within the timeout, else False."""
        try:
            self.find_visible(by, locator, timeout=timeout)
            return True
        except TimeoutException:
            return False

    @staticmethod
    def extract_amount(raw_text: str) -> float:
        """Extract numeric monetary value from text such as 'To Pay Rs. 249.00'."""
        cleaned = raw_text.replace(",", "")
        match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
        if not match:
            raise ValueError(f"Could not extract numeric amount from {raw_text!r}")
        return float(match.group(1))
