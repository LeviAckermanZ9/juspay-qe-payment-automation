# End-to-End Payment Workflow Automation Framework

## 1. Project Overview & Automation Scope
A modular Python Quality Engineering (QE) automation framework built to validate end-to-end payment checkout workflows across **Web** and **Android Mobile** platforms. The framework enforces a strict Page Object Model (POM), externalized environment configuration via `.env`, deterministic explicit waits (zero `time.sleep()` calls), masked sensitive logging, cross-screen amount integrity verification, and self-contained HTML test reporting with automatic failure screenshot capture.

### Automation Coverage Across Channels
- **Web Checkout Automation (Playwright):**
  - Gateway checkout journeys on **Razorpay Demo** (`https://razorpay.com/demo/`).
  - Covers **Credit/Debit Card**, **Netbanking**, and **Invalid Luhn Card** negative validation up to the Second Factor Authentication (2FA / OTP / bank authentication) screen without executing live financial charges.
- **Mobile Android Checkout Automation (Appium 2 + `UiAutomator2`):**
  - Native Android checkout journeys on **Swiggy** (`in.swiggy.android`) covering **Credit/Debit Card**, **Add New UPI ID** (in-app VPA flow), **Netbanking**, and **Invalid Card** negative validation.
  - Handles Material/Compose `TextView` label wrappers via automatic `EditText` focus transfer and `ActionChains` fallbacks, dismisses on-screen soft keyboards safely, and bypasses Swiggy's RBI card-tokenization bottom sheet (`"Pay without saving"`).
- **OTP Automation & End-to-End Completion:**
  - Android ADB SMS inbox polling (`content://sms/inbox`) synchronized against the Android device clock (`adb shell date +%s`) to prevent host-to-device clock skew and avoid reusing stale OTPs.
  - Includes an automated Android emulator SMS injection test (`adb emu sms send`), a Razorpay sandbox 2FA/ACS completion flow asserting `pay_...` Payment IDs, and a safety-gated live mobile E2E order completion test (`ENABLE_LIVE_OTP_E2E=false` by default).

---

## 2. Architecture & Repository Layout

```text
juspay-qe-payment-automation/
|-- config/
|   |-- __init__.py
|   |-- settings.py                      # Typed Settings dataclass loaded from .env
|-- pages/
|   |-- __init__.py
|   |-- web/
|   |   |-- __init__.py
|   |   |-- base_web_page.py             # Resilient locators, visible iframe switching, smart waits
|   |   |-- razorpay_demo_page.py        # Razorpay Checkout v2 iframe, popup/ACS & E2E confirmation
|   |-- mobile/
|       |-- __init__.py
|       |-- base_mobile_page.py          # Explicit waits, focus/EditText fallback & UiScrollable
|       |-- swiggy_cart_page.py          # Swiggy Cart To Pay capture & Proceed to Pay
|       |-- swiggy_payment_page.py       # Swiggy Card, RBI modal bypass, UPI, Netbanking & OTP
|-- tests/
|   |-- __init__.py
|   |-- conftest.py                      # Playwright/Appium fixtures, CLI flags & failure screenshots
|   |-- test_framework_smoke.py          # Core configuration and browser smoke test
|   |-- web/
|   |   |-- __init__.py
|   |   |-- test_sandbox_payments.py     # Razorpay Demo Card, Netbanking & negative card tests
|   |   |-- test_razorpay_e2e.py         # Razorpay Sandbox 2FA completion & Payment ID assertion
|   |-- mobile/
|       |-- __init__.py
|       |-- test_mobile_payments.py      # Prioritized Swiggy Android payment tests
|       |-- test_mobile_otp_e2e.py       # ADB SMS OTP inbox polling & gated live E2E test
|-- utils/
|   |-- __init__.py
|   |-- logger.py                        # Structured stdout and reports/execution.log logger
|   |-- otp_helper.py                    # Device-clock-synced ADB SMS OTP reader & regex parser
|-- reports/
|   |-- screenshots/
|       |-- .gitkeep
|-- .env.example                         # Documented environment variable template
|-- .gitignore                           # Ignores .env, caches, reports, IDE & local tool files
|-- pytest.ini                           # Pytest markers and self-contained HTML report options
|-- requirements.txt                     # Unpinned Python dependencies
|-- README.md
```

