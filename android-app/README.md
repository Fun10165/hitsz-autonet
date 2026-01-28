# HITSZ AutoNet - Android App

An Android application for automatic HITSZ campus network authentication. This app mirrors the functionality of the Python daemon but runs natively on Android devices.

## Features

- 🔄 **Automatic Network Detection**: Continuously monitors network connectivity
- 🔐 **Auto-Login**: Automatically authenticates when network is lost
- 🚀 **Start on Boot**: Option to start monitoring service on device boot
- 📱 **Foreground Service**: Reliable background operation with persistent notification
- 🔔 **Event Notifications**: Get notified of login attempts and status changes
- 💾 **Secure Credential Storage**: Uses DataStore for encrypted credential storage

## Architecture

The app follows modern Android architecture guidelines:

- **UI Layer**: `MainActivity` - Material Design 3 UI for configuration
- **Service Layer**: 
  - `NetworkMonitorService` - Foreground service for continuous monitoring
  - `BootReceiver` - Auto-start on device boot
  - `NetworkChangeReceiver` - React to network state changes
- **Utils Layer**:
  - `NetworkChecker` - Network connectivity validation
  - `LoginManager` - WebView-based authentication
  - `PreferencesManager` - DataStore-based settings storage

## Requirements

- **Minimum SDK**: Android 7.0 (API 24)
- **Target SDK**: Android 14 (API 34)
- **Permissions**:
  - `INTERNET` - Network access
  - `ACCESS_NETWORK_STATE` - Monitor connectivity
  - `POST_NOTIFICATIONS` - Send notifications (Android 13+)
  - `FOREGROUND_SERVICE` - Run background service
  - `RECEIVE_BOOT_COMPLETED` - Start on boot

## Building the App

### Prerequisites

1. **Java/JDK**: JDK 8 or higher
2. **Android SDK**: Install via Android Studio or command line tools
3. **Gradle**: 8.0 or higher

### Build Commands

```bash
cd android-app

# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease

# Install debug APK to connected device
./gradlew installDebug

# Run all checks and tests
./gradlew check

# Clean build
./gradlew clean
```

### Build Output

Debug APK: `app/build/outputs/apk/debug/app-debug.apk`
Release APK: `app/build/outputs/apk/release/app-release.apk`

## Installation

### Option 1: Direct APK Install

1. Build the APK using gradle commands above
2. Transfer APK to your Android device
3. Enable "Install from Unknown Sources" in Settings
4. Open the APK file and install

### Option 2: Android Studio

1. Open `android-app` folder in Android Studio
2. Connect your Android device via USB with USB debugging enabled
3. Click Run (green play button) or press Shift+F10
4. Select your device from the deployment target dialog

## Usage

### Initial Setup

1. Launch the app
2. Enter your HITSZ network credentials
   - Username: Your student/staff ID
   - Password: Your network password
3. Tap "Save Credentials"

### Starting the Service

1. Tap "Start Monitoring" button
2. Grant notification permission if prompted
3. The service will start monitoring in the background
4. A persistent notification will appear showing service status

### Auto-Start on Boot

1. Enable the "Start on Boot" toggle
2. The service will automatically start when your device boots
3. No manual intervention needed after reboot

### Monitoring Behavior

- **Check Interval**: Every 60 seconds
- **Connectivity Test**: Verifies actual internet access (not just network connection)
- **Auto-Login**: Triggers when captive portal or no internet detected
- **Notifications**: Receive alerts for login attempts and status changes

## Configuration Files

### Gradle Configuration

- `build.gradle.kts` (project) - Top-level build configuration
- `app/build.gradle.kts` - App module dependencies and build settings
- `gradle.properties` - Gradle JVM settings
- `settings.gradle.kts` - Project structure definition

### Android Manifest

`app/src/main/AndroidManifest.xml` - Declares:
- App permissions
- Activities, Services, and Broadcast Receivers
- App metadata and configurations

## Key Components Explained

### NetworkChecker.kt

Mirrors Python's `check_internet()` function:
- Tests network availability using ConnectivityManager
- Validates real internet access by requesting Baidu
- Detects captive portals (returns different URL/content)

### LoginManager.kt

Mirrors Python's `login()` function using Selenium:
- Uses WebView with JavaScript enabled
- Fills login form with credentials
- Clicks submit button via JavaScript
- Verifies success via `window.CONFIG.page` check

### NetworkMonitorService.kt

Mirrors Python's main monitoring loop:
- Runs as foreground service for reliability
- Checks connectivity every 60 seconds
- Triggers login when needed
- Sends notifications for status updates

### PreferencesManager.kt

Replaces Python's `.env` file approach:
- Uses DataStore for secure storage
- Stores credentials and settings
- Provides Flow-based reactive access

## Troubleshooting

### Service Won't Start

- Ensure credentials are saved
- Check notification permission is granted
- Verify app has necessary permissions in Settings

### Login Fails

- Verify credentials are correct
- Check if login page URL is accessible
- Ensure device has network connectivity (even if no internet)

### Auto-Start Not Working

- Check "Start on Boot" toggle is enabled
- Verify `RECEIVE_BOOT_COMPLETED` permission is granted
- Some manufacturers require additional battery optimization exemptions

### High Battery Usage

- This is expected for background services
- The service checks every 60 seconds
- Consider adding to battery optimization exemptions for reliability

## Development

### Project Structure

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
│   │   │   ├── layout/
│   │   │   │   └── activity_main.xml
│   │   │   ├── values/
│   │   │   │   ├── strings.xml
│   │   │   │   ├── colors.xml
│   │   │   │   └── themes.xml
│   │   │   └── xml/
│   │   │       ├── backup_rules.xml
│   │   │       └── data_extraction_rules.xml
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

### Code Style

- **Language**: Kotlin
- **Architecture**: MVVM-lite with coroutines
- **Naming**: Follow Kotlin conventions (camelCase)
- **Formatting**: Android Studio default formatter
- **Comments**: KDoc for public APIs

### Adding Features

1. Network detection methods → Extend `NetworkChecker`
2. Authentication strategies → Extend `LoginManager`
3. Notification types → Update `NetworkMonitorService`
4. UI improvements → Modify `activity_main.xml` and `MainActivity`

## Comparison with Python Version

| Feature | Python (macOS) | Android |
|---------|---------------|---------|
| Platform | macOS LaunchAgent | Android Service |
| Web Automation | Selenium + ChromeDriver | WebView + JavaScript |
| Notifications | AppleScript | Android Notifications |
| Configuration | .env file | DataStore |
| Background | Daemon process | Foreground Service |
| Auto-start | LaunchAgent plist | Boot Receiver |
| Check Interval | 60 seconds | 60 seconds |

## Known Limitations

1. **WebView vs Selenium**: WebView may behave differently than Chrome
2. **Background Restrictions**: Android 12+ has strict background limits
3. **Battery Impact**: Continuous monitoring affects battery life
4. **Network Types**: Only tested on campus WiFi networks
5. **Captive Portals**: Some complex portals may not be detected

## Future Enhancements

- [ ] Manual login trigger button
- [ ] Connection history log
- [ ] Customizable check interval
- [ ] Multiple credential profiles
- [ ] Widget for quick status view
- [ ] Dark mode theme
- [ ] Network usage statistics

## License

Same license as the parent Python project.

## Contributing

Follow the same contribution guidelines as the main project. Ensure all Android-specific code follows Kotlin conventions and Android best practices.
