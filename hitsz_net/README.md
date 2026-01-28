# HITSZ Network Auto-Login - Python Daemon

Automated login daemon for HITSZ campus network using Selenium WebDriver.

## Overview

This Python script provides automated authentication for HITSZ campus network. It runs as a background service on macOS (via LaunchAgent) and detects when network access is blocked by the captive portal, then automatically logs in.

## Features

- **Automated Login**: Detects network status and logs in when needed
- **Captive Portal Detection**: Identifies when network access requires authentication
- **macOS Service Integration**: Runs as LaunchAgent for automatic startup
- **ChromeDriver Auto-Management**: Automatically downloads compatible ChromeDriver
- **Headless Operation**: Runs without visible browser windows

## Installation

### Prerequisites

- Python 3.8+
- Chrome browser installed
- macOS 10.15+ (for LaunchAgent features)

### Setup

1. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

2. Create configuration file `.env`:
```bash
HITSZ_USERNAME=your_username
HITSZ_PASSWORD=your_password
```

Configuration file locations (checked in order):
- `~/.config/hitsz-autonet/.env`
- `/etc/hitsz-autonet/.env`
- `./.env` (current directory)

### Install as macOS Service

```bash
python3 service/install.py install --config .env
```

Check service status:
```bash
python3 service/install.py status
```

Uninstall service:
```bash
python3 service/install.py uninstall
```

## Manual Usage

Run once (single authentication attempt):
```bash
python3 hitsz_net/hitsz_net.py --once
```

Run as foreground daemon (checks every 60 seconds):
```bash
python3 hitsz_net/hitsz_net.py --daemon
```

Update ChromeDriver to match Chrome version:
```bash
python3 hitsz_net/hitsz_net.py --update-driver
```

## How It Works

1. **Network Check**: Performs HTTP request to baidu.com
2. **Captive Portal Detection**: Checks if response redirects to campus portal
3. **Automated Login**: If captive portal detected, launches headless Chrome to authenticate
4. **Verification**: Validates authentication success via `window.CONFIG.page` status
5. **Continuous Monitoring**: Repeats check every 60 seconds

## Logs

Service logs are stored at:
- `~/Library/Logs/hitsz-autonet/service.log` - Normal operation logs
- `~/Library/Logs/hitsz-autonet/error.log` - Error logs

View logs:
```bash
tail -f ~/Library/Logs/hitsz-autonet/service.log
```

## Configuration

### Environment Variables

- `HITSZ_USERNAME` - Campus network username
- `HITSZ_PASSWORD` - Campus network password

### Service Configuration

LaunchAgent plist: `~/Library/LaunchAgents/edu.hitsz.autonet.plist`

The service:
- Runs on network state changes (KeepAlive NetworkState trigger)
- Automatically restarts on failure
- Runs in user context (LaunchAgent)

## Troubleshooting

### ChromeDriver Issues

If you get ChromeDriver version mismatch errors:
```bash
python3 hitsz_net/hitsz_net.py --update-driver
```

Note: ChromeDriver updates require internet access. If you're offline due to captive portal, use mobile hotspot temporarily.

### Service Won't Start

1. Check if credentials are configured in `.env`
2. Verify `.env` file is in one of the default locations
3. Check logs at `~/Library/Logs/hitsz-autonet/error.log`
4. Ensure Chrome browser is installed

### Authentication Fails

1. Verify credentials are correct in `.env`
2. Check if campus portal is accessible: `http://10.248.98.2`
3. Test with `--once` flag for detailed output
4. Check logs for specific error messages

## Platform Support

- **macOS**: Full support with LaunchAgent integration
- **Linux**: Basic support (requires manual daemon setup or cron job)

For Linux users, consider setting up a systemd service or cron job for automated execution.

## Dependencies

- `selenium>=4.0.0` - Browser automation
- `webdriver-manager>=3.8.0` - ChromeDriver management
- `requests>=2.25.0` - HTTP client for network testing
- `python-dotenv` - Environment variable loading

See `requirements.txt` for complete dependency list.

## Acknowledgments

This project is inspired by and adapted from the original [hitsz_net](https://github.com/siliconx/hitsz_net) project by siliconx. The original project provided the foundation for HITSZ campus network authentication automation.

## Related Projects

- **Android App**: Native Android implementation available in `../android-app/`
  - See [android-app/README.md](../android-app/README.md) for details

## License

Same license terms as the original hitsz_net project.