### Core Engineering Standards
- **Page Object Model (POM):** All selectors and interaction logic reside strictly in `pages/web/` and `pages/mobile/`; test modules in `tests/` contain only flow orchestration and assertions.
- **Multi-Locator Fallback Resolution:** `BaseWebPage.find_resilient_locator` and `BaseMobilePage.find_resilient_element` evaluate primary semantic/accessibility locators first and fall back to secondary attributes or `EditText` instance selectors.
- **Amount Integrity Verification:** Every checkout suite captures the payable total on the cart or gift card summary page and asserts parity against the payable amount displayed on the payment gateway sheet.
- **Sensitive Data Masking:** Card numbers, expiry dates, CVVs, UPI VPAs, and OTP codes are always masked (`***`) in stdout and file logs.
- **Zero Static Sleeps:** All synchronization uses Playwright auto-waiting/expectations, Selenium `WebDriverWait`, and bounded `time.monotonic()` + `threading.Event().wait()` polling loops.
- **Automatic Failure Evidence:** `pytest_runtest_makereport` in `tests/conftest.py` captures PNG screenshots on any Web or Mobile failure into `reports/screenshots/` and embeds them directly into `reports/test_report.html`.

---

## 3. Complete Test Coverage Matrix (All 12 Automated Tests)

| Test Name | File Path | Target App & Payment Method | Priority & Markers | Key QA Assertions |
| :--- | :--- | :--- | :--- | :--- |
| `test_framework_foundation_smoke` | `tests/test_framework_smoke.py` | Framework / Example Domain | `smoke` | Loads `Settings`, launches browser, asserts URL and link visibility |
| `test_sandbox_card_to_otp` | `tests/web/test_sandbox_payments.py` | Razorpay Demo / Credit-Debit Card | `P0` (`web`, `regression`, `p0`) | Modal amount > 0, two-step card entry, 2FA/OTP screen verification |
| `test_sandbox_upi_payment_flow` | `tests/web/test_sandbox_payments.py` | Razorpay Demo / UPI | `P0` (`web`, `regression`, `p0`) | Modal amount > 0, UPI method selection, QR or collect screen check |
| `test_sandbox_netbanking_to_bank_page` | `tests/web/test_sandbox_payments.py` | Razorpay Demo / Netbanking | `P1` (`web`, `regression`, `p1`) | HDFC Netbanking selection reaches bank authentication modal/portal |
| `test_sandbox_invalid_card_error` | `tests/web/test_sandbox_payments.py` | Razorpay Demo / Invalid Luhn Card | `P2` (`web`, `regression`, `p2`) | Malformed card input triggers inline `"Please enter a valid card number"` |
| `test_razorpay_sandbox_card_e2e_confirmation` | `tests/web/test_razorpay_e2e.py` | Razorpay Sandbox / Card E2E | `E2E` (`web`, `e2e`, `regression`) | Completes test OTP or Mock Bank `Success`, asserts `pay_...` Payment ID |
| `test_mobile_card_reaches_2fa_otp` | `tests/mobile/test_mobile_payments.py` | Swiggy Android / Credit-Debit Card | `P0` (`mobile`, `regression`, `p0`, `smoke`) | Cart `To Pay` parity, RBI sheet bypass, 3DS/OTP/WebView transition |
| `test_mobile_upi_payment_initiation` | `tests/mobile/test_mobile_payments.py` | Swiggy Android / Add New UPI ID | `P0` (`mobile`, `regression`, `p0`) | Cart `To Pay` parity, VPA entry, UPI collect approval timer screen |
| `test_mobile_netbanking_redirect` | `tests/mobile/test_mobile_payments.py` | Swiggy Android / Netbanking | `P1` (`mobile`, `regression`, `p1`) | Cart `To Pay` parity, bank selection, transition to bank 2FA screen |
| `test_mobile_invalid_card_validation` | `tests/mobile/test_mobile_payments.py` | Swiggy Android / Invalid Luhn Card | `P2` (`mobile`, `regression`, `p2`) | Bypasses RBI sheet, asserts inline/Toast error or no 2FA launch |
| `test_adb_sms_otp_inbox_retrieval_on_emulator` | `tests/mobile/test_mobile_otp_e2e.py` | Android Emulator / ADB SMS OTP | `E2E` (`mobile`, `e2e`) | Injects SMS via `adb emu sms send`, asserts device-clock-synced OTP match |
| `test_mobile_live_otp_e2e_order_confirmation` | `tests/mobile/test_mobile_otp_e2e.py` | Swiggy Android / Live Card E2E | `E2E` (`mobile`, `e2e`) | Gated by `ENABLE_LIVE_OTP_E2E=true`; submits live SMS OTP to order confirm |

