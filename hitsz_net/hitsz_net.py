#!/usr/bin/env python3
import time
import os
import sys
import logging
import argparse
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.getLogger("selenium").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Default config paths
DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "hitsz-autonet" / ".env",
    Path("/etc/hitsz-autonet/.env"),
    Path.cwd() / ".env",
]

LOGIN_URL = "http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2"
CHECK_URL = "http://www.baidu.com"


def setup_logging(is_daemon=False, log_file=None):
    """Configure logging based on mode."""
    handlers = []

    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))
    else:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


def load_config(config_path=None):
    """Load configuration from environment variables or .env file."""
    # 1. Try command line config path
    if config_path:
        path = Path(config_path).expanduser()
        if path.exists():
            load_dotenv(path)
            logger.info(f"Loaded config from {path}")
            return True
        else:
            logger.error(f"Config file not found at {path}")
            return False

    # 2. Try default paths
    for path in DEFAULT_CONFIG_PATHS:
        if path.exists():
            load_dotenv(path)
            logger.info(f"Loaded config from {path}")
            return True

    logger.warning("No .env file found in default locations.")
    return False


def notify(title, message):
    """Send a system notification on macOS."""
    if sys.platform != "darwin":
        return

    try:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def check_internet():
    """
    Check connectivity by pinging a known site.
    Returns True if connected, False otherwise.
    """
    try:
        # We allow redirects because http://www.baidu.com might redirect to https://
        # or the network might redirect to a captive portal.
        response = requests.get(CHECK_URL, timeout=10)

        # 1. Check status code
        if response.status_code != 200:
            logger.info(f"Connectivity check failed: Status {response.status_code}")
            return False

        # 2. Check if we are actually on Baidu (and not a captive portal login page)
        # Captive portals often return 200 OK but with their own content.
        if "baidu.com" in response.url or "百度" in response.text:
            return True
        else:
            logger.info(f"Connectivity check failed: Redirected to {response.url}")
            return False

    except requests.RequestException as e:
        logger.warning(f"Connectivity check error: {e}")
        return False


def find_cached_driver():
    """
    Search for the latest 'chromedriver' in ~/.wdm directory.
    Returns path as string if found, else None.
    """
    try:
        wdm_dir = Path.home() / ".wdm"
        if not wdm_dir.exists():
            return None

        # Recursively find all 'chromedriver' files
        candidates = []
        for path in wdm_dir.rglob("chromedriver"):
            if path.is_file() and os.access(path, os.X_OK):
                candidates.append(path)

        if not candidates:
            return None

        # Sort by modification time (newest first) to likely get the latest version
        # Or we could try to parse version from path, but mtime is a decent proxy for "most recently downloaded"
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        best_candidate = candidates[0]
        logger.info(f"Found cached driver at: {best_candidate}")
        return str(best_candidate)

    except Exception as e:
        logger.warning(f"Error searching for cached driver: {e}")
        return None


def get_chromedriver_service(force_update=False):
    """
    Initialize ChromeDriver service, optionally handling updates.
    """
    service = None
    try:
        # Try to install/update driver via webdriver_manager if connected or forced
        # This handles downloading the correct version for current Chrome
        # We only try update if force_update is True or we likely have internet (not strictly checked here, but let manager handle it)
        install_path = ChromeDriverManager().install()
        service = Service(install_path)
        logger.info(f"ChromeDriver initialized/updated at: {install_path}")
    except Exception as e:
        logger.warning(f"Failed to install/update ChromeDriver via manager: {e}")

        # Try to find cached driver manually
        cached_path = find_cached_driver()
        if cached_path:
            logger.info(f"Using manually located cached driver: {cached_path}")
            service = Service(executable_path=cached_path)
        else:
            logger.info("Attempting to use system default 'chromedriver'...")
            # Fallback to default service (looks in PATH)
            service = Service()

    return service


