#!/usr/bin/env python3
import socket
import tempfile
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
from dataclasses import dataclass
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
_STATE_VERSION = 1
_STATE_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "hitsz-autonet"
    / "session-state.json"
)
_STATE_MAX_SESSIONS_PER_INTERFACE = 64
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


def get_interface_mac(interface):
    """Return the active MAC address reported by ifconfig, or None."""
    try:
        result = subprocess.run(
            ["ifconfig", interface],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for line in result.stdout.splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0] == "ether":
            return fields[1]
    return None


def is_wifi_port(port):
    """Return whether a networksetup hardware-port record is Wi-Fi."""
    name = port.get("hardware_port", "").lower()
    return name in {"wi-fi", "airport"}


def is_wired_port(port):
    """Return whether a hardware-port record represents wired Ethernet."""
    name = port.get("hardware_port", "").lower()
    return any(token in name for token in ("ethernet", "usb", "lan"))


def query_user_info(session, target_ip=None):
    """Query Srun state, optionally for one explicitly specified IP."""
    params = {"callback": generate_callback(), "_": int(time.time() * 1000)}
    if target_ip:
        params["ip"] = target_ip
    response = session.get(
        f"http://{_PORTAL_IP}/cgi-bin/rad_user_info",
        params=params,
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


def empty_session_state():
    """Return a new persistent session-state document."""
    return {"version": _STATE_VERSION, "accounts": {}}


def load_session_state(path=_STATE_PATH):
    """Load persistent interface/session history, failing closed if corrupted."""
    if not path.exists():
        return empty_session_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Cannot read session state %s: %s", path, error)
        return None
    if not isinstance(state, dict) or state.get("version") != _STATE_VERSION:
        logger.error(
            "Unsupported session state format at %s; reconciliation disabled.", path
        )
        return None
    if not isinstance(state.get("accounts"), dict):
        logger.error(
            "Invalid session state accounts at %s; reconciliation disabled.", path
        )
        return None
    return state


def save_session_state(state, path=_STATE_PATH):
    """Atomically persist session state with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            os.chmod(temporary_path, 0o600)
            json.dump(state, temporary, ensure_ascii=False, sort_keys=True, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
        raise


def session_identity(user_info, target_ip):
    """Extract the account and portal MAC for one Srun IP session."""
    if user_info.get("error") != "ok" or user_info.get("online_ip") != target_ip:
        return None

    username = user_info.get("user_name") or user_info.get("username")
    portal_mac = normalize_mac(user_info.get("user_mac") or user_info.get("mac"))
    matched_device = None
    for device in parse_online_devices(user_info):
        if device.get("ip") == target_ip:
            matched_device = device
            device_mac = normalize_mac(device.get("user_mac") or device.get("mac"))
            if device_mac:
                portal_mac = device_mac
            break

    return {
        "username": username,
        "portal_mac": portal_mac,
        "rad_online_id": (
            (matched_device or {}).get("rad_online_id")
            or user_info.get("rad_online_id")
            or ""
        ),
    }


def remember_session(
    state,
    username,
    interface,
    port,
    ip,
    user_info,
    observed_at=None,
):
    """Remember a freshly observed online session for one local interface."""
    identity = session_identity(user_info, ip)
    if not identity or identity["username"] != username:
        return False

    observed_at = observed_at or int(time.time())
    account = state["accounts"].setdefault(username, {"interfaces": {}})
    interfaces = account.setdefault("interfaces", {})
    interface_state = interfaces.setdefault(interface, {"sessions": {}})
    hardware_port = port.get("hardware_port", "")
    hardware_mac = normalize_mac(
        get_interface_mac(interface) or port.get("ethernet_address")
    )
    metadata_changed = (
        interface_state.get("hardware_port") != hardware_port
        or interface_state.get("hardware_mac") != hardware_mac
    )
    interface_state["hardware_port"] = hardware_port
    interface_state["hardware_mac"] = hardware_mac
    sessions = interface_state.setdefault("sessions", {})
    existing = sessions.get(ip, {})
    if (
        existing
        and not metadata_changed
        and existing.get("portal_mac") == identity["portal_mac"]
        and existing.get("rad_online_id") == identity["rad_online_id"]
        and observed_at - int(existing.get("last_seen", 0)) < 300
    ):
        return False
    sessions[ip] = {
        "first_seen": existing.get("first_seen", observed_at),
        "last_seen": observed_at,
        "portal_mac": identity["portal_mac"],
        "rad_online_id": identity["rad_online_id"],
    }

    if len(sessions) > _STATE_MAX_SESSIONS_PER_INTERFACE:
        oldest = sorted(sessions, key=lambda item: sessions[item].get("last_seen", 0))
        for stale_ip in oldest[: len(sessions) - _STATE_MAX_SESSIONS_PER_INTERFACE]:
            del sessions[stale_ip]
    return True


def remember_matching_local_sessions(
    state, username, ports, user_info, observed_at=None
):
    """Seed history from account sessions whose MAC matches a local interface."""
    remembered = 0
    local_interfaces = {}
    for interface, port in ports.items():
        local_mac = normalize_mac(
            get_interface_mac(interface) or port.get("ethernet_address")
        )
        if local_mac:
            local_interfaces[local_mac] = (interface, port)

    for device in parse_online_devices(user_info):
        device_ip = device.get("ip")
        device_mac = normalize_mac(device.get("user_mac") or device.get("mac"))
        matched = local_interfaces.get(device_mac)
        if not device_ip or not matched:
            continue
        interface, port = matched
        device_info = {
            "error": "ok",
            "online_ip": device_ip,
            "user_name": device.get("user_name") or username,
            "user_mac": device_mac,
            "rad_online_id": device.get("rad_online_id") or "",
        }
        remembered += remember_session(
            state,
            username,
            interface,
            port,
            device_ip,
            device_info,
            observed_at,
        )
    return remembered


def forget_session(state, username, interface, ip):
    """Remove one confirmed-offline or identity-conflicted historical session."""
    account = state.get("accounts", {}).get(username, {})
    interface_state = account.get("interfaces", {}).get(interface, {})
    sessions = interface_state.get("sessions", {})
    return sessions.pop(ip, None) is not None


def observe_default_session(username, state_path=_STATE_PATH):
    """Persist the currently online default-interface session."""
    if sys.platform != "darwin":
        return False
    default_interface = get_default_interface()
    ports = get_hardware_ports()
    port = ports.get(default_interface, {})
    ip = get_interface_ipv4(default_interface) if default_interface else None
    if not default_interface or not ip or not port:
        return False

    state = load_session_state(state_path)
    if state is None:
        return False
    try:
        with create_portal_session(default_interface, ip) as session:
            user_info = query_user_info(session, ip)
    except (OSError, requests.RequestException, ValueError) as error:
        logger.warning("Unable to observe current Srun session: %s", error)
        return False

    changed = remember_session(state, username, default_interface, port, ip, user_info)
    changed |= bool(remember_matching_local_sessions(state, username, ports, user_info))
    if not changed:
        return False
    try:
        save_session_state(state, state_path)
    except OSError as error:
        logger.error("Unable to persist session state: %s", error)
        return False
    logger.info(
        "Remembered %s session %s for interface %s.", username, ip, default_interface
    )
    return True


def verify_historical_session(user_info, username, target_ip):
    """Require fresh server confirmation that the target belongs to the account."""
    identity = session_identity(user_info, target_ip)
    return bool(identity and identity["username"] == username)


def logout_target_session(session, username, target_ip):
    """Ask Srun DM to logout one explicitly identified account IP session."""
    request_time = int(time.time())
    unbind = "1"
    sign = srun_sha1(f"{request_time}{username}{target_ip}{unbind}{request_time}")
    response = session.get(
        f"http://{_PORTAL_IP}/cgi-bin/rad_user_dm",
        params={
            "callback": generate_callback(),
            "user_ip": target_ip,
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


def reconcile_historical_sessions(username, state_path=_STATE_PATH):
    """Logout this account's remembered non-current WLAN/Ethernet sessions."""
    if sys.platform != "darwin":
        return 0

    default_interface = get_default_interface()
    ports = get_hardware_ports()
    default_port = ports.get(default_interface, {})
    current_ip = get_interface_ipv4(default_interface) if default_interface else None
    if (
        not default_interface
        or not current_ip
        or not (is_wifi_port(default_port) or is_wired_port(default_port))
    ):
        return 0

    state = load_session_state(state_path)
    if state is None:
        return 0
    account = state.get("accounts", {}).get(username, {})
    interface_states = account.get("interfaces", {})
    candidates = []
    for interface, interface_state in interface_states.items():
        for target_ip, record in interface_state.get("sessions", {}).items():
            if target_ip == current_ip:
                continue
            candidates.append(
                (
                    int(record.get("last_seen", 0)),
                    interface,
                    target_ip,
                    record,
                )
            )
    candidates.sort(reverse=True)
    if not candidates:
        return 0

    removed = 0
    state_changed = False
    try:
        with create_portal_session(default_interface, current_ip) as session:
            for _, remembered_interface, target_ip, record in candidates:
                try:
                    fresh_info = query_user_info(session, target_ip)
                except requests.RequestException as error:
                    logger.warning(
                        "Unable to query remembered session %s: %s", target_ip, error
                    )
                    continue

                if fresh_info.get("error") == "not_online_error":
                    state_changed |= forget_session(
                        state, username, remembered_interface, target_ip
                    )
                    logger.info(
                        "Remembered session %s is already offline; removed stale state.",
                        target_ip,
                    )
                    continue

                if not verify_historical_session(fresh_info, username, target_ip):
                    identity = session_identity(fresh_info, target_ip)
                    logger.warning(
                        "Remembered session %s no longer belongs to account %s (fresh account %s); not logging it out.",
                        target_ip,
                        username,
                        (identity or {}).get("username") or "unknown",
                    )
                    state_changed |= forget_session(
                        state, username, remembered_interface, target_ip
                    )
                    continue

                fresh_identity = session_identity(fresh_info, target_ip) or {}
                stored_mac = normalize_mac(record.get("portal_mac"))
                fresh_mac = normalize_mac(fresh_identity.get("portal_mac"))
                if stored_mac and fresh_mac and stored_mac != fresh_mac:
                    warning = (
                        f"历史 IP {target_ip} 的 MAC 已变化："
                        f"{stored_mac} → {fresh_mac}。账户仍匹配，将按历史 IP 下线。"
                    )
                    logger.warning(warning)
                    notify("HITSZ Net 会话提醒", warning)

                if get_default_interface() != default_interface:
                    logger.warning(
                        "Default route changed during session reconciliation; stopping."
                    )
                    break

                logger.info(
                    "Logging out remembered %s session %s for account %s (stored/fresh MAC %s/%s).",
                    remembered_interface,
                    target_ip,
                    username,
                    record.get("portal_mac") or "unknown",
                    fresh_identity.get("portal_mac") or "unknown",
                )
                result = logout_target_session(session, username, target_ip)
                if result.get("error") != "ok":
                    logger.error(
                        "Srun rejected targeted logout for %s: error=%s ecode=%s message=%s",
                        target_ip,
                        result.get("error"),
                        result.get("ecode"),
                        result.get("error_msg") or result.get("message"),
                    )
                    continue

                confirmed_offline = False
                for _ in range(3):
                    time.sleep(1)
                    post_logout_info = query_user_info(session, target_ip)
                    if (
                        post_logout_info.get("error") == "not_online_error"
                        and post_logout_info.get("online_ip") != target_ip
                    ):
                        confirmed_offline = True
                        break

                if not confirmed_offline:
                    logger.error(
                        "Srun accepted logout for %s, but the session is still online.",
                        target_ip,
                    )
                    continue

                forget_session(state, username, remembered_interface, target_ip)
                state_changed = True
                removed += 1
                logger.info("Confirmed remembered session %s is offline.", target_ip)
    except (OSError, requests.RequestException, ValueError) as error:
        logger.warning("Unable to reconcile remembered sessions: %s", error)

    if state_changed:
        try:
            save_session_state(state, state_path)
        except OSError as error:
            logger.error("Unable to persist reconciled session state: %s", error)
    return removed


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
    """Send a safely escaped system notification on macOS."""
    if sys.platform != "darwin":
        return

    def escape(value):
        return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    try:
        script = (
            f'display notification "{escape(message)[:900]}" '
            f'with title "{escape(title)}"'
        )
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


@dataclass(frozen=True)
class LoginResult:
    success: bool
    detail: str = ""
    capacity_exceeded: bool = False

    def __bool__(self):
        return self.success


def route_description():
    """Return the current default interface, hardware port, and IPv4."""
    interface = get_default_interface() or "unknown"
    port = get_hardware_ports().get(interface, {}).get("hardware_port", "unknown")
    ip = get_interface_ipv4(interface) or "unknown"
    return f"interface={interface} port={port} ip={ip}"


def login_failure_detail(login_info, user_info=None):
    """Build a diagnostic-safe summary of a rejected Srun login."""
    user_info = user_info or {}
    raw_values = []
    for key in ("ecode", "error", "error_msg", "message", "suc_msg", "res"):
        value = login_info.get(key)
        if value not in (None, ""):
            raw_values.append(f"{key}={value}")

    raw_text = " ".join(str(value) for value in login_info.values())
    capacity_exceeded = "E2620" in raw_text.upper() or any(
        phrase in raw_text.lower()
        for phrase in ("online device", "device count", "online number")
    )

    device_total = (
        login_info.get("online_device_total")
        or user_info.get("online_device_total")
        or "unknown"
    )
    devices = login_info.get("data")
    if not isinstance(devices, list):
        devices = parse_online_devices(login_info) or parse_online_devices(user_info)
    device_summaries = []
    for device in devices[:8]:
        device_summaries.append(
            "/".join(
                str(value or "?")
                for value in (
                    device.get("ip"),
                    device.get("user_mac") or device.get("mac"),
                    device.get("os_name") or device.get("class_name"),
                    device.get("add_time"),
                )
            )
        )

    prefix = "设备数已满，Srun 拒绝登录" if capacity_exceeded else "Srun 登录失败"
    parts = [prefix, route_description(), f"online_device_total={device_total}"]
    if raw_values:
        parts.append(" ".join(raw_values))
    if device_summaries:
        parts.append("devices=[" + ", ".join(device_summaries) + "]")
    return LoginResult(False, "; ".join(parts), capacity_exceeded)


def login(username, password):
    """Perform login using the Srun HTTP API and return diagnostic details."""
    if not username or not password:
        logger.error("Username or password not set.")
        notify("HITSZ Net", "Configuration error: Missing credentials")
        return LoginResult(False, "Configuration error: missing credentials")

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
                return LoginResult(True, str(success_message))

            if any(
                login_info.get(key)
                for key in ("ecode", "error", "error_msg", "message")
            ):
                failure = login_failure_detail(login_info, user_info)
                logger.error(failure.detail)
                return failure

            # Ambiguous response — verify via connectivity
            logger.warning("Srun login response ambiguous, checking connectivity...")
            if check_internet():
                logger.info("Login successful (connectivity verified).")
                return LoginResult(True, "Connectivity verified")

            failure = login_failure_detail(
                {
                    "error": "ambiguous_response",
                    "error_msg": "connectivity check failed after portal response",
                },
                user_info,
            )
            logger.error(failure.detail)
            return failure

        except requests.RequestException as e:
            logger.warning(f"Login attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait = 5 * attempt
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                detail = f"Login attempts exhausted: {e}; {route_description()}"
                logger.error(detail)
                return LoginResult(False, detail)
        except Exception as e:
            detail = f"Unexpected login error: {e}; {route_description()}"
            logger.error(detail)
            return LoginResult(False, detail)

    return LoginResult(False, f"Login failed without response; {route_description()}")


def run_monitor_check(username, password):
    """Run one reconciliation, connectivity, and login cycle."""
    reconcile_historical_sessions(username)
    if not check_internet():
        logger.info("Internet unavailable. Initiating login sequence...")
        notify("HITSZ Net", "Network lost. Attempting login...")
        result = login(username, password)
        if result:
            observe_default_session(username)
            notify("HITSZ Net", "Login successful. You are back online.")
            if check_internet():
                logger.info("Connectivity verified.")
            else:
                logger.warning("Login reported success but connectivity check failed.")
        else:
            title = (
                "HITSZ Net：在线设备数已满"
                if result.capacity_exceeded
                else "HITSZ Net：登录失败"
            )
            notify(title, result.detail)
        return result

    logger.info("Connectivity OK — no login needed.")
    if observe_default_session(username):
        reconcile_historical_sessions(username)
    return None


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

    # Main loop
    while True:
        try:
            run_monitor_check(username, password)
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
