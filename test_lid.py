#!/usr/bin/env python3
"""Test lid-open detection: close and open your MacBook lid to see events."""

import subprocess
import time


def poll_lid():
    """Return True if lid is currently closed."""
    try:
        r = subprocess.run(
            ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return '"AppleClamshellState" = Yes' in r.stdout
    except Exception:
        return None


def main():
    print("Watching lid state — close and open your MacBook lid now.")
    print("Press Ctrl+C to stop.\n")

    was_closed = poll_lid()
    if was_closed is None:
        print("ERROR: Cannot query lid state. Is this macOS?")
        return

    closed_label = "CLOSED" if was_closed else "OPEN"
    t0 = time.strftime("%H:%M:%S")
    print(f"[{t0}] Initial state: lid is {closed_label}")

    while True:
        time.sleep(2)
        now_closed = poll_lid()
        if now_closed is None:
            continue

        if was_closed and not now_closed:
            t = time.strftime("%H:%M:%S")
            print(f"[{t}] >>> LID OPENED — wake trigger would fire!")
        elif not was_closed and now_closed:
            t = time.strftime("%H:%M:%S")
            print(f"[{t}] Lid closed.")

        was_closed = now_closed


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
