# AGENTS.md - HITSZ AutoNet Project

## Project Overview
Automated HITSZ campus network authentication with two implementations:
- **Android App** (Primary): Native Kotlin app with background service for network monitoring and auto-login
- **Python Daemon** (Legacy): Selenium-based macOS LaunchAgent for automated authentication

## Build/Lint/Test Commands

### Android App

#### Build Commands
```bash
cd android-app
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools

./gradlew assembleDebug
./gradlew assembleRelease
./gradlew clean

adb install -r app/build/outputs/apk/debug/app-debug.apk
```

#### Testing Commands
```bash
./gradlew test
./gradlew connectedAndroidTest
./gradlew lint
```

#### Logging & Debugging
```bash
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
adb logcat -c
adb logcat -s NetworkMonitorService:I
```

### Python Daemon

#### Running the Script
```bash
python3 hitsz_net/hitsz_net.py --once
python3 hitsz_net/hitsz_net.py --daemon
python3 hitsz_net/hitsz_net.py --config path/to/.env
python3 hitsz_net/hitsz_net.py --update-driver
```

#### Service Management (macOS)
```bash
python3 service/install.py install --config .env
python3 service/install.py status
python3 service/install.py uninstall

tail -f ~/Library/Logs/hitsz-autonet/service.log
tail -f ~/Library/Logs/hitsz-autonet/error.log
```

#### Testing
```bash
python3 -c "from hitsz_net.hitsz_net import check_internet; print(check_internet())"
python3 -c "from hitsz_net.hitsz_net import load_config; load_config('.env')"
```

## Code Style Guidelines

### Android (Kotlin)

#### File Organization
```kotlin
package com.hitsz.autonet.utils

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class NetworkChecker(private val context: Context) {
    companion object {
        private const val TAG = "NetworkChecker"
    }
}
```

#### Naming Conventions
- **Classes**: `PascalCase` (e.g., `NetworkMonitorService`, `LoginManager`)
- **Functions**: `camelCase` (e.g., `checkInternet`, `startService`)
- **Properties**: `camelCase` (e.g., `isRunning`, `checkInterval`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `CHECK_INTERVAL`, `LOGIN_URL`)
- **Private members**: No underscore prefix (Kotlin convention)

#### Formatting
- **Indentation**: 4 spaces (no tabs)
- **Line length**: 120 characters max
- **Braces**: K&R style (opening brace on same line)

#### Coroutines & Async
```kotlin
suspend fun checkInternet(): Boolean = withContext(Dispatchers.IO) {
    try {
        // Network operation
    } catch (e: Exception) {
        Log.e(TAG, "Error: ${e.message}")
        false
    }
}
```

#### Logging
```kotlin
Log.d(TAG, "Debug message")
Log.i(TAG, "Info message")
Log.w(TAG, "Warning message")
Log.e(TAG, "Error: ${exception.message}")
```

### Python Daemon

#### Import Order
```python
import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
```

#### Formatting
- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **String quotes**: Double quotes `"` for strings
- **Trailing commas**: Omitted in single-line structures
- **Blank lines**: 2 between top-level functions/classes

#### Naming Conventions
- **Functions/variables**: `snake_case` (e.g., `check_internet`, `log_file`)
- **Classes**: `PascalCase` (e.g., `ServiceInstaller`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `LOGIN_URL`, `CHECK_URL`, `LABEL`)
- **Private/internal**: Leading underscore `_helper_function`

#### Error Handling
```python
try:
    driver.get(LOGIN_URL)
except WebDriverException as e:
    logger.error(f"WebDriver error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
finally:
    driver.quit()
```

#### Logging
- Use standard `logging` module, not `print()`
- Log levels: `DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`
- Format: `"%(asctime)s - %(levelname)s - %(message)s"`
```python
logger.info("Normal operation message")
logger.warning("Something unusual but not fatal")
logger.error("Operation failed")
```

#### Configuration
- Credentials in `.env` files (never commit)
- Default config paths checked in order:
  1. `~/.config/hitsz-autonet/.env`
  2. `/etc/hitsz-autonet/.env`
  3. `./.env`
- Use `pathlib.Path` for all file paths
- Environment variables: `HITSZ_USERNAME`, `HITSZ_PASSWORD`

#### Selenium Best Practices
- Always use headless mode in production: `--headless`
- Set explicit timeouts: `driver.set_page_load_timeout(30)`
- Use `WebDriverWait` for element presence checks
- Always `driver.quit()` in `finally` block
- Prefer `execute_script("arguments[0].click()")` over `.click()` for reliability
- Suppress Selenium logs: `logging.getLogger("selenium").setLevel(logging.ERROR)`

## Project Structure

### Android App
```
android-app/
├── app/
│   ├── src/main/
│   │   ├── java/com/hitsz/autonet/
│   │   │   ├── ui/
│   │   │   │   └── MainActivity.kt
│   │   │   ├── service/
│   │   │   │   ├── NetworkMonitorService.kt
│   │   │   │   ├── BootReceiver.kt
│   │   │   │   └── NetworkChangeReceiver.kt
│   │   │   └── utils/
│   │   │       ├── NetworkChecker.kt
│   │   │       ├── LoginManager.kt
│   │   │       └── PreferencesManager.kt
│   │   ├── res/
│   │   │   ├── layout/activity_main.xml
│   │   │   ├── values/strings.xml
│   │   │   └── xml/network_security_config.xml
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
└── README.md
```

