"""Base Page Object for Playwright web automation with resilient locator resolution."""

from __future__ import annotations

import re

from playwright.sync_api import (
    FrameLocator,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from utils.logger import get_logger

_ROLE_WITH_NAME_RE = re.compile(r"^role=([a-zA-Z0-9_-]+)\[name=(['\"]?)(.+?)\2\]$")


class BaseWebPage:
    """Base wrapper around Playwright's Page with smart waits and masked logging."""

    def __init__(self, page: Page, timeout_ms: int = 15000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms
        self.logger = get_logger(self.__class__.__name__)

    def _resolve_locator(self, locator: str | Locator) -> Locator:
        """Convert a selector string into a Playwright Locator if needed."""
        if isinstance(locator, str):
            return self._build_locator(self.page, locator)
        return locator

    @staticmethod
    def _build_locator(page_or_frame: Page | FrameLocator, selector: str | Locator) -> Locator:
        """Build a Playwright Locator from semantic prefixes or standard CSS/XPath selectors."""
        if not isinstance(selector, str):
            return selector

        if selector.startswith("role="):
            match = _ROLE_WITH_NAME_RE.match(selector)
            if match:
                role_name = match.group(1)
                accessible_name = match.group(3)
                return page_or_frame.get_by_role(role_name, name=accessible_name).first
            role_only = selector.removeprefix("role=").strip()
            return page_or_frame.get_by_role(role_only).first

        if selector.startswith("placeholder="):
            return page_or_frame.get_by_placeholder(selector.removeprefix("placeholder=")).first

        if selector.startswith("label="):
            return page_or_frame.get_by_label(selector.removeprefix("label=")).first

        if selector.startswith("text="):
            raw_text = selector.removeprefix("text=")
            # Support Playwright regex syntax 'text=/pattern/flags' via locator engine.
            if raw_text.startswith("/"):
                return page_or_frame.locator(selector).first
            return page_or_frame.get_by_text(raw_text).first

        if selector.startswith("testid="):
            return page_or_frame.get_by_test_id(selector.removeprefix("testid=")).first

        return page_or_frame.locator(selector).first

    def navigate(self, url: str) -> None:
        """Navigate to the target URL and wait for DOM content to load."""
        self.logger.info("Navigating to URL: %s", url)
        self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)

    def wait_for_visible(self, locator: str | Locator, timeout: int | None = None) -> Locator:
        """Wait until the target element is visible and return its Locator."""
        effective_timeout = timeout if timeout is not None else self.timeout_ms
        target = self._resolve_locator(locator)
        target.wait_for(state="visible", timeout=effective_timeout)
        return target

    def click_element(self, locator: str | Locator, timeout: int | None = None) -> None:
        """Wait for an element to be visible and click it."""
        effective_timeout = timeout if timeout is not None else self.timeout_ms
        target = self.wait_for_visible(locator, timeout=effective_timeout)
        self.logger.info("Clicking element: %s", locator)
        target.click(timeout=effective_timeout)

    def fill_input(
        self,
        locator: str | Locator,
        value: str,
        mask_log: bool = False,
        timeout: int | None = None,
    ) -> None:
        """Wait for an input to be visible, clear it, and fill the provided value."""
        effective_timeout = timeout if timeout is not None else self.timeout_ms
        target = self.wait_for_visible(locator, timeout=effective_timeout)
        logged_value = "***" if mask_log else value
        self.logger.info("Filling input %s with value: %s", locator, logged_value)
        target.fill(value, timeout=effective_timeout)

    def find_resilient_locator(
        self,
        page_or_frame: Page | FrameLocator,
        selectors: list[str | Locator],
        timeout: int | None = None,
    ) -> Locator:
        """Evaluate primary semantic locators first and fall back to secondary attributes."""
        if not selectors:
            raise ValueError("selectors list must contain at least one locator.")

        effective_timeout = timeout if timeout is not None else self.timeout_ms
        per_candidate_timeout = max(1500, effective_timeout // len(selectors))
        attempted: list[str] = []

        for selector in selectors:
            attempted.append(str(selector))
            candidate = self._build_locator(page_or_frame, selector)
            try:
                candidate.wait_for(state="visible", timeout=per_candidate_timeout)
                self.logger.info("Matched resilient locator: %s", selector)
                return candidate
            except PlaywrightTimeoutError:
                continue

        raise PlaywrightTimeoutError(
            f"None of the resilient locators became visible within {effective_timeout} ms: "
            f"{attempted}"
        )

    def wait_for_url_change(self, old_url: str, timeout: int | None = None) -> str:
        """Wait for the page URL to transition away from old_url and return the new URL."""
        effective_timeout = timeout if timeout is not None else self.timeout_ms
        self.logger.info("Waiting for URL transition away from: %s", old_url)
        self.page.wait_for_url(lambda current: current != old_url, timeout=effective_timeout)
        new_url = self.page.url
        self.logger.info("URL transitioned to: %s", new_url)
        return new_url

    def switch_to_payment_frame(
        self,
        frame_selectors: list[str],
        timeout: int | None = None,
    ) -> FrameLocator:
        """Locate the first visible payment gateway iframe and return its FrameLocator."""
        if not frame_selectors:
            raise ValueError("frame_selectors must contain at least one iframe selector.")

        effective_timeout = timeout if timeout is not None else self.timeout_ms
        # Give primary frame selector most of the budget so slow cold-load iframes do not fall through.
        primary_timeout = max(8000, int(effective_timeout * 0.75)) if len(frame_selectors) > 1 else effective_timeout
        fallback_timeout = max(2500, effective_timeout // len(frame_selectors))

        for index, selector in enumerate(frame_selectors):
            visible_selector = (
                selector if ":visible" in selector else f"{selector}:visible"
            )
            step_timeout = primary_timeout if index == 0 else fallback_timeout
            try:
                self.page.locator(visible_selector).first.wait_for(
                    state="visible", timeout=step_timeout
                )
                self.logger.info("Switched to visible payment gateway iframe: %s", visible_selector)
                return self.page.frame_locator(visible_selector).first
            except PlaywrightTimeoutError:
                continue

        raise PlaywrightTimeoutError(
            f"Unable to locate visible payment iframe from candidates: {frame_selectors}"
        )

    def get_frame_locator(self, iframe_selector: str) -> FrameLocator:
        """Wait for an iframe to attach and return a Playwright FrameLocator."""
        self.logger.info("Accessing iframe: %s", iframe_selector)
        self.page.locator(iframe_selector).first.wait_for(
            state="attached", timeout=self.timeout_ms
        )
        return self.page.frame_locator(iframe_selector).first

    def is_visible(self, locator: str | Locator, timeout: int | None = None) -> bool:
        """Return True if the element becomes visible within the timeout, else False."""
        effective_timeout = timeout if timeout is not None else 3000
        try:
            target = self._resolve_locator(locator)
            target.wait_for(state="visible", timeout=effective_timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def assert_url_or_element(
        self,
        expected_url_substring: str | None = None,
        locator: str | Locator | None = None,
        timeout: int | None = None,
    ) -> None:
        """Assert that either the current URL contains a substring or an element is visible."""
        if expected_url_substring is None and locator is None:
            raise ValueError("Provide at least one of 'expected_url_substring' or 'locator'.")

        effective_timeout = timeout if timeout is not None else self.timeout_ms

        if expected_url_substring is not None:
            self.logger.info("Asserting URL contains: %s", expected_url_substring)
            expect(self.page).to_have_url(
                re.compile(re.escape(expected_url_substring)),
                timeout=effective_timeout,
            )

        if locator is not None:
            self.logger.info("Asserting element is visible: %s", locator)
            target = self._resolve_locator(locator)
            expect(target).to_be_visible(timeout=effective_timeout)

    @staticmethod
    def extract_amount(raw_text: str) -> float:
        """Extract numeric monetary value from text such as 'Pay Rs. 100.00'."""
        cleaned = raw_text.replace(",", "")
        match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
        if not match:
            raise ValueError(f"Could not extract numeric amount from {raw_text!r}")
        return float(match.group(1))
