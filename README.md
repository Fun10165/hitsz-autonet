# HITSZ AutoNet

Automated HITSZ (Harbin Institute of Technology, Shenzhen) campus network authentication.

## Overview

Two independent implementations sharing the same operational logic:

| Platform | Approach | Status |
|----------|----------|--------|
| **Python daemon** (macOS) | Pure HTTP — Srun portal API | Active |
| **Android App** (Kotlin) | WebView + JavaScript injection | Active |

Both detect captive portals by probing `baidu.com` and authenticate against the campus Srun portal on a 60-second loop.

## Quick Start — Python Daemon (macOS)

```bash
# Install deps
uv sync

# Create config
cat > .env << EOF
HITSZ_USERNAME=your_student_id
HITSZ_PASSWORD=your_password
EOF

# Single check
uv run hitsz_net/hitsz_net.py --once

# Install as background service (auto-starts on boot)
uv run service/install.py install --config .env

# Manage
uv run service/install.py status
uv run service/install.py uninstall
```

Logs: `~/Library/Logs/hitsz-autonet/service.log`

### How It Works

```
check_internet() ──→ baidu.com reachable? ──→ OK, sleep 60s
         │ no (captive portal redirect)
         └──→ GET /cgi-bin/get_challenge
              Compute HMAC-MD5 + XXTEA-encrypted credentials
              GET /cgi-bin/srun_portal
              Verify connectivity
```

No browser, no ChromeDriver — pure HTTP requests against the Srun portal API.

## Android App

```bash
cd android-app
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

See [android-app/README.md](android-app/README.md) for details.

## Project Structure

```
hitsz-autonet/
├── hitsz_net/              # Python daemon
│   ├── hitsz_net.py        # Main daemon (connectivity check, login, notifications, daemon loop)
│   └── srun_crypto.py      # Srun portal crypto (XXTEA, custom base64, HMAC-MD5, SHA1)
├── service/                # macOS LaunchAgent installer
│   └── install.py
├── android-app/            # Android app (Kotlin, Gradle)
│   └── app/src/main/java/com/hitsz/autonet/
├── requirements.txt        # Python deps (pip-compatible)
└── AGENTS.md               # AI assistant guidelines
```

## Requirements

- Python >= 3.13 (managed via `uv`)
- Android: JDK 17, Gradle 8.7, AGP 8.5.0, minSdk 24

## License

MIT — adapted from [siliconx/hitsz_net](https://github.com/siliconx/hitsz_net).
