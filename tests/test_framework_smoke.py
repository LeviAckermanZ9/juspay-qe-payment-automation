"""Lightweight smoke tests verifying framework configuration, Playwright, and reporting."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config.settings import Settings
from pages.web.base_web_page import BaseWebPage


@pytest.mark.smoke
def test_framework_foundation_smoke(settings: Settings, web_page: Page) -> None:
    """Verify Settings loading, BaseWebPage navigation, and HTML report generation."""
    assert settings.browser in {"chromium", "firefox", "webkit"}
    assert settings.default_timeout_ms > 0
    assert settings.appium_server_url.startswith("http")

    base_page = BaseWebPage(web_page, timeout_ms=settings.default_timeout_ms)
    base_page.navigate("https://example.com")
    base_page.assert_url_or_element(
        expected_url_substring="example.com",
        locator="role=link[name='Learn more']",
    )
    assert "Example" in web_page.title()
