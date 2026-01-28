# AGENTS.md - HITSZ Network Automation Project

## Project Overview
Python-based network automation daemon for HITSZ campus network authentication. Uses Selenium for web automation and runs as a macOS LaunchAgent service.

## Build/Lint/Test Commands

### Dependencies
```bash
# Install dependencies
pip3 install -r requirements.txt

# Install in development mode (if needed)
pip3 install -e .
```

### Running the Script
```bash
# Run once (single authentication attempt)
python3 hitsz_net/hitsz_net.py --once

# Run as foreground daemon (checks every 60s)
python3 hitsz_net/hitsz_net.py --daemon

# Specify custom config file
python3 hitsz_net/hitsz_net.py --config path/to/.env

# Update ChromeDriver and exit
python3 hitsz_net/hitsz_net.py --update-driver
```

### Service Management (macOS)
```bash
# Install as LaunchAgent service
python3 service/install.py install --config .env

# Check service status
python3 service/install.py status

# Uninstall service
python3 service/install.py uninstall

# View service logs
tail -f ~/Library/Logs/hitsz-autonet/service.log
tail -f ~/Library/Logs/hitsz-autonet/error.log
```

### Testing
No formal test suite exists yet. Manual testing:
```bash
# Test connectivity check
python3 -c "from hitsz_net.hitsz_net import check_internet; print(check_internet())"

# Test config loading
python3 -c "from hitsz_net.hitsz_net import load_config; load_config('.env')"
```

## Code Style Guidelines

### Import Order
```python
# Standard library (alphabetical)
import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Third-party (alphabetical)
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

### Formatting
- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **String quotes**: Double quotes `"` for strings, single quotes for dict keys when needed
- **Trailing commas**: Omitted in single-line structures
- **Blank lines**: 2 blank lines between top-level functions/classes

### Types & Annotations
- **No type hints currently used** - project is un-typed
- When adding types, use standard library `typing` module
- Return types should be explicit: `-> bool`, `-> str`, `-> None`

### Naming Conventions
- **Functions/variables**: `snake_case` (e.g., `check_internet`, `log_file`)
- **Classes**: `PascalCase` (e.g., `ServiceInstaller`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `LOGIN_URL`, `CHECK_URL`, `LABEL`)
- **Private/internal**: Leading underscore `_helper_function`

### Error Handling
```python
# Broad exception catching with logging
try:
    # Risky operation
    driver.get(LOGIN_URL)
except WebDriverException as e:
    logger.error(f"WebDriver error: {e}")
    # Handle specific error
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Generic fallback
finally:
    # Cleanup (e.g., driver.quit())
    pass
```

### Logging
- Use standard `logging` module, not `print()`
- Log levels: `DEBUG` < `INFO` < `WARNING` < `ERROR` < `CRITICAL`
- Format: `"%(asctime)s - %(levelname)s - %(message)s"`
```python
logger.info("Normal operation message")
logger.warning("Something unusual but not fatal")
logger.error("Operation failed")
```

### Configuration
- Credentials in `.env` files (never commit)
- Default config paths checked in order:
  1. `~/.config/hitsz-autonet/.env`
  2. `/etc/hitsz-autonet/.env`
  3. `./.env`
- Use `pathlib.Path` for all file paths
- Environment variables: `HITSZ_USERNAME`, `HITSZ_PASSWORD`

### Selenium Best Practices
- Always use headless mode in production: `--headless`
- Set explicit timeouts: `driver.set_page_load_timeout(30)`
- Use `WebDriverWait` for element presence checks
- Always `driver.quit()` in `finally` block
- Prefer `execute_script("arguments[0].click()")` over `.click()` for reliability
- Suppress Selenium logs: `logging.getLogger("selenium").setLevel(logging.ERROR)`

### Code Organization
- Main logic in `hitsz_net/hitsz_net.py`
- Service installer in `service/install.py`
- Configuration files at project root or `~/.config/hitsz-autonet/`
- Logs in `~/Library/Logs/hitsz-autonet/` (macOS)

## Platform-Specific Notes

### macOS (Primary)
- Uses AppleScript for notifications: `osascript -e 'display notification...'`
- LaunchAgent plist in `~/Library/LaunchAgents/`
- Service runs on `NetworkState` change (KeepAlive)

### Linux (Secondary Support)
- Notifications: Use `notify-send` or similar
- Service management: systemd unit files
- Config paths: `~/.config/hitsz-autonet/` or `/etc/hitsz-autonet/`

## Key Files

- `hitsz_net/hitsz_net.py` - Main authentication script
- `service/install.py` - macOS LaunchAgent installer
- `requirements.txt` - Python dependencies
- `.env` - Credentials (git-ignored)
- `CLAUDE.md` - Project documentation index
- `requirements.md` - Comprehensive requirements doc

## Development Workflow

1. **Setup**: Create `.env` with credentials
2. **Test**: Run with `--once` flag first
3. **Iterate**: Modify code, test with direct invocation
4. **Service**: Install as LaunchAgent only after validation
5. **Debug**: Check logs in `~/Library/Logs/hitsz-autonet/`

## Common Pitfalls

1. **ChromeDriver mismatch**: Run `--update-driver` when Chrome updates
2. **Offline driver updates**: Can't auto-update without internet - use mobile hotspot
3. **Missing config**: Service fails silently if `.env` not found
4. **Captive portal false positives**: `check_internet()` validates Baidu content, not just HTTP 200
5. **Permission issues**: Ensure script is executable, paths are absolute in plist

## Extending the Project

- Add new network detection methods in `check_internet()`
- Support additional notification backends in `notify()`
- Implement retry strategies in `login()`
- Add structured logging (JSON format for parsing)
- Create pytest test suite for core functions
