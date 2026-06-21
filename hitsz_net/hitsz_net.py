#!/usr/bin/env python3
import time
import os
import sys
import json
import random
import logging
import argparse
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from srun_crypto import (
    srun_xencode,
    srun_base64,
    srun_hmac_md5,
    srun_sha1,
    generate_callback,
    parse_jsonp,
)

# Configure logging
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


def login(username, password):
    """
    Perform login using the Srun HTTP API.
    Returns True if successful, False otherwise.
    """
    if not username or not password:
        logger.error("Username or password not set.")
        notify("HITSZ Net", "Configuration error: Missing credentials")
        return False

    logger.info("Attempting to login...")

    def request_timestamp():
        return int(time.time() * 1000) + random.randint(0, 999)

    try:
        callback = generate_callback()

        # Step 1: Get the current portal-side IP address.
        response = requests.get(
            "http://10.248.98.2/cgi-bin/rad_user_info",
            params={"callback": callback, "_": request_timestamp()},
            timeout=10,
        )
        user_info = parse_jsonp(response.text)
        if not user_info:
            logger.warning("Failed to parse Srun user info response.")
            return False

        ip = user_info.get("online_ip")
        if not ip:
            logger.warning("Srun user info response did not include online_ip.")
            return False

        # Step 2: Get the per-login challenge token.
        response = requests.get(
            "http://10.248.98.2/cgi-bin/get_challenge",
            params={
                "callback": callback,
                "username": username,
                "ip": ip,
                "_": request_timestamp(),
            },
            timeout=10,
        )
        challenge_info = parse_jsonp(response.text)
        if not challenge_info:
            logger.warning("Failed to parse Srun challenge response.")
            return False

        token = challenge_info.get("challenge")
        if not token:
            logger.warning("Srun challenge response did not include challenge token.")
            return False

        # Step 3: Compute the encrypted login parameters.
        ac_id = "1"
        n = "200"
        login_type = "1"
        hmd5 = srun_hmac_md5(password, token)
        info_json = json.dumps(
            {
                "username": username,
                "password": password,
                "ip": ip,
                "acid": ac_id,
                "enc_ver": "srun_bx1",
            },
            separators=(",", ":"),
        )
        info = "{SRBX1}" + srun_base64(srun_xencode(info_json, token))
        chkstr = (
            token
            + username
            + token
            + hmd5
            + token
            + ac_id
            + token
            + ip
            + token
            + n
            + token
            + login_type
            + token
            + info
        )
        chksum = srun_sha1(chkstr)

        # Step 4: Submit the login request.
        response = requests.get(
            "http://10.248.98.2/cgi-bin/srun_portal",
            params={
                "callback": callback,
                "action": "login",
                "username": username,
                "password": "{MD5}" + hmd5,
                "ac_id": ac_id,
                "ip": ip,
                "chksum": chksum,
                "info": info,
                "n": n,
                "type": login_type,
                "os": "macOS+15",
                "name": "Mac",
                "double_stack": "0",
                "_": request_timestamp(),
            },
            timeout=10,
        )
        login_info = parse_jsonp(response.text)
        if not login_info:
            logger.warning("Failed to parse Srun login response.")
            return False

        success_message = login_info.get("suc_msg")
        if success_message:
            success_message_lower = success_message.lower()
            if "login_ok" in success_message_lower or "success" in success_message_lower:
                logger.info(f"Login successful: {success_message}")
                return True

        error_message = login_info.get("error")
        if error_message:
            logger.warning(f"Login failed: {error_message}")
            return False

        logger.warning("Srun login response ambiguous, checking actual connectivity...")
        if check_internet():
            logger.info("Login successful (connectivity verified).")
            return True

        logger.error("Login failed: Srun response ambiguous and connectivity check failed.")
        return False

    except requests.RequestException as e:
        logger.warning(f"Login request error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        return False
    finally:
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

    # Handle deprecated driver update request
    if args.update_driver:
        logger.info("ChromeDriver no longer required since v2.0 (HTTP-based login). This flag is deprecated and has no effect.")
        sys.exit(0)

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
                    if check_internet():
                        logger.info("Connectivity verified.")
                    else:
                        logger.warning(
                            "Login reported success but connectivity check failed."
                        )
                else:
                    notify("HITSZ Net", "Login failed. Will retry.")
            else:
                logger.info("Connectivity OK — no login needed.")

        except KeyboardInterrupt:
            logger.info("Stopping monitor...")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")

        if args.once:
            logger.info("Single check complete. Exiting.")
            break

        # Wait for 60 seconds
        time.sleep(60)


if __name__ == "__main__":
    main()
