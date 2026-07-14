#!/usr/bin/env python3
import socket
import threading
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
from requests.adapters import HTTPAdapter
from urllib3 import disable_warnings
from urllib3.connection import HTTPConnection
from urllib3.exceptions import InsecureRequestWarning
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
disable_warnings(InsecureRequestWarning)

# Default config paths
DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "hitsz-autonet" / ".env",
    Path("/etc/hitsz-autonet/.env"),
    Path.cwd() / ".env",
]

LOGIN_URL = "http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2"
CHECK_URL = "http://www.baidu.com"

# Force-resolve net.hitsz.edu.cn to the portal IP, bypassing broken system DNS
# (macOS may set 114.114.114.114 which is unreachable before portal login)
_PORTAL_IP = "10.248.98.2"
_DNS_OVERRIDE = {"net.hitsz.edu.cn": _PORTAL_IP}
_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, *args, **kwargs):
    if host in _DNS_OVERRIDE:
        return _orig_getaddrinfo(_DNS_OVERRIDE[host], *args, **kwargs)
    return _orig_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo

# Darwin's IP_BOUND_IF socket option. Python's socket module does not expose it.
_DARWIN_IP_BOUND_IF = 25


class InterfaceAdapter(HTTPAdapter):
    """Bind every connection in a requests session to one macOS interface."""

    def __init__(self, interface, source_ip, *args, **kwargs):
        self.interface = interface
        self.source_ip = source_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["source_address"] = (self.source_ip, 0)
        if sys.platform == "darwin":
            interface_index = socket.if_nametoindex(self.interface)
            pool_kwargs["socket_options"] = list(
                HTTPConnection.default_socket_options
            ) + [(socket.IPPROTO_IP, _DARWIN_IP_BOUND_IF, interface_index)]
        return super().init_poolmanager(
            connections, maxsize, block=block, **pool_kwargs
        )


def create_portal_session(interface=None, source_ip=None):
    """Create a portal session, optionally pinned to a local interface and IP."""
    if bool(interface) != bool(source_ip):
        raise ValueError("interface and source_ip must be provided together")

    session = requests.Session()
    session.verify = False  # Portal cert is for net.hitsz.edu.cn, not its IP.
    session.trust_env = False
    if interface and source_ip:
        adapter = InterfaceAdapter(interface, source_ip)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    return session


def create_default_route_session():
    """Create a session pinned to the current macOS default interface."""
    interface = get_default_interface()
    source_ip = get_interface_ipv4(interface) if interface else None
    if interface and source_ip:
        return create_portal_session(interface, source_ip)
    return create_portal_session()


def get_default_interface():
    """Return the macOS default-route interface, or None when unavailable."""
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "interface":
            return value.strip() or None
    return None


def get_hardware_ports():
    """Return macOS network devices keyed by BSD interface name."""
    if sys.platform != "darwin":
        return {}
    try:
        result = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return {}

    ports = {}
    current = {}
    for line in [*result.stdout.splitlines(), ""]:
        if not line.strip():
            device = current.get("device")
            if device:
                ports[device] = current
            current = {}
            continue
        key, separator, value = line.partition(":")
        if separator:
            normalized = key.strip().lower().replace(" ", "_")
            current[normalized] = value.strip()
    return ports


def get_interface_ipv4(interface):
    """Return an interface's current IPv4 address, or None."""
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", interface],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def is_wifi_port(port):
    """Return whether a networksetup hardware-port record is Wi-Fi."""
    name = port.get("hardware_port", "").lower()
    return name in {"wi-fi", "airport"}


def is_wired_port(port):
    """Return whether a hardware-port record represents wired Ethernet."""
    name = port.get("hardware_port", "").lower()
    return any(token in name for token in ("ethernet", "usb", "lan"))


def query_user_info(session):
    """Query Srun state for the session's bound source interface."""
    response = session.get(
        f"http://{_PORTAL_IP}/cgi-bin/rad_user_info",
        params={"callback": generate_callback(), "_": int(time.time() * 1000)},
        timeout=10,
    )
    response.raise_for_status()
    info = parse_jsonp(response.text)
    if not info:
        raise requests.RequestException("Failed to parse Srun user info response")
    return info


def parse_online_devices(user_info):
    """Return normalized records from Srun's nested online-device payload."""
    devices = user_info.get("online_device_detail")
    if isinstance(devices, str):
        try:
            devices = json.loads(devices)
        except json.JSONDecodeError:
            return []
    if isinstance(devices, dict):
        return [value for value in devices.values() if isinstance(value, dict)]
    if isinstance(devices, list):
        return [value for value in devices if isinstance(value, dict)]
    return []


def normalize_mac(value):
    """Normalize a MAC address for comparison."""
    return "".join(
        character
        for character in (value or "").lower()
        if character in "0123456789abcdef"
    )


