# HITSZ AutoNet

Automated HITSZ campus network authentication for Android and macOS.

## Project Overview

This repository provides automated network authentication solutions for HITSZ (Harbin Institute of Technology, Shenzhen) campus network:

- **Android App** (Primary): Native Android application with background monitoring service
- **Python Daemon** (Legacy): macOS LaunchAgent-based daemon for automated login

## Quick Start

### Android App

The Android app provides automatic network monitoring and authentication with a native mobile experience.

**Features:**
- 🔄 Continuous network monitoring with 60-second intervals
- 🔐 Automatic login when captive portal detected
- 🚀 Start on boot support
- 📱 Foreground service with persistent notification
- 💾 Secure credential storage via DataStore

**Installation:**

1. Build the APK:
```bash
cd android-app
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
./gradlew assembleDebug
```

2. Install to device:
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**See [android-app/README.md](android-app/README.md) for detailed documentation.**

### Python Daemon (macOS)

Legacy Python-based daemon using Selenium for automated authentication.

**Features:**
- Automated login via Selenium WebDriver
- macOS LaunchAgent integration
- Captive portal detection
- Configurable via `.env` file

**Installation:**

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Create `.env` configuration:
```bash
HITSZ_USERNAME=your_username
HITSZ_PASSWORD=your_password
```

3. Install as LaunchAgent service:
```bash
python3 service/install.py install --config .env
```

**See [hitsz_net/README.md](hitsz_net/README.md) for legacy script details.**

## Project Structure

```
hitsz-autonet/
├── android-app/              # Android application (primary)
│   ├── app/src/main/
│   │   ├── java/com/hitsz/autonet/
│   │   │   ├── ui/           # MainActivity
│   │   │   ├── service/      # NetworkMonitorService, BootReceiver
│   │   │   └── utils/        # NetworkChecker, LoginManager
│   │   ├── res/              # Layouts, themes, strings
│   │   └── AndroidManifest.xml
│   └── README.md
├── hitsz_net/                # Python daemon (legacy)
│   ├── hitsz_net.py          # Main authentication script
│   └── README.md
├── service/                  # macOS service installer
│   └── install.py
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Documentation

- [AGENTS.md](AGENTS.md) - AI agent instructions for development
- [android-app/README.md](android-app/README.md) - Android app comprehensive guide
- [android-app/BUILD.md](android-app/BUILD.md) - Build instructions
- [android-app/QUICKSTART.md](android-app/QUICKSTART.md) - Quick start guide
- [hitsz_net/README.md](hitsz_net/README.md) - Python daemon documentation

## How It Works

### Network Detection

Both implementations monitor network connectivity by:
1. Testing connection to external sites (e.g., baidu.com)
2. Detecting HTTP redirects to campus portal
3. Validating response content to distinguish captive portals

### Authentication Process

When captive portal detected:
1. Load login page (`http://10.248.98.2` → redirects to `https://net.hitsz.edu.cn/srun_portal_phone`)
2. Wait for Vue.js dynamic content to render
3. Fill username/password fields via JavaScript
4. Submit login form
5. Verify authentication by checking network connectivity

### Platform Differences

| Feature | Android | Python (macOS) |
|---------|---------|----------------|
| Web Automation | WebView + JavaScript | Selenium + ChromeDriver |
| Background Service | Foreground Service | LaunchAgent Daemon |
| Credential Storage | DataStore (encrypted) | .env file |
| Notifications | Android Notifications | AppleScript |
| Auto-start | Boot Receiver | LaunchAgent plist |
| Check Interval | 60 seconds | 60 seconds |

## Requirements

### Android App
- Android 7.0+ (API 24)
- Java 8+ for building
- Android SDK with Gradle 8.0+

### Python Daemon
- Python 3.8+
- Chrome/Chromium browser
- ChromeDriver (auto-managed via webdriver-manager)
- macOS 10.15+ (for LaunchAgent features)

## Acknowledgments

The Python daemon (`hitsz_net`) is inspired by and adapted from the original [hitsz_net](https://github.com/siliconx/hitsz_net) project by siliconx. Thank you for the foundational work on HITSZ campus network authentication automation.

## License

This project follows the same license terms as the original hitsz_net project.

## Contributing

Contributions welcome! Please ensure:
- Android code follows Kotlin conventions
- Python code follows PEP 8
- Update relevant documentation
- Test on target platforms before submitting

## Support

For issues or questions:
- Check existing documentation in respective README files
- Review troubleshooting sections in Android app README
- Open an issue on GitHub with detailed logs and environment info