---

## 4. Fresh-System Setup Guide (Step-by-Step)

### Step 1 - Clone Repository & Install Global Python Dependencies
Ensure **Python 3.11+** (3.10+ supported) is installed and available on the global `PATH`:
```powershell
git clone https://github.com/LeviAckermanZ9/juspay-qe-payment-automation.git
cd juspay-qe-payment-automation
pip install -r requirements.txt
```

### Step 2 - Install Playwright Browser
Install Playwright's Chromium binary:
```powershell
playwright install chromium
```
If Google Chrome or Microsoft Edge is already installed on the machine and bundled Chromium is absent, the framework automatically falls back to system `chrome` or `msedge` (or you can pin `BROWSER_CHANNEL=chrome` or `BROWSER_CHANNEL=msedge` in `.env`).

### Step 3 - Android SDK, ADB & Device/Emulator Setup
1. Install **Android SDK Platform-Tools** (standalone or via Android Studio) and add the `platform-tools` directory to your system `PATH`.
2. Boot an Android Virtual Device (for example, Pixel 7 with API 34/35) or connect a physical Android device over USB with **Developer Options** and **USB Debugging** enabled.
3. Verify ADB recognizes the target device and note its UDID (e.g., `emulator-5554`):
   ```powershell
   adb devices
   ```

### Step 4 - Appium 2 & `UiAutomator2` Setup
1. Install **Node.js** (LTS), then install Appium 2 and the `UiAutomator2` driver globally:
   ```powershell
   npm install -g appium
   appium driver install uiautomator2
   ```
2. Verify the driver is installed:
   ```powershell
   appium driver list --installed
   ```

### Step 5 - Target Android App Preparation (Swiggy)
1. Install Swiggy (`in.swiggy.android`) on the emulator/device (or provide a local `.apk` path via `APK_PATH` in `.env`).
2. Launch Swiggy once manually, complete login, and set a delivery address. With `NO_RESET=true`, Appium preserves your authenticated session across test runs.
3. Add 1 low-cost item to the Swiggy Cart so cart-to-payment journeys execute deterministically (if the cart is empty, `SwiggyCartPage` attempts a quick item add automatically).
4. With Swiggy open on screen, verify its active package and launcher activity:
   - Windows CMD / PowerShell:
     ```powershell
     adb shell dumpsys window | findstr mCurrentFocus
     ```
   - macOS / Linux:
     ```bash
     adb shell dumpsys window | grep mCurrentFocus
     ```

---

## 5. Environment Configuration Reference (`.env`)

Create your local `.env` file from the template before running tests:
- **Windows PowerShell:**
  ```powershell
  Copy-Item .env.example .env
  ```
- **Windows CMD:**
  ```cmd
  copy .env.example .env
  ```
- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

