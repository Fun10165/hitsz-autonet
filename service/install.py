#!/usr/bin/env python3
"""
Service installer for HITSZ Network Auto Login.
Handles LaunchAgent creation and registration on macOS.
"""

import os
import sys
import plistlib
import argparse
import subprocess
from pathlib import Path

# Constants
LABEL = "com.github.hitsz.autonet"
PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>--daemon</string>
        <string>--config</string>
        <string>{config_path}</string>
{extra_args}
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>StartInterval</key>
    <integer>{interval}</integer>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
        <key>NetworkState</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>HOME</key>
        <string>{home}</string>
    </dict>
    
    <key>WorkingDirectory</key>
    <string>{work_dir}</string>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
"""


class ServiceInstaller:
    def __init__(self, script_path, config_path, interval=60, extra_args=None):
        self.script_path = Path(script_path).resolve()
        self.config_path = Path(config_path).resolve()
        self.interval = interval
        self.extra_args = extra_args or []
        self.home = Path.home()
        self.log_dir = self.home / "Library" / "Logs" / "hitsz-autonet"
        self.plist_path = self.home / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    def install(self):
        print(f"Installing service: {LABEL}")

        # 1. Verify paths
        if not self.script_path.exists():
            print(f"Error: Script not found at {self.script_path}")
            return False

        if not self.config_path.exists():
            print(f"Warning: Config file not found at {self.config_path}")
            print("Please create it before the service runs.")

        # 2. Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"Log directory created: {self.log_dir}")

        # 3. Generate Plist
        extra = "".join(f"        <string>{a}</string>\n" for a in self.extra_args)
        plist_content = PLIST_TEMPLATE.format(
            label=LABEL,
            python_path=sys.executable,
            script_path=self.script_path,
            config_path=self.config_path,
            interval=self.interval,
            log_out=self.log_dir / "service.log",
            log_err=self.log_dir / "error.log",
            home=self.home,
            work_dir=self.script_path.parent,
            extra_args=extra,
        )

        # 4. Write Plist
        self.plist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plist_path, "w") as f:
            f.write(plist_content)
        print(f"Plist written to: {self.plist_path}")

        # 5. Load Service
        self.unload()  # Ensure clean state
        try:
            subprocess.run(
                ["launchctl", "load", "-w", str(self.plist_path)], check=True
            )
            print("Service loaded successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to load service: {e}")
            return False

    def uninstall(self):
        print(f"Uninstalling service: {LABEL}")
        self.unload()
        if self.plist_path.exists():
            self.plist_path.unlink()
            print("Plist file removed.")
        else:
            print("Plist file not found.")

    def unload(self):
        if self.plist_path.exists():
            try:
                subprocess.run(
                    ["launchctl", "unload", str(self.plist_path)],
                    check=False,
                    capture_output=True,
                )
                print("Service unloaded.")
            except Exception:
                pass

    def status(self):
        try:
            result = subprocess.run(
                ["launchctl", "list", LABEL], capture_output=True, text=True
            )
            if result.returncode != 0:
                print("Service is not running.")
                return

            import re

            pid_match = re.search(r'"PID"\s*=\s*(\d+)', result.stdout)
            exit_match = re.search(r'"LastExitStatus"\s*=\s*(\d+)', result.stdout)
            pid = pid_match.group(1) if pid_match else "unknown"
            exit_code = exit_match.group(1) if exit_match else "unknown"

            if pid != "unknown":
                print(f"Service is running.  PID: {pid}  Last exit: {exit_code}")
            else:
                print("Service is loaded but not currently running.")
            print(f"Logs: {self.log_dir}")
        except Exception as e:
            print(f"Error checking status: {e}")


def main():
    parser = argparse.ArgumentParser(description="Install HITSZ AutoNet Service")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Install command
    install_parser = subparsers.add_parser(
        "install", help="Install and start the service"
    )
    install_parser.add_argument(
        "--config", "-c", required=True, help="Path to .env config file"
    )
    install_parser.add_argument(
        "--script",
        "-s",
        default="./hitsz_net/hitsz_net.py",
        help="Path to hitsz_net.py",
    )
    install_parser.add_argument(
        "--wake",
        action="store_true",
        help="Trigger check on lid-open / wake from sleep",
    )
    install_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)",
    )

    # Uninstall command
    subparsers.add_parser("uninstall", help="Stop and remove the service")

    # Status command
    subparsers.add_parser("status", help="Check service status")

    args = parser.parse_args()
    script_path = getattr(args, "script", "./hitsz_net/hitsz_net.py")
    config_path = getattr(args, "config", ".env")

    extra_args = []
    if getattr(args, "wake", False):
        extra_args.append("--wake")
    if getattr(args, "interval", 60) != 60:
        extra_args.extend(["--interval", str(args.interval)])

    script_path = args.script if hasattr(args, "script") else "./hitsz_net/hitsz_net.py"
    config_path = args.config if hasattr(args, "config") else ""

    installer = ServiceInstaller(
        script_path,
        config_path,
        interval=getattr(args, "interval", 60),
        extra_args=extra_args,
    )

    if args.command == "install":
        installer.install()
    elif args.command == "uninstall":
        installer.uninstall()
    elif args.command == "status":
        installer.status()


if __name__ == "__main__":
    main()