def find_verified_wifi_session(user_info, username, wifi_ip, wifi_mac):
    """Return True only when Srun identifies this exact local Wi-Fi session."""
    if user_info.get("error") != "ok" or user_info.get("online_ip") != wifi_ip:
        return False

    response_username = user_info.get("user_name") or user_info.get("username")
    if response_username and response_username != username:
        logger.error("Wi-Fi session belongs to a different account; refusing logout.")
        return False

    devices = parse_online_devices(user_info)
    if not devices:
        return True

    expected_mac = normalize_mac(wifi_mac)
    for device in devices:
        if device.get("ip") != wifi_ip:
            continue
        device_mac = normalize_mac(device.get("user_mac") or device.get("mac"))
        if not expected_mac or not device_mac or device_mac == expected_mac:
            return True

    logger.error("Wi-Fi IP was not paired with this interface MAC; refusing logout.")
    return False


def logout_wifi_session(session, username, wifi_ip):
    """Ask Srun DM to logout one explicitly identified IP session."""
    request_time = int(time.time())
    unbind = "1"
    sign = srun_sha1(f"{request_time}{username}{wifi_ip}{unbind}{request_time}")
    response = session.get(
        f"http://{_PORTAL_IP}/cgi-bin/rad_user_dm",
        params={
            "callback": generate_callback(),
            "user_ip": wifi_ip,
            "username": username,
            "time": str(request_time),
            "unbind": unbind,
            "sign": sign,
            "_": int(time.time() * 1000),
        },
        timeout=10,
    )
    response.raise_for_status()
    result = parse_jsonp(response.text)
    if not result:
        raise requests.RequestException("Failed to parse Srun logout response")
    return result


def handle_wired_handoff(username):
    """Safely remove this Mac's Wi-Fi session after wired Ethernet takes over."""
    if sys.platform != "darwin":
        return False

    default_interface = get_default_interface()
    ports = get_hardware_ports()
    default_port = ports.get(default_interface, {})
    if not default_interface or not is_wired_port(default_port):
        return False

    wired_ip = get_interface_ipv4(default_interface)
    if not wired_ip:
        return False

    wifi_candidates = [
        (interface, port)
        for interface, port in ports.items()
        if is_wifi_port(port) and interface != default_interface
    ]
    for wifi_interface, wifi_port in wifi_candidates:
        wifi_ip = get_interface_ipv4(wifi_interface)
        if not wifi_ip or wifi_ip == wired_ip:
            continue

        try:
            with create_portal_session(wifi_interface, wifi_ip) as wifi_session:
                wifi_info = query_user_info(wifi_session)
                if not find_verified_wifi_session(
                    wifi_info,
                    username,
                    wifi_ip,
                    wifi_port.get("ethernet_address"),
                ):
                    continue

                # Route changes can race the probe. Never logout unless wired is
                # still the default immediately before the destructive request.
                if get_default_interface() != default_interface:
                    logger.warning(
                        "Default route changed during handoff; skipping logout."
                    )
                    return False

                logger.info(
                    "Wired interface %s (%s) took over; logging out verified Wi-Fi session %s (%s).",
                    default_interface,
                    wired_ip,
                    wifi_interface,
                    wifi_ip,
                )
                result = logout_wifi_session(wifi_session, username, wifi_ip)
                if result.get("error") != "ok":
                    logger.error(
                        "Targeted Wi-Fi logout was not accepted: %s",
                        result.get("error"),
                    )
                    return False

                for _ in range(3):
                    time.sleep(1)
                    post_logout_info = query_user_info(wifi_session)
                    if (
                        post_logout_info.get("error") == "not_online_error"
                        and post_logout_info.get("online_ip") != wifi_ip
                    ):
                        logger.info(
                            "Confirmed Wi-Fi session %s is no longer online.", wifi_ip
                        )
                        return True

                logger.error(
                    "Srun accepted the logout request, but Wi-Fi session %s is still online.",
                    wifi_ip,
                )
                return False
        except (OSError, requests.RequestException, ValueError) as error:
            logger.warning("Unable to inspect or logout Wi-Fi session: %s", error)
            return False

    return False