### Configuration Variables (`config/settings.py`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `RAZORPAY_DEMO_URL` | `https://razorpay.com/demo/` | Target Razorpay checkout URL (live demo or test-mode URL) |
| `WEB_BASE_URL` | `https://razorpay.com/demo/` | Generic primary web base URL |
| `SANDBOX_BASE_URL` | `https://razorpay.com/demo/` | Generic sandbox base URL |
| `BROWSER` | `chromium` | Playwright engine (`chromium`, `firefox`, or `webkit`) |
| `BROWSER_CHANNEL` | *(empty)* | Optional system browser channel (`chrome` or `msedge`) |
| `HEADLESS` | `false` | Run browser headless (`true`) or headed (`false`) |
| `DEFAULT_TIMEOUT_MS` | `15000` | Default Playwright and Appium (`ms / 1000`) explicit wait timeout |
| `TEST_CARD_NUMBER` | `4111111111111111` | Test card number used for Card 2FA flows |
| `TEST_CARD_EXPIRY` | `12/28` | Card expiry (`MM/YY`) |
| `TEST_CARD_CVV` | `123` | Card security code |
| `TEST_CARD_HOLDER` | `Test User` | Cardholder name |
| `TEST_INVALID_CARD_NUMBER` | `4111111111111112` | Invalid Luhn checksum card number for P2 negative tests |
| `TEST_UPI_ID` | `success@razorpay` | UPI VPA entered in UPI payment flows |
| `TEST_NETBANKING_BANK` | `HDFC` | Target bank name for Netbanking flows (`HDFC`, `ICICI`, `SBI`) |
| `TEST_OTP_CODE` | `123456` | General placeholder test OTP value |
| `SANDBOX_TEST_OTP` | `123456` | OTP submitted during Razorpay test-mode 2FA verification |
| `OTP_POLL_TIMEOUT_SECONDS` | `30` | Maximum polling window (seconds) for `fetch_latest_sms_otp` |
| `ENABLE_LIVE_OTP_E2E` | `false` | Safety gate for real-money mobile checkout (`true` to enable) |
| `TEST_RECIPIENT_NAME` | `QA Test User` | Gift card recipient name for web checkout forms |
| `TEST_RECIPIENT_EMAIL` | `qa.test@example.com` | Contact/receipt email for checkout forms |
| `TEST_RECIPIENT_MOBILE` | `9820098200` | Non-sequential 10-digit mobile number for checkout forms |
| `TEST_SENDER_NAME` | `QA Automation` | Gift card sender name for web checkout forms |
| `APPIUM_SERVER_URL` | `http://127.0.0.1:4723` | Running Appium 2 server endpoint |
| `ANDROID_UDID` | *(empty)* | Target Android device/emulator ID from `adb devices` |
| `ANDROID_PLATFORM_VERSION` | `14.0` | Android OS version on the target device/emulator |
| `APP_PACKAGE` | `in.swiggy.android` | Android application package name |
| `APP_ACTIVITY` | *(empty)* | Swiggy launcher activity (e.g., `.HomeIcon` or full activity name) |
| `APP_WAIT_ACTIVITY` | `in.swiggy.android.*` | Wildcard wait activity pattern for splash-to-home transitions |
| `APK_PATH` | *(empty)* | Optional path to a local `.apk` for fresh app installation |
| `NO_RESET` | `true` | Preserves logged-in app data and session between test runs |
| `AUTO_GRANT_PERMISSIONS` | `true` | Automatically grants Android runtime app permissions |

---

## 6. Complete Test Execution Commands Reference

### Discovery & Smoke Verification
```powershell
# Verify all 12 tests and markers collect cleanly
pytest --collect-only

# Run critical P0 smoke tests
pytest -m p0 -v
```

### Web Payment Suite
```powershell
# Run the full Web suite
pytest -m web -v

# Run Web tests filtered by priority
pytest -m "web and p0" -v
pytest -m "web and p1" -v
pytest -m "web and p2" -v

# Run Web tests in headless mode (PowerShell session override)
$env:HEADLESS="true"; pytest -m web -v
```

