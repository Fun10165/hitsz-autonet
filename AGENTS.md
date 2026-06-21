# Repository Guidelines

**Generated:** 2026-06-17

## Project Overview

Automated HITSZ (Harbin Institute of Technology, Shenzhen) campus-network authentication — two independent implementations sharing operational constants but no code:

- **Android App** (primary): Native Kotlin app with foreground service, `WebView`-based login, `DataStore` preferences. Manual on-device testing.
- **Python Daemon** (legacy): Single-file `hitsz_net.py` — Selenium + ChromeDriver headless browser login, macOS LaunchAgent service. Synchronous `while True` loop.

Both probe `http://www.baidu.com` for connectivity, detect captive-portal redirects, and authenticate against `http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2` on a 60-second loop.

## Architecture & Data Flow

### Shared Constants (must stay aligned across platforms)

| Constant | Value |
|----------|-------|
| Login URL | `http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2` |
| Check URL | `http://www.baidu.com` |
| Poll interval | 60 seconds |

### Android Data Flow

```
BootReceiver ──(if auto-start)──> NetworkMonitorService
                                        │
MainActivity ──(start/stop)─────────────┤
                                        │
                             ┌── while(true) every 60s ──┐
                             │                           │
                        NetworkChecker.isOnline()         │
                             │                           │
                      ┌──────┴──────┐                    │
                      │  offline?   │                    │
                      └──────┬──────┘                    │
                             │ yes                       │
                        LoginManager.login()              │
                        (WebView + JS injection)          │
                             │                           │
                        Notification ─────────────────────┘
```

- `NetworkChangeReceiver` is **passive** — logs connectivity changes but does not drive the loop; the service owns the check/login cycle.
- `NetworkChecker` uses two-tier validation: `ConnectivityManager` + `NET_CAPABILITY_VALIDATED` for local state, then OkHttp GET to Baidu with body inspection for `'百度'` to rule out captive portals.
- `LoginManager` creates a headless `WebView` on `Dispatchers.Main`, injects JavaScript to fill credentials and click the login button, then verifies via `HttpURLConnection` to Baidu. Falls back through multiple DOM selectors (PC vs mobile Vue.js portal versions). Timeouts: 30s page load, 2s page-load delay, 3s submit delay.
- `PreferencesManager` uses Jetpack `DataStore` (not `SharedPreferences`). Keys: `username`, `password`, `auto_start`. Credentials stored unencrypted.

### Python Data Flow

```
main() ──> argparse ──> load_config() ──> while True:
                                               │
                                          check_internet()
                                          (requests.get to Baidu)
                                               │
                                        ┌──────┴──────┐
                                        │  offline?    │
                                        └──────┬──────┘
                                               │ yes
                                    is_trusted_hitsz_wifi()
                                    (macOS: SSID + BSSID allowlist)
                                               │
                                          login()
                                          (Selenium ChromeDriver headless)
                                               │
                                          notify()
                                          (macOS osascript notifications)
                                               │
                                          time.sleep(60)
```

- **Config lookup order** (fixed): CLI `--config` path > `~/.config/hitsz-autonet/.env` > `/etc/hitsz-autonet/.env` > `./.env`
- **Wi-Fi identity gating** (macOS only): Before launching Selenium, verifies SSID matches `HITSZ_WIFI_SSID` (default `'HITSZ'`) and BSSID is in the comma-separated `HITSZ_WIFI_BSSIDS` allowlist. Prevents credential exposure on spoofed networks. Bypassed to `True` on non-macOS platforms.
- **Selenium lifecycle**: `get_chromedriver_service()` tries `webdriver-manager` install, falls back to `~/.wdm` cached driver search (most recent by mtime), then PATH default. Chrome runs headless with `--no-sandbox --headless=undefined --disable-gpu --disable-dev-shm-usage` and a fixed Chrome 120 user-agent.
- **Login verification**: JS checks `window.CONFIG.page == 'success'`, then 3x `check_internet()` retries with 2s gaps.
- **Error handling**: Broad `except Exception` in most functions (logs, rarely propagates). `login()` has `try/finally` guaranteeing `driver.quit()`. ChromeDriver version mismatch gets a special critical log + notification.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `android-app/` | Android app: Gradle project, Kotlin source, shell scripts, debug docs |
| `android-app/app/src/main/java/com/hitsz/autonet/ui/` | `MainActivity` — single screen |
| `android-app/app/src/main/java/com/hitsz/autonet/service/` | Foreground service + boot/network receivers |
| `android-app/app/src/main/java/com/hitsz/autonet/utils/` | `LoginManager`, `NetworkChecker`, `PreferencesManager` |
| `hitsz_net/` | Legacy Python daemon: monolithic `hitsz_net.py`, `pyproject.toml`, `uv.lock` |
| `service/` | macOS LaunchAgent installer (`install.py`) — wraps `hitsz_net.py` |
| `research-findings/` | Archival research (~47 .md files, Jan 2026). Reference only; not source of truth |
| `config/` | Empty — reserved for future config artifacts |
| `scripts/` | Empty — reserved for future automation scripts |

