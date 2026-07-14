#!/usr/bin/env python3
"""Behavioral tests for safe Wi-Fi-to-wired Srun session handoff."""

import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

MODULE_PATH = pathlib.Path(__file__).parent / "hitsz_net" / "hitsz_net.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("hitsz_net_daemon", MODULE_PATH)
hitsz_net = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hitsz_net)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class HandoffTests(unittest.TestCase):
    def test_logout_request_targets_one_ip_with_current_portal_contract(self):
        session = MagicMock()
        session.get.return_value = FakeResponse(
            'callback({"error":"ok","res":"logout_ok"})'
        )

        with patch.object(hitsz_net.time, "time", return_value=1_700_000_000):
            result = hitsz_net.logout_wifi_session(session, "student", "10.250.1.23")

        self.assertEqual(result["error"], "ok")
        _, kwargs = session.get.call_args
        params = kwargs["params"]
        self.assertEqual(params["user_ip"], "10.250.1.23")
        self.assertNotIn("ip", params)
        self.assertEqual(params["unbind"], "1")
        self.assertEqual(
            params["sign"],
            hitsz_net.srun_sha1("1700000000student10.250.1.2311700000000"),
        )

    def test_session_identity_requires_exact_ip_and_matching_mac(self):
        info = {
            "error": "ok",
            "online_ip": "10.250.1.23",
            "user_name": "student",
            "online_device_detail": (
                '{"1":{"ip":"10.250.1.23","user_mac":"aa:bb:cc:dd:ee:ff"}}'
            ),
        }

        self.assertTrue(
            hitsz_net.find_verified_wifi_session(
                info, "student", "10.250.1.23", "AA-BB-CC-DD-EE-FF"
            )
        )
        self.assertFalse(
            hitsz_net.find_verified_wifi_session(
                info, "student", "10.250.1.23", "00:11:22:33:44:55"
            )
        )
        self.assertFalse(
            hitsz_net.find_verified_wifi_session(
                info, "another-user", "10.250.1.23", "aa:bb:cc:dd:ee:ff"
            )
        )

    @patch.object(hitsz_net.time, "sleep")
    @patch.object(hitsz_net, "logout_wifi_session", return_value={"error": "ok"})
    @patch.object(hitsz_net, "query_user_info")
    @patch.object(hitsz_net, "create_portal_session")
    @patch.object(hitsz_net, "get_interface_ipv4")
    @patch.object(hitsz_net, "get_hardware_ports")
    @patch.object(hitsz_net, "get_default_interface")
    def test_handoff_only_succeeds_after_post_logout_offline_check(
        self,
        default_interface,
        hardware_ports,
        interface_ipv4,
        create_session,
        query_user_info,
        logout_session,
        sleep,
    ):
        default_interface.side_effect = ["en7", "en7"]
        hardware_ports.return_value = {
            "en0": {
                "hardware_port": "Wi-Fi",
                "ethernet_address": "aa:bb:cc:dd:ee:ff",
            },
            "en7": {"hardware_port": "USB 10/100/1000 LAN"},
        }
        interface_ipv4.side_effect = lambda interface: {
            "en0": "10.250.1.23",
            "en7": "10.250.2.34",
        }[interface]
        create_session.return_value.__enter__.return_value = MagicMock()
        query_user_info.side_effect = [
            {
                "error": "ok",
                "online_ip": "10.250.1.23",
                "user_name": "student",
            },
            {"error": "not_online_error", "client_ip": "10.250.1.23"},
        ]

        self.assertTrue(hitsz_net.handle_wired_handoff("student"))
        logout_session.assert_called_once()
        self.assertEqual(query_user_info.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch.object(hitsz_net, "logout_wifi_session")
    @patch.object(hitsz_net, "query_user_info")
    @patch.object(hitsz_net, "create_portal_session")
    @patch.object(hitsz_net, "get_interface_ipv4")
    @patch.object(hitsz_net, "get_hardware_ports")
    @patch.object(hitsz_net, "get_default_interface", return_value="en7")
    def test_not_online_precheck_never_calls_logout(
        self,
        default_interface,
        hardware_ports,
        interface_ipv4,
        create_session,
        query_user_info,
        logout_session,
    ):
        hardware_ports.return_value = {
            "en0": {"hardware_port": "Wi-Fi"},
            "en7": {"hardware_port": "USB LAN"},
        }
        interface_ipv4.side_effect = lambda interface: {
            "en0": "10.250.1.23",
            "en7": "10.250.2.34",
        }[interface]
        create_session.return_value.__enter__.return_value = MagicMock()
        query_user_info.return_value = {
            "error": "not_online_error",
            "client_ip": "10.250.1.23",
        }

        self.assertFalse(hitsz_net.handle_wired_handoff("student"))
        logout_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