### Mobile Android Payment Suite
Start Appium in **Terminal 1**:
```powershell
appium
```

Run Mobile tests in **Terminal 2**:
```powershell
# Run the full Mobile Android suite
pytest -m mobile -v

# Run Mobile tests filtered by priority
pytest -m "mobile and p0" -v
pytest -m "mobile and p1" -v
pytest -m "mobile and p2" -v
```

### Bonus OTP & End-to-End Suite
```powershell
# Run all E2E tests (ADB emulator SMS test + Razorpay E2E; live order skips unless ENABLE_LIVE_OTP_E2E=true)
pytest -m e2e -v

# Run only the ADB emulator SMS injection & OTP extraction test
pytest tests/mobile/test_mobile_otp_e2e.py -k "emulator" -v
```

### Run Any Individual Test by Keyword
```powershell
pytest -k "<test_name>" -v
```

---

## 7. Reports, Logs & Troubleshooting

### Generated Execution Evidence
- **HTML Report:** `reports/test_report.html` - self-contained Pytest HTML report generated automatically via `pytest.ini` (`--html=reports/test_report.html --self-contained-html`).
- **Execution Log:** `reports/execution.log` - chronological console and file logs with card numbers, CVVs, UPI VPAs, and OTPs masked as `***`.
- **Failure Screenshots:** `reports/screenshots/` - automatically populated via `pytest_runtest_makereport` on any Web (`Page.screenshot`) or Mobile (`driver.save_screenshot`) failure and embedded directly inside `reports/test_report.html`.

### Troubleshooting Guide
- **Swiggy Compose / Material Input Focus (`InvalidElementStateException`):**
  - On Swiggy's "Add New Card" form, text locators such as `"Card Number"` or `"Valid Through (MM/YY)"` can match an inner `TextView` label rather than the editable `EditText`. `BaseMobilePage.send_keys_resilient` handles this by clicking the matched element first, catching `InvalidElementStateException`, resolving `//android.widget.EditText[@focused='true']` (or falling back to `ActionChains`), and dismissing the soft keyboard afterward so `Proceed` stays visible.
- **Swiggy RBI Card-Tokenization Modal:**
  - Tapping `Proceed` on Swiggy's card form can open an RBI tokenization bottom sheet (`"Save your card as per RBI guidelines"` / `"Save Card & Pay"`). `SwiggyPaymentPage._handle_rbi_tokenization_sheet` detects this modal and taps `"Pay without saving"` so card validation and 2FA flows proceed without attempting card tokenization.
- **Razorpay Demo Live-Key vs. Sandbox Behavior:**
  - The public `https://razorpay.com/demo/` endpoint executes Checkout v2 in live production mode (`traffic_env=production`) and declines synthetic test cards (`4111111111111111`) with `"Payment could not be completed"` / `"Payment declined"`. `RazorpayDemoPage` detects this state immediately via `_is_live_card_declined()` and skips `test_razorpay_sandbox_card_e2e_confirmation` cleanly with an informative message. Point `RAZORPAY_DEMO_URL` in `.env` to a Razorpay test-mode checkout page (`rzp_test_...`) to exercise the Mock Bank `Success` simulator and `pay_...` confirmation end to end.
- **Android Emulator Clock Synchronization:**
  - `adb emu sms send` timestamps incoming rows in `content://sms/inbox` using the emulator's system clock, which can drift from the host OS clock. `utils/otp_helper.py` uses `get_device_timestamp_ms(udid)` (`adb shell date +%s` * 1000) with a 2-second buffer (`- 2000`) so newly injected or live bank OTPs are never filtered out.
- **Physical Device SMS Read Permissions:**
  - On physical Android 10+ devices (especially MIUI/ColorOS), enable **"USB Debugging (Security Settings)"** in Developer Options if `adb shell content query --uri content://sms/inbox` fails due to shell permission restrictions.
