# HITSZ Network Auto-Login - Python Daemon

Pure-HTTP login daemon for the HITSZ campus network and macOS LaunchAgent.

## Overview

This Python script provides automated authentication for HITSZ campus network. It runs as a background service on macOS (via LaunchAgent) and detects when network access is blocked by the captive portal, then automatically logs in.

## Features

- **Pure HTTP Login**: Uses the Srun challenge and portal APIs; no browser or driver
- **Captive Portal Detection**: Validates the Baidu response instead of trusting HTTP 200
- **Persistent Session Reconciliation**: Remembers per-interface IP history and removes old account-owned sessions after DHCP/interface changes
- **MAC Change Alerts**: Records MACs as diagnostic metadata and notifies on changes without blocking logout
- **Interface Binding**: Pins Srun probes, logout, and login requests to the intended macOS interface
- **Detailed Capacity Errors**: Reports portal codes such as `E2620`, route/interface context, device totals, and returned device summaries
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

Credentials are used only for Srun HTTP login. Session reconciliation identifies interfaces from macOS `networksetup`, `route`, `ipconfig`, and `ifconfig` output.

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

1. **Historical Reconciliation**: Loads remembered interface/IP sessions and directly queries each non-current historical IP
2. **Account Verification**: Logs out only when Srun still reports that exact IP under the configured account; MAC mismatches notify but do not block
3. **Destructive-Action Guard**: Rechecks the default route, sends an IP-targeted `rad_user_dm`, and confirms the old IP is offline before deleting its record
4. **Network Check**: Probes Baidu and detects captive-portal redirects or substituted content
5. **Srun Login**: Gets a challenge, computes HMAC-MD5/XXTEA/SHA1 parameters, and submits `/cgi-bin/srun_portal`
6. **Observation**: Records the current session after login or an online check, then repeats every 60 seconds

## Logs

Service logs and state are stored at:
- `~/Library/Logs/hitsz-autonet/service.log` - LaunchAgent stdout
- `~/Library/Logs/hitsz-autonet/error.log` - Python logger output and LaunchAgent stderr
- `~/Library/Application Support/hitsz-autonet/session-state.json` - per-account interface/IP history (mode `0600`)

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

### Historical Session Is Not Removed

1. Inspect `session-state.json` and confirm the old IP was previously observed under the configured account.
2. Confirm `rad_user_info?ip=<old-ip>` still reports that IP online under the same account; offline or other-account records are pruned without logout.
3. Check `error.log` for a route-race refusal or rejected `rad_user_dm` response.
4. A MAC mismatch is only a warning/notification and does not prevent an account-matching historical IP from being logged out.
5. Logout is counted only after a post-operation query confirms the target IP is offline.

### Online Device Limit Reached

For Srun capacity failures such as `E2620`, inspect the notification and `error.log`. They include the raw portal code/message, current default interface/hardware port/IP, reported device total, and any device rows returned by the portal.

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