def login(username, password):
    """
    Perform login using Selenium.
    Returns True if successful, False otherwise.
    """
    if not username or not password:
        logger.error("Username or password not set.")
        notify("HITSZ Net", "Configuration error: Missing credentials")
        return False

    logger.info("Attempting to login...")
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Use a consistent User-Agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = get_chromedriver_service(force_update=False)

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)

        driver.get(LOGIN_URL)
        time.sleep(2)  # Wait for page load

        # Check if already logged in (based on previous logic)
        try:
            config = driver.execute_script("return window.CONFIG;")
            if config and config.get("page") == "success":
                logger.info("Already logged in (page status).")
                return True
        except Exception:
            pass  # Continue to login if check fails

        # Input credentials
        # Wait for username field to be present
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(driver, 10)
            username_input = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_input.clear()
            username_input.send_keys(username)

            pwd_input = driver.find_element(By.ID, "password")
            pwd_input.clear()
            pwd_input.send_keys(password)

            # Click login using JS to avoid interception
            login_btn = driver.find_element(By.ID, "login-account")
            driver.execute_script("arguments[0].click();", login_btn)

            time.sleep(3)  # Wait for login to process
        except Exception as e:
            logger.error(f"Error interacting with login form: {e}")
            # Save screenshot for debug
            # driver.save_screenshot("login_error.png")
            return False

        # Verify login success
        # 1. Check page status via JS
        try:
            config = driver.execute_script("return window.CONFIG;")
            if config and config.get("page") == "success":
                logger.info("Login successful (page status).")
                return True
        except Exception:
            pass

        # 2. Fallback: Check connectivity directly
        logger.warning(
            "Page status verification failed, checking actual connectivity..."
        )
        for _ in range(3):
            if check_internet():
                logger.info("Login successful (connectivity verified).")
                return True
            time.sleep(2)

        logger.error(
            "Login failed: Page status not success and connectivity check failed."
        )
        return False

    except WebDriverException as e:
        logger.error(f"WebDriver error during login: {e}")
        if "This version of ChromeDriver only supports Chrome version" in str(e):
            logger.critical(
                "\n"
                "CRITICAL ERROR: ChromeDriver version mismatch detected.\n"
                "You are currently OFFLINE, so the script cannot auto-update the driver.\n"
                "SOLUTION:\n"
                "1. Connect to a mobile hotspot or other network temporarily.\n"
                "2. Run the script once to let it download the correct driver.\n"
                "3. OR manually download ChromeDriver matching your Chrome version and place it in PATH."
            )
            notify("HITSZ Net", "Driver Mismatch! Check logs.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="HITSZ Network Auto Login")
    parser.add_argument("--config", "-c", help="Path to configuration file (.env)")
    parser.add_argument(
        "--daemon",
        "-d",
        action="store_true",
        help="Run in background (doesn't fork, just implies service mode)",
    )
    parser.add_argument("--once", "-o", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--update-driver",
        action="store_true",
        help="Force update ChromeDriver and exit",
    )
    parser.add_argument("--log-file", help="Path to log file")

    args = parser.parse_args()

    # Setup logging
    global logger
    logger = setup_logging(is_daemon=args.daemon, log_file=args.log_file)

    logger.info("HITSZ AutoNet Monitor starting...")

    # Handle driver update request
    if args.update_driver:
        logger.info("Updating ChromeDriver...")
        try:
            service = get_chromedriver_service(force_update=True)
            if service:
                logger.info("ChromeDriver update process completed.")
                sys.exit(0)
            else:
                logger.error("ChromeDriver update failed.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during driver update: {e}")
            sys.exit(1)

    # Load config
    load_config(args.config)

    username = os.getenv("HITSZ_USERNAME")
    password = os.getenv("HITSZ_PASSWORD")

    if not username or not password:
        logger.error(
            "Please configure .env file with HITSZ_USERNAME and HITSZ_PASSWORD"
        )
        notify("HITSZ Net", "Please configure credentials")
        sys.exit(1)

    # Main loop
    while True:
        try:
            if not check_internet():
                logger.info("Internet unavailable. Initiating login sequence...")
                notify("HITSZ Net", "Network lost. Attempting login...")

                if login(username, password):
                    notify("HITSZ Net", "Login successful. You are back online.")
                    # Double check
                    if check_internet():
                        logger.info("Connectivity verified.")
                    else:
                        logger.warning(
                            "Login reported success but connectivity check failed."
                        )
                else:
                    notify("HITSZ Net", "Login failed. Will retry.")
            else:
                logger.debug("Connectivity OK.")

        except KeyboardInterrupt:
            logger.info("Stopping monitor...")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")

        if args.once:
            break

        # Wait for 60 seconds
        time.sleep(60)


if __name__ == "__main__":
    main()