### Python Daemon
```
hitsz_net/
├── hitsz_net.py          # Main authentication script
└── README.md

service/
└── install.py            # macOS LaunchAgent installer
```

## Key Implementation Details

### Android Authentication Flow

1. **Network Detection** (`NetworkChecker.kt`):
   - Uses `ConnectivityManager` to check network state
   - HTTP request to `baidu.com` to verify real internet access
   - Detects captive portal via redirect/content mismatch

2. **WebView-based Login** (`LoginManager.kt`):
   - Loads `http://10.248.98.2` (redirects to mobile portal)
   - Waits 2 seconds for Vue.js dynamic content
   - JavaScript injection to fill form and submit
   - Verification via network connectivity check (not page status)

3. **Background Service** (`NetworkMonitorService.kt`):
   - Runs as foreground service with notification
   - 60-second check interval
   - Auto-triggers login on connectivity loss

### Python Authentication Flow

1. **Network Detection** (`check_internet()`):
   - HTTP request to `baidu.com`
   - Checks response code and content
   - Detects captive portal redirects

2. **Selenium Login** (`login()`):
   - Headless Chrome with explicit waits
   - JavaScript-based form interaction
   - Success verification via `window.CONFIG.page`

3. **Daemon Loop**:
   - 60-second interval checks
   - AppleScript notifications on macOS
   - LaunchAgent for auto-start

## Platform-Specific Notes

### Android
- **Min SDK**: API 24 (Android 7.0)
- **Target SDK**: API 34 (Android 14)
- **Background limits**: Use foreground service to avoid Doze restrictions
- **Battery optimization**: App should be exempted for reliable monitoring

### macOS (Python - Primary)
- Uses AppleScript for notifications: `osascript -e 'display notification...'`
- LaunchAgent plist in `~/Library/LaunchAgents/`
- Service runs on `NetworkState` change (KeepAlive)

### Linux (Python - Secondary Support)
- Notifications: Use `notify-send` or similar
- Service management: systemd unit files
- Config paths: `~/.config/hitsz-autonet/` or `/etc/hitsz-autonet/`

## Key Files

### Android
- `android-app/app/src/main/java/com/hitsz/autonet/utils/LoginManager.kt` - WebView login logic
- `android-app/app/src/main/java/com/hitsz/autonet/utils/NetworkChecker.kt` - Connectivity detection
- `android-app/app/src/main/java/com/hitsz/autonet/service/NetworkMonitorService.kt` - Background service
- `android-app/app/src/main/AndroidManifest.xml` - App configuration
- `android-app/app/src/main/res/xml/network_security_config.xml` - HTTP cleartext permissions

### Python
- `hitsz_net/hitsz_net.py` - Main authentication script
- `service/install.py` - macOS LaunchAgent installer
- `requirements.txt` - Python dependencies
- `.env` - Credentials (git-ignored)

### Documentation
- `README.md` - Project overview
- `AGENTS.md` - This file (development guide)
- `android-app/README.md` - Comprehensive Android documentation
- `android-app/BUILD.md` - Build instructions
- `android-app/QUICKSTART.md` - Quick start guide
- `hitsz_net/README.md` - Python daemon documentation

## Development Workflow

### Android
1. **Setup**: Create credentials in app UI
2. **Test**: Run in Android Studio with connected device
3. **Debug**: Use `adb logcat` with filtered tags
4. **Build**: Generate APK with gradle
5. **Install**: Deploy via `adb install`

### Python
1. **Setup**: Create `.env` with credentials
2. **Test**: Run with `--once` flag first
3. **Iterate**: Modify code, test with direct invocation
4. **Service**: Install as LaunchAgent only after validation
5. **Debug**: Check logs in `~/Library/Logs/hitsz-autonet/`

## Common Pitfalls

### Android
1. **WebView postDelayed issues**: Use `Handler(Looper.getMainLooper()).postDelayed()` instead of `view.postDelayed()`
2. **Cleartext HTTP blocked**: Ensure `network_security_config.xml` properly configured
3. **Background restrictions**: Android 12+ limits background work, use foreground service
4. **Permission issues**: Request runtime permissions for notifications
5. **Form detection**: Don't rely on page config - verify by testing actual network connectivity

### Python
1. **ChromeDriver mismatch**: Run `--update-driver` when Chrome updates
2. **Offline driver updates**: Can't auto-update without internet - use mobile hotspot
3. **Missing config**: Service fails silently if `.env` not found
4. **Captive portal false positives**: `check_internet()` validates Baidu content, not just HTTP 200
5. **Permission issues**: Ensure script is executable, paths are absolute in plist

## Extending the Project

### Android
- **New network detection**: Extend `NetworkChecker.checkInternet()`
- **Additional notifications**: Modify `NetworkMonitorService.sendNotification()`
- **UI improvements**: Update `activity_main.xml` and `MainActivity`
- **Custom intervals**: Add configuration option in `PreferencesManager`

### Python
- Add new network detection methods in `check_internet()`
- Support additional notification backends in `notify()`
- Implement retry strategies in `login()`
- Add structured logging (JSON format for parsing)
- Create pytest test suite for core functions

## Acknowledgments

Python daemon inspired by original [hitsz_net](https://github.com/siliconx/hitsz_net) project by siliconx.
