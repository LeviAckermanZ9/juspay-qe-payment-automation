"""Pytest configuration, runtime CLI overrides, fixtures, and failure screenshot hooks."""

from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest
from playwright.sync_api import Browser, Error as PlaywrightError, Page, Playwright, sync_playwright

from config.settings import Settings, get_settings
from utils.logger import get_logger

if TYPE_CHECKING:
    from appium.webdriver.webdriver import WebDriver as AppiumWebDriver

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "screenshots"
logger = get_logger("conftest")


def pytest_configure(config: pytest.Config) -> None:
    """Ensure report and failure screenshot directories exist on fresh checkouts."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register runtime CLI flags to override .env browser settings."""
    parser.addoption(
        "--headless",
        action="store",
        default=None,
        choices=["true", "false"],
        help="Override HEADLESS setting from .env ('true' or 'false').",
    )
    parser.addoption(
        "--browser",
        action="store",
        default=None,
        choices=["chromium", "firefox", "webkit"],
        help="Override BROWSER setting from .env ('chromium', 'firefox', or 'webkit').",
    )


@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    """Load framework settings from .env with optional CLI overrides."""
    cfg = get_settings()

    cli_headless = request.config.getoption("--headless")
    if cli_headless is not None:
        cfg.headless = cli_headless.lower() == "true"

    cli_browser = request.config.getoption("--browser")
    if cli_browser is not None:
        cfg.browser = cli_browser.lower()

    return cfg


def _launch_browser(playwright: Playwright, settings: Settings) -> Browser:
    """Launch configured browser, falling back to system Chrome/Edge if bundled Chromium is absent."""
    browser_launcher = getattr(playwright, settings.browser, None)
    if browser_launcher is None:
        raise ValueError(f"Unsupported Playwright browser: {settings.browser!r}")

    if settings.browser_channel:
        logger.info("Using configured browser channel: %s", settings.browser_channel)
        return browser_launcher.launch(
            headless=settings.headless,
            channel=settings.browser_channel,
        )

    try:
        return browser_launcher.launch(headless=settings.headless)
    except PlaywrightError as exc:
        if settings.browser != "chromium" or "Executable doesn't exist" not in str(exc):
            raise
        for channel in ("chrome", "msedge"):
            try:
                logger.info(
                    "Bundled Chromium not installed; falling back to system channel=%s",
                    channel,
                )
                return browser_launcher.launch(headless=settings.headless, channel=channel)
            except PlaywrightError:
                continue
        raise


@pytest.fixture(scope="function")
def web_page(settings: Settings) -> Generator[Page, None, None]:
    """Provide a clean Playwright Page per test and tear down browser resources."""
    logger.info(
        "Launching Playwright browser=%s (headless=%s)",
        settings.browser,
        settings.headless,
    )
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, settings)
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
        )
        context.set_default_timeout(settings.default_timeout_ms)
        page = context.new_page()

        try:
            yield page
        finally:
            logger.info("Closing Playwright browser context")
            context.close()
            browser.close()


@pytest.fixture(scope="function")
def appium_driver(settings: Settings) -> Generator[AppiumWebDriver, None, None]:
    """Provide an Appium UiAutomator2 Android driver per test and quit cleanly on teardown."""
    from appium import webdriver as appium_webdriver
    from appium.options.android import UiAutomator2Options

    settings.validate_for_suite("mobile")

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.udid = settings.android_udid
    options.platform_version = settings.android_platform_version
    options.app_package = settings.app_package
    options.app_activity = settings.app_activity
    options.app_wait_activity = settings.app_wait_activity
    options.no_reset = settings.no_reset
    options.auto_grant_permissions = settings.auto_grant_permissions
    options.new_command_timeout = 120
    if settings.apk_path:
        options.app = settings.apk_path

    logger.info(
        "Connecting Appium UiAutomator2 session (server=%s, udid=%s, package=%s)",
        settings.appium_server_url,
        settings.android_udid,
        settings.app_package,
    )
    driver = appium_webdriver.Remote(
        command_executor=settings.appium_server_url,
        options=options,
    )
    try:
        yield driver
    finally:
        logger.info("Quitting Appium Android driver session")
        driver.quit()


def _sanitize_filename(nodeid: str) -> str:
    """Convert a Pytest nodeid into a safe filename stem."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", nodeid).strip("_")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[None],
) -> Generator[None, pytest.TestReport, None]:
    """Capture a screenshot on test failure and attach it to the pytest-html report."""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_sanitize_filename(item.nodeid)}_{timestamp}.png"
    screenshot_path = SCREENSHOTS_DIR / filename

    png_bytes: bytes | None = None
    web_page_obj = item.funcargs.get("web_page")
    mobile_driver_obj = item.funcargs.get("appium_driver") or item.funcargs.get("mobile_driver")

    try:
        if web_page_obj is not None:
            png_bytes = web_page_obj.screenshot(path=str(screenshot_path), full_page=True)
        elif mobile_driver_obj is not None:
            mobile_driver_obj.save_screenshot(str(screenshot_path))
            png_bytes = screenshot_path.read_bytes()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to capture failure screenshot for %s: %s", item.nodeid, exc)
        return

    if png_bytes is None:
        return

    logger.info("Saved failure screenshot: %s", screenshot_path)
    html_plugin = item.config.pluginmanager.getplugin("html")
    if html_plugin is not None:
        from pytest_html import extras

        encoded = base64.b64encode(png_bytes).decode("utf-8")
        extra_list = getattr(report, "extras", [])
        extra_list.append(extras.png(encoded, name=filename))
        report.extras = extra_list
