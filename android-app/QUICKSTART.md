# Android App Created - Quick Start Guide

## What Was Built

A complete Android application mirroring the Python daemon's functionality has been created in `android-app/` directory.

## Project Structure

```
android-app/
├── app/
│   ├── src/main/
│   │   ├── java/com/hitsz/autonet/
│   │   │   ├── ui/MainActivity.kt - Main configuration screen
│   │   │   ├── service/
│   │   │   │   ├── NetworkMonitorService.kt - Background monitoring service
│   │   │   │   ├── BootReceiver.kt - Auto-start on boot
│   │   │   │   └── NetworkChangeReceiver.kt - Network state listener
│   │   │   └── utils/
│   │   │       ├── NetworkChecker.kt - Connectivity checker
│   │   │       ├── LoginManager.kt - WebView-based authentication
│   │   │       └── PreferencesManager.kt - Settings storage
│   │   ├── res/ - UI layouts and resources
│   │   └── AndroidManifest.xml - App configuration
│   └── build.gradle.kts - Dependencies and build config
├── README.md - Complete documentation
├── BUILD.md - Build instructions for Mac
└── gradle/ - Gradle wrapper files
```

## Key Features Implemented

✅ Network connectivity detection (mirrors `check_internet()`)
✅ WebView-based login (mirrors `login()` using Selenium)
✅ Background service with 60-second check interval (mirrors daemon loop)
✅ Android notifications (mirrors macOS notifications)
✅ DataStore credential storage (replaces `.env` file)
✅ Auto-start on boot (replaces LaunchAgent)
✅ Material Design 3 UI
✅ Foreground service for reliability

## How to Build

### Quick Start

```bash
cd android-app

# Option 1: Use the build script (recommended)
./build.sh

# Option 2: Manual build
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
./gradlew assembleDebug

# Output: app/build/outputs/apk/debug/app-debug.apk
```

**First Time Setup (if needed):**
```bash
# Accept SDK licenses
$ANDROID_HOME/cmdline-tools/bin/sdkmanager --licenses

# Install required SDK components
$ANDROID_HOME/cmdline-tools/bin/sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

### Install on Device

**Option 1 - Via ADB:**
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

**Option 2 - Manual Transfer:**
1. Transfer `app-debug.apk` to your Android device
2. Enable "Install from Unknown Sources" in Settings
3. Open APK and install

## How to Use

1. **Launch App** - Open "HITSZ AutoNet" on your device
2. **Enter Credentials** - Input your HITSZ username and password
3. **Save** - Tap "Save Credentials"
4. **Start Service** - Tap "Start Monitoring"
5. **Auto-Start (Optional)** - Enable "Start on Boot" toggle

The app will:
- Monitor network every 60 seconds
- Auto-login when internet is unavailable
- Send notifications for status changes
- Show persistent notification while running

## Architecture Comparison

| Component | Python (macOS) | Android |
|-----------|---------------|---------|
| **Network Check** | `requests.get()` | `OkHttpClient` + `ConnectivityManager` |
| **Login** | Selenium + ChromeDriver | WebView + JavaScript injection |
| **Background** | Daemon process | Foreground Service |
| **Storage** | `.env` file | DataStore (encrypted) |
| **Notifications** | AppleScript | Android Notification API |
| **Auto-start** | LaunchAgent plist | Boot Receiver |

## Technology Stack

- **Language**: Kotlin
- **Min SDK**: Android 7.0 (API 24)
- **Target SDK**: Android 14 (API 34)
- **Architecture**: Service-based with coroutines
- **UI**: Material Design 3
- **Storage**: DataStore Preferences
- **Networking**: OkHttp3
- **Background**: WorkManager + Foreground Service

## Files Created

**Configuration:**
- `build.gradle.kts` (root and app)
- `settings.gradle.kts`
- `gradle.properties`
- `gradle/wrapper/gradle-wrapper.properties`

**Source Code (Kotlin):**
- `MainActivity.kt` - UI and user interaction
- `NetworkMonitorService.kt` - Background monitoring
- `NetworkChecker.kt` - Connectivity validation
- `LoginManager.kt` - Authentication logic
- `PreferencesManager.kt` - Settings storage
- `BootReceiver.kt` - Boot auto-start
- `NetworkChangeReceiver.kt` - Network events

**Resources:**
- `AndroidManifest.xml` - Permissions and components
- `activity_main.xml` - UI layout
- `strings.xml`, `colors.xml`, `themes.xml` - UI resources

**Documentation:**
- `README.md` - Complete app documentation
- `BUILD.md` - Build instructions for Mac

## Documentation

See the following files for detailed information:

- **android-app/README.md** - Complete feature documentation
- **android-app/BUILD.md** - Mac build setup and troubleshooting
- **This file** - Quick start reference

## Next Steps

1. **Build the APK** - Follow instructions in BUILD.md
2. **Install on device** - Use ADB or manual transfer
3. **Configure credentials** - Enter your HITSZ account info
4. **Test** - Start service and verify auto-login works

## Troubleshooting

**Build fails:**
- Ensure Java 8+ is installed: `java -version`
- Set ANDROID_HOME correctly
- Accept SDK licenses: `sdkmanager --licenses`

**Service won't start:**
- Check credentials are saved
- Grant notification permission
- Ensure app isn't battery-optimized

**Login fails:**
- Verify credentials are correct
- Check network connectivity
- See logs in Android Logcat

For detailed troubleshooting, see BUILD.md and README.md.

---

**Status**: ✅ Android app fully implemented and ready to build!
