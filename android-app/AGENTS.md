# ANDROID APP KNOWLEDGE BASE

**Generated:** 2026-04-07 12:13:17 CST
**Commit:** 8783546
**Branch:** master

## OVERVIEW
Native Android implementation of HITSZ AutoNet. Core flow: `MainActivity` stores credentials, `NetworkMonitorService` runs the 60-second monitor, `LoginManager` performs WebView login, and `BootReceiver` optionally restarts the service after reboot.

## STRUCTURE
```text
android-app/
├── app/src/main/java/com/hitsz/autonet/
│   ├── ui/        # MainActivity only
│   ├── service/   # Foreground service + receivers
│   └── utils/     # NetworkChecker, LoginManager, PreferencesManager
├── app/src/main/res/xml/
│   └── network_security_config.xml
├── build.sh
├── install-and-test.sh
├── view-logs.sh
└── DEBUG.md
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| App entry/config UI | `app/src/main/java/com/hitsz/autonet/ui/MainActivity.kt` | Saves credentials, toggles auto-start, starts/stops service |
| Monitoring loop | `app/src/main/java/com/hitsz/autonet/service/NetworkMonitorService.kt` | Foreground service; 60s retry/check cycle |
| Boot behavior | `app/src/main/java/com/hitsz/autonet/service/BootReceiver.kt` | Reads DataStore and starts service after boot |
| Login behavior | `app/src/main/java/com/hitsz/autonet/utils/LoginManager.kt` | WebView, JS injection, delayed DOM readiness, connectivity verification |
| Connectivity heuristic | `app/src/main/java/com/hitsz/autonet/utils/NetworkChecker.kt` | OkHttp request to Baidu; redirect/content validation |
| Persistent settings | `app/src/main/java/com/hitsz/autonet/utils/PreferencesManager.kt` | DataStore-backed username/password/auto-start |
| Component wiring | `app/src/main/AndroidManifest.xml` | Permissions, receivers, `foregroundServiceType="dataSync"` |
| Cleartext exception | `app/src/main/res/xml/network_security_config.xml` | Only campus login host + Baidu are whitelisted |
| Debug workflow | `DEBUG.md`, `view-logs.sh`, `clear-and-watch.sh`, `save-logs.sh` | Manual validation is log-driven |

## CONVENTIONS
- Package layout is simple and stable: `ui`, `service`, `utils`; do not create finer-grained AGENTS files under them.
- Foreground monitoring is the only supported background pattern here; `NetworkMonitorService` returns `START_STICKY` and uses notification channel `hitsz_autonet_channel`.
- Login happens in a WebView on the main dispatcher; network verification happens after form submission rather than trusting page state alone.
- Data persistence uses DataStore, not SharedPreferences or `.env`-style files.
- Build environment in project docs/scripts assumes macOS/Homebrew paths:
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17`
  - `ANDROID_HOME=/opt/homebrew/share/android-commandlinetools`

## ANTI-PATTERNS
- Do not remove or broaden `network_security_config.xml`; the cleartext exception is intentionally narrow.
- Do not switch delayed WebView handling back to `view.postDelayed()`; project docs explicitly call out `Handler(Looper.getMainLooper()).postDelayed()` as the reliable pattern.
- Do not treat `NetworkChangeReceiver` as the primary orchestration path; it is passive and the service owns the actual check/login loop.
- Do not assume automated tests protect behavior; this module currently depends on device testing and filtered `adb logcat` output.
- Do not hardcode new absolute user paths in scripts; one existing script already has a maintainer-specific APK path and should not become a wider pattern.

## COMMANDS
```bash
cd android-app
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools

./gradlew assembleDebug
./gradlew assembleRelease
./gradlew lint
./build.sh

adb install -r app/build/outputs/apk/debug/app-debug.apk
./view-logs.sh
./clear-and-watch.sh
./save-logs.sh
./quick-test.sh
./test-login.sh
```

## NOTES
- `app/build.gradle.kts` declares JUnit/Espresso dependencies, but there are currently no real `src/test/` or `src/androidTest/` suites.
- `LoginManager.kt` is the Android complexity hotspot; if login breaks, start there before touching UI or receivers.
- `DEBUG.md` is the best operational companion when reproducing failures on a real device.
