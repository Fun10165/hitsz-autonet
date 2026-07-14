# HITSZ Network Auto-Login - Python Daemon

Pure-HTTP login daemon for the HITSZ campus network and macOS LaunchAgent.

## Overview

This Python script provides automated authentication for HITSZ campus network. It runs as a background service on macOS (via LaunchAgent) and detects when network access is blocked by the captive portal, then automatically logs in.

## Features

- **Pure HTTP Login**: Uses the Srun challenge and portal APIs; no browser or driver
- **Captive Portal Detection**: Validates the Baidu response instead of trusting HTTP 200
- **Safe Wired Handoff**: Removes only a verified local Wi-Fi IP session when USB/Ethernet becomes the default route
- **Interface Binding**: Pins Srun probes and login requests to the intended macOS interface
- **macOS Service Integration**: Runs as a LaunchAgent and can react to lid-open events

## Installation

### Prerequisites

- Python 3.13+
- `uv`
- macOS for LaunchAgent, interface binding, and wired-handoff features

### Setup

1. Install Python dependencies:
```bash
uv sync
```

2. Create configuration file `.env`:
```bash
HITSZ_USERNAME=your_username
HITSZ_PASSWORD=your_password
```

Credentials are used only for Srun HTTP login. Wired handoff identifies the local Wi-Fi and wired interfaces from macOS `networksetup`, `route`, and `ipconfig` output.

Configuration file locations (checked in order):
- `~/.config/hitsz-autonet/.env`
- `/etc/hitsz-autonet/.env`
- `./.env` (current directory)

### Install as macOS Service

```bash
uv run service/install.py install --config .env
```

Check service status:
```bash
uv run service/install.py status
```

Uninstall service:
```bash
uv run service/install.py uninstall
```

## Manual Usage

Run once (single authentication attempt):
```bash
uv run hitsz_net/hitsz_net.py --once
```

Run as foreground daemon (checks every 60 seconds):
```bash
uv run hitsz_net/hitsz_net.py --daemon
```

## How It Works

1. **Route Inspection**: Detects the current macOS default interface
2. **Wired Handoff**: If wired is active, verifies the exact bound Wi-Fi session before targeted logout and confirms the post-logout state
3. **Network Check**: Probes Baidu and detects captive-portal redirects or substituted content
4. **Srun Login**: Gets a challenge, computes HMAC-MD5/XXTEA/SHA1 parameters, and submits `/cgi-bin/srun_portal`
5. **Verification**: Rechecks connectivity and repeats every 60 seconds

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

LaunchAgent plist: `~/Library/LaunchAgents/com.github.hitsz.autonet.plist`

The service:
- Runs on network state changes (KeepAlive NetworkState trigger)
- Automatically restarts on failure
- Runs in user context (LaunchAgent)

## Troubleshooting

### Service Won't Start

1. Check if credentials are configured in `.env`
2. Verify `.env` file is in one of the default locations
3. Check logs at `~/Library/Logs/hitsz-autonet/error.log`
4. Run `uv run hitsz_net/hitsz_net.py --once` and inspect the result

### Authentication Fails

1. Verify credentials are correct in `.env`
2. Check if campus portal is accessible: `http://10.248.98.2`
3. Test with `--once` flag for detailed output
4. Check logs for specific error messages

### Wired Handoff Does Not Remove Wi-Fi Session

1. Confirm `route -n get default` reports the USB/Ethernet interface.
2. Confirm both interfaces still have distinct IPv4 addresses with `ipconfig getifaddr <interface>`.
3. Check logs for an account/IP/MAC mismatch or a route-race refusal.
4. The daemon deliberately skips logout when the Wi-Fi-bound precheck returns `not_online_error`.

## Platform Support

- **macOS**: Full support with LaunchAgent integration
- **Linux**: Basic support (requires manual daemon setup or cron job)

For Linux users, consider setting up a systemd service or cron job for automated execution.

## Dependencies

- `requests` - Connectivity checks and Srun HTTP API calls
- `python-dotenv` - Environment variable loading

See `requirements.txt` for complete dependency list.

## Acknowledgments

This project is inspired by and adapted from the original [hitsz_net](https://github.com/siliconx/hitsz_net) project by siliconx. The original project provided the foundation for HITSZ campus network authentication automation.

## Related Projects

- **Android App**: Native Android implementation available in `../android-app/`
  - See [android-app/README.md](../android-app/README.md) for details

## License

Same license terms as the original hitsz_net project.