## Development Commands

### Android

```bash
cd android-app

# Build
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
./gradlew assembleDebug         # Debug APK
./gradlew assembleRelease       # Release APK (with signing config)
./gradlew lint                  # Static analysis

# Convenience scripts
./build.sh                      # Clean assembleDebug with env vars pre-set
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Debugging (require adb + connected device with USB debugging)
./view-logs.sh                  # Filtered logcat with device check
./clear-and-watch.sh            # Clear logs, start fresh stream
./save-logs.sh                  # Capture 2 min of logs to timestamped file
./install-and-test.sh           # Full install + log watching workflow
./test-login.sh                 # Force-stop, clear logs, watch for login
./quick-test.sh                 # Shorter variant of test-login.sh
```

All log scripts filter on three tags: `LoginManager|NetworkMonitorService|NetworkChecker`.

### Python Daemon

```bash
# Install deps (pick one)
pip3 install -r requirements.txt
# or: cd hitsz_net && uv sync

# Run
python3 hitsz_net/hitsz_net.py --once          # Single check + login
python3 hitsz_net/hitsz_net.py --daemon        # Continuous loop
python3 hitsz_net/hitsz_net.py --update-driver # Refresh ChromeDriver

# macOS service management
python3 service/install.py install --config .env
python3 service/install.py uninstall
python3 service/install.py status
```

Service logs: `~/Library/Logs/hitsz-autonet/service.log` and `error.log`.

## Runtime/Toolchain Requirements

| Component | Version/Tool | Notes |
|-----------|-------------|-------|
| Python | >=3.13 | Managed via `uv` (`hitsz_net/uv.lock`) or legacy `pip` (`requirements.txt`) |
| Selenium | 4.39.0 | ChromeDriver via `webdriver-manager` (in `requirements.txt` but **not** in `pyproject.toml` — be aware of this drift) |
| Kotlin | 2.0.0 | Android |
| AGP | 8.5.0 | Android Gradle Plugin |
| Gradle | 8.7 | Wrapper included |
| compileSdk / targetSdk | 34 (Android 14) | |
| minSdk | 24 (Android 7.0) | |
| JDK | 17 (Homebrew path) | `JAVA_HOME=/opt/homebrew/opt/openjdk@17` |
| Android SDK | Command-line tools (Homebrew) | `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools` |

## Important Files

| File | Role |
|------|------|
| `hitsz_net/hitsz_net.py` | Python daemon: config, check, login, retry, notifications (~554 lines, monolithic) |
| `hitsz_net/pyproject.toml` | Python project metadata + deps |
| `hitsz_net/uv.lock` | Pinned transitive dependency versions |
| `hitsz_net/.env.example` | Config template: `HITSZ_USERNAME`, `HITSZ_PASSWORD`, `HITSZ_WIFI_SSID`, `HITSZ_WIFI_BSSIDS` |
| `requirements.txt` | Legacy pip deps (includes `webdriver-manager` that `pyproject.toml` omits) |
| `service/install.py` | macOS LaunchAgent plist generator + lifecycle (label: `com.github.hitsz.autonet`) |
| `android-app/app/build.gradle.kts` | Android dependencies, SDK versions, build config |
| `android-app/app/src/main/AndroidManifest.xml` | Permissions, components, `foregroundServiceType="dataSync"` |
| `android-app/app/src/main/res/xml/network_security_config.xml` | Cleartext allowed for `10.248.98.2` + `*.baidu.com` only |
| `android-app/app/src/main/java/com/hitsz/autonet/service/NetworkMonitorService.kt` | Foreground service monitor loop, notifications |
| `android-app/app/src/main/java/com/hitsz/autonet/utils/LoginManager.kt` | WebView login with JS injection, DOM fallbacks, connectivity verification |
| `android-app/app/src/main/java/com/hitsz/autonet/utils/NetworkChecker.kt` | Two-tier connectivity check (Android APIs + OkHttp to Baidu) |
| `android-app/app/src/main/java/com/hitsz/autonet/utils/PreferencesManager.kt` | DataStore-backed credentials + auto-start toggle |
| `android-app/app/src/main/java/com/hitsz/autonet/service/BootReceiver.kt` | Auto-start service after boot if preference enabled |
| `android-app/app/src/main/java/com/hitsz/autonet/service/NetworkChangeReceiver.kt` | Passive connectivity change logger (does **not** drive login) |
| `android-app/app/src/main/java/com/hitsz/autonet/ui/MainActivity.kt` | Single `AppCompatActivity` entry point |

