# Repository Guidelines

**Generated:** 2026-07-14

## Project Overview

Automated HITSZ (Harbin Institute of Technology, Shenzhen) campus-network authentication — two independent implementations sharing operational constants but no code:

- **Android App** (primary): Native Kotlin app with foreground service, `WebView`-based login, `DataStore` preferences. Manual on-device testing.
- **Python Daemon**: Single-file `hitsz_net.py` — pure-HTTP Srun login, safe Wi-Fi-to-wired session handoff, and macOS LaunchAgent service. Synchronous `while True` loop plus optional lid watcher.

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
                                  handle_wired_handoff()
                                  (route + interface-bound Srun probe)
                                               │
                                          check_internet()
                                          (requests.get to Baidu)
                                               │
                                        ┌──────┴──────┐
                                        │  offline?    │
                                        └──────┬──────┘
                                               │ yes
                                            login()
                                  (challenge + encrypted HTTP API)
                                               │
                                          notify()
                                               │
                                          time.sleep(60)
```

- **Config lookup order** (fixed): CLI `--config` path > `~/.config/hitsz-autonet/.env` > `/etc/hitsz-autonet/.env` > `./.env`
- **Pure HTTP login**: Queries `rad_user_info`, obtains a challenge, computes HMAC-MD5 + Srun XXTEA/base64 + SHA1, then submits `srun_portal`; portal requests force-resolve `net.hitsz.edu.cn` to `10.248.98.2` for pre-login DNS failures.
- **Interface binding** (macOS): `InterfaceAdapter` supplies both `source_address` and Darwin `IP_BOUND_IF` so probes and login requests cannot drift to another interface.
- **Safe wired handoff**: Only runs when the default hardware port is wired. It verifies the Wi-Fi-bound Srun IP/account/MAC, rechecks the route, sends the current portal's IP-targeted `rad_user_dm` request, and requires a post-operation offline check. A precheck `not_online_error` never triggers logout.
- **Error handling**: Portal and subprocess failures are logged and retried by the main loop. Credential absence exits immediately; route races and identity mismatches fail closed.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `android-app/` | Android app: Gradle project, Kotlin source, shell scripts, debug docs |
| `android-app/app/src/main/java/com/hitsz/autonet/ui/` | `MainActivity` — single screen |
| `android-app/app/src/main/java/com/hitsz/autonet/service/` | Foreground service + boot/network receivers |
| `android-app/app/src/main/java/com/hitsz/autonet/utils/` | `LoginManager`, `NetworkChecker`, `PreferencesManager` |
| `hitsz_net/` | Python daemon: monolithic runtime, Srun crypto helper, project metadata |
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
# Install dependencies
uv sync

# Run
uv run hitsz_net/hitsz_net.py --once
uv run hitsz_net/hitsz_net.py --daemon

# macOS service management
uv run service/install.py install --config .env
uv run service/install.py uninstall
uv run service/install.py status

# Handoff contract tests
uv run ./test_handoff.py
```

Service logs: `~/Library/Logs/hitsz-autonet/service.log` and `error.log`.

## Runtime/Toolchain Requirements

| Component | Version/Tool | Notes |
|-----------|-------------|-------|
| Python | >=3.13 | Managed via root `uv.lock`; dependencies are `requests` and `python-dotenv` |
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
| `hitsz_net/hitsz_net.py` | Python daemon: config, interface binding/handoff, connectivity check, Srun login, retry, notifications |
| `hitsz_net/pyproject.toml` | Python project metadata + deps |
| `hitsz_net/uv.lock` | Pinned transitive dependency versions |
| `hitsz_net/.env.example` | Config template: `HITSZ_USERNAME`, `HITSZ_PASSWORD` |
| `test_handoff.py` | Stdlib `unittest` coverage for exact session identity, targeted parameters, and post-logout verification |
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
- **Monolithic**: Runtime orchestration remains in `hitsz_net.py`; cryptography lives in `srun_crypto.py`.
- **Synchronous**: Blocking `while True` loop with `time.sleep(60)`; the optional lid watcher is the only background thread.
- **Fail-closed handoff**: Never logout from an account-wide device list or from `not_online_error`. Require exact source-bound IP identity, optional response account/MAC agreement, stable wired route, accepted DM response, and post-logout offline state.
- **Config**: `python-dotenv` keys are only `HITSZ_USERNAME` and `HITSZ_PASSWORD`.
- **Logging**: `force=True` `basicConfig` with `%Y-%m-%d %H:%M:%S`; expected portal TLS warnings and urllib3 logs are suppressed.
- **macOS integration**: `route`, `networksetup`, `ipconfig`, Darwin `IP_BOUND_IF`, `osascript`, and LaunchAgent label `com.github.hitsz.autonet`.

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

- **Python daemon**: Run `uv run ./test_handoff.py` for handoff contracts, then `uv run hitsz_net/hitsz_net.py --once --config .env` for a real non-daemon cycle and inspect the LaunchAgent log after restart.
- **Android app**: Test dependencies declared in `build.gradle.kts` (JUnit, Espresso) but **no real test classes exist** in `src/test/` or `src/androidTest/`. All validation is manual on-device testing with `adb logcat` filtering.
- **Debug workflow**: See `android-app/DEBUG.md` for the operational debugging guide — covers DNS issues, cleartext blocks, form structure changes, WebView DevTools debugging.
- The project has no CI pipeline. Builds, linting, and testing are developer-driven.
