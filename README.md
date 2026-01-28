# HITSZ Network Auto-Login Daemon

Automated login service for HITSZ campus network, designed for macOS (LaunchAgent) and adaptable for other systems.

## Features

- **Automated Login**: Detects network status and logs in when needed.
- **Captive Portal Detection**: Handles network redirects intelligently.
- **macOS Service Integration**: Runs as a background service via LaunchAgent.
- **Resilient**: Auto-restart on failure, network change detection.
- **Configurable**: Simple `.env` configuration.

## Project Structure

- `hitsz_net/hitsz_net.py`: Main logic script.
- `service/install.py`: Service installer for macOS.
- `requirements.txt`: Python dependencies.
- `research-findings/`: Project documentation and research.

## Installation

### 1. Prerequisites

Ensure you have Python 3.8+ and Chrome installed.

```bash
# Install dependencies
pip3 install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root or `~/.config/hitsz-autonet/.env`:

```bash
HITSZ_USERNAME=your_username
HITSZ_PASSWORD=your_password
```

### 3. Install Service (macOS)

Register the script as a background service that starts on login:

```bash
python3 service/install.py install --config .env
```

To check status:
```bash
python3 service/install.py status
```

To uninstall:
```bash
python3 service/install.py uninstall
```

## Manual Usage

You can also run the script directly:

```bash
# Run once
python3 hitsz_net/hitsz_net.py --once

# Run as foreground daemon
python3 hitsz_net/hitsz_net.py --daemon
```

## Logs

- Service logs: `~/Library/Logs/hitsz-autonet/service.log`
- Error logs: `~/Library/Logs/hitsz-autonet/error.log`