## Code Conventions & Common Patterns

### Cross-Platform
- Treat Android and Python as **parallel implementations** of the same operational flow, not interchangeable modules.
- Canonical operational constants must stay aligned across platforms (login URL, check URL, 60s interval).
- Do not commit `.env` or any credentials.
- Do not assume HTTP 200 means internet access — captive-portal detection depends on redirect/content validation against Baidu.

### Python
- **Monolithic**: All daemon logic in `hitsz_net.py` (~554 lines). No package tree, no modules.
- **Synchronous**: Blocking `while True` loop with `time.sleep(60)`. No async, no threading, no concurrency.
- **Error handling**: Broad `except Exception` in most functions. Logs and continues. Only ChromeDriver version mismatch gets a critical-level log.
- **Config**: `python-dotenv` loading. Env var keys: `HITSZ_USERNAME`, `HITSZ_PASSWORD`, `HITSZ_WIFI_SSID` (default `'HITSZ'`), `HITSZ_WIFI_BSSIDS` (comma-separated).
- **Logging**: `force=True` `basicConfig` with `%Y-%m-%d %H:%M:%S` format. Selenium/urllib3 suppressed to `ERROR`. Daemon mode logs to file; once mode to stdout.
- **macOS-specific paths**: Airport Wi-Fi via `networksetup` + `/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport`. Notifications via `osascript -e 'display notification'`. LaunchAgent plist at `~/Library/LaunchAgents/com.github.hitsz.autonet.plist`.

### Android
- **Manual DI**: No Hilt, no Koin, no Dagger. Dependencies created in `onCreate` and passed explicitly.
- **No Navigation, No ViewModel**: Single `AppCompatActivity` with manual `findViewById`. `ViewBinding` compile flag enabled but unused.
- **Coroutine patterns**: `NetworkMonitorService` uses a custom `CoroutineScope(Dispatchers.Default + Job())`. `BootReceiver` fires-and-forgets with a fresh `CoroutineScope`. `MainActivity` uses `lifecycleScope`.
- **`suspendCancellableCoroutine`**: Used in `LoginManager` to bridge WebView callbacks (`onPageFinished`, `onReceivedError`) into coroutine suspension.
- **DataStore**: `preferencesDataStore` delegate extension on `Context`. Three keys: `username`, `password`, `auto_start`.
- **Foreground service**: `START_STICKY` return. Notification channel `hitsz_autonet_channel` (LOW importance). Notification icon: `android.R.drawable.ic_dialog_info` (no custom icon).
- **WebView login**: `Handler(Looper.getMainLooper()).postDelayed()` for delayed DOM readiness — NOT `view.postDelayed()` (project docs explicitly call this out).
- **Network security**: Cleartext scoped to `10.248.98.2` + `*.baidu.com` via `network_security_config.xml`. Do NOT broaden this.

### Shell Scripts
- All Android scripts live under `android-app/`. Depend on `adb` on PATH and a connected device.
- Hard-coded Homebrew paths for JDK 17 and Android SDK (macOS development environment).
- `install-and-test.sh` has a maintainer-specific absolute APK path — do not replicate this pattern.
- Log filter tag triple (`LoginManager|NetworkMonitorService|NetworkChecker`) is hard-coded across all log scripts.

## Anti-Patterns

- Do not commit `.env` or any credentials.
- Do not treat `research-findings/` as maintained application code or source of truth.
- Do not assume HTTP 200 means internet access.
- Do not break cross-platform constant parity when changing login URL, connectivity target, or retry interval.
- Do not remove or broaden `network_security_config.xml`; the cleartext exception is intentionally narrow.
- Do not switch WebView delayed handling to `view.postDelayed()`.
- Do not treat `NetworkChangeReceiver` as the primary orchestration path — it is passive.
- Do not add child AGENTS.md files under `hitsz_net/`, `service/`, `ui/`, or `utils/` unless those areas stop being single-purpose.
- Do not hardcode new absolute user paths in scripts.

## Testing & QA

- **Python daemon**: No formal test suite. Manual verification via `--once` flag and log inspection.
- **Android app**: Test dependencies declared in `build.gradle.kts` (JUnit, Espresso) but **no real test classes exist** in `src/test/` or `src/androidTest/`. All validation is manual on-device testing with `adb logcat` filtering.
- **Debug workflow**: See `android-app/DEBUG.md` for the operational debugging guide — covers DNS issues, cleartext blocks, form structure changes, WebView DevTools debugging.
- The project has no CI pipeline. Builds, linting, and testing are developer-driven.