def watch_lid_events(stop_event, wake_event):
    """Background thread: detect lid-open events via ioreg polling (macOS only)."""
    was_closed = False
    while not stop_event.is_set():
        try:
            result = subprocess.run(
                ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_closed = '"AppleClamshellState" = Yes' in result.stdout
            if was_closed and not is_closed:
                logger.info("Lid opened — triggering connectivity check.")
                wake_event.set()
            was_closed = is_closed
        except Exception:
            pass
        stop_event.wait(timeout=2)


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
    Check connectivity by probing baidu.com.
    Returns True if connected, False if captive portal / no network.
    """
    try:
        response = requests.get(CHECK_URL, timeout=10)
        if response.status_code != 200:
            logger.info(f"Connectivity check failed: Status {response.status_code}")
            return False
        if "baidu.com" in response.url or "百度" in response.text:
            return True
        logger.info(f"Connectivity check failed: Redirected to {response.url}")
        return False
    except requests.RequestException as e:
        # DNS resolution might fail if macOS set a non-working DNS server
        # (e.g. 114.114.114.114) before portal login. Don't treat this as
        # "connected" — it means we need to log in.
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

    def request_timestamp():
        return int(time.time() * 1000) + random.randint(0, 999)

    session = create_default_route_session()
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempting to login... (attempt {attempt}/{max_retries})")
        try:
            callback = generate_callback()

            # Step 1: Get the current portal-side IP address.
            response = session.get(
                "http://10.248.98.2/cgi-bin/rad_user_info",
                params={"callback": callback, "_": request_timestamp()},
                timeout=10,
            )
            user_info = parse_jsonp(response.text)
            if not user_info:
                raise requests.RequestException(
                    "Failed to parse Srun user info response"
                )

            ip = user_info.get("online_ip")
            if not ip:
                raise requests.RequestException(
                    "Srun user info response missing online_ip"
                )

            # Step 2: Get the per-login challenge token.
            response = session.get(
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
                raise requests.RequestException(
                    "Failed to parse Srun challenge response"
                )

            token = challenge_info.get("challenge")
            if not token:
                raise requests.RequestException("Srun challenge response missing token")

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
            response = session.get(
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
                raise requests.RequestException("Failed to parse Srun login response")

            success_message = login_info.get("suc_msg")
            if success_message and (
                "login_ok" in success_message.lower()
                or "success" in success_message.lower()
            ):
                logger.info(f"Login successful: {success_message}")
                return True

            error_message = login_info.get("error")
            if error_message:
                logger.warning(f"Login failed: {error_message}")
                return False

            # Ambiguous response — verify via connectivity
            logger.warning("Srun login response ambiguous, checking connectivity...")
            if check_internet():
                logger.info("Login successful (connectivity verified).")
                return True

            logger.error(
                "Login failed: ambiguous response and connectivity check failed."
            )
            return False

        except requests.RequestException as e:
            logger.warning(f"Login attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait = 5 * attempt
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error("All login attempts exhausted.")
                return False
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            return False

    return False


def main():
    parser = argparse.ArgumentParser(description="HITSZ Network Auto Login")
    parser.add_argument("--config", "-c", help="Path to configuration file (.env)")
    parser.add_argument(
        "--daemon",
        "-d",
        action="store_true",
        help="Run as service (implies continuous mode)",
    )
    parser.add_argument("--once", "-o", action="store_true", help="Check once and exit")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60, 0 = no auto checks)",
    )
    parser.add_argument(
        "--wake",
        action="store_true",
        help="Also trigger check on lid-open / wake from sleep (macOS only)",
    )
    parser.add_argument(
        "--update-driver",
        action="store_true",
        help="Deprecated: ChromeDriver no longer required",
    )
    parser.add_argument("--log-file", help="Path to log file")

    args = parser.parse_args()

    # Setup logging
    global logger
    logger = setup_logging(is_daemon=args.daemon, log_file=args.log_file)
    logger.info("HITSZ AutoNet Monitor starting...")

    if args.update_driver:
        logger.info(
            "ChromeDriver no longer required (HTTP-based login). This flag is deprecated."
        )
        sys.exit(0)

    load_config(args.config)
    username = os.getenv("HITSZ_USERNAME")
    password = os.getenv("HITSZ_PASSWORD")
    if not username or not password:
        logger.error(
            "Please configure .env file with HITSZ_USERNAME and HITSZ_PASSWORD"
        )
        notify("HITSZ Net", "Please configure credentials")
        sys.exit(1)

    interval = args.interval
    wake_event = threading.Event()
    stop_event = threading.Event()
    watcher = None

    if args.wake:
        watcher = threading.Thread(
            target=watch_lid_events, args=(stop_event, wake_event), daemon=True
        )
        watcher.start()
        logger.info("Lid-open watcher started.")

    def run_check():
        handle_wired_handoff(username)
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

    # Main loop
    while True:
        try:
            run_check()
        except KeyboardInterrupt:
            logger.info("Stopping monitor...")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")

        if args.once:
            logger.info("Single check complete. Exiting.")
            break

        if interval == 0 and not args.wake:
            logger.info("No interval or wake trigger configured. Exiting.")
            break

        triggered = False
        if args.wake:
            timeout = interval if interval > 0 else None
            triggered = wake_event.wait(timeout=timeout)
            if triggered:
                wake_event.clear()
                logger.info("Wake event triggered.")
        elif interval > 0:
            time.sleep(interval)


if __name__ == "__main__":
    main()
