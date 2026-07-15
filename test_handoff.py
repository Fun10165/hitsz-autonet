#!/usr/bin/env python3
"""Behavioral tests for stateful HITSZ session reconciliation."""

import importlib.util
import pathlib
import stat
import sys
import tempfile
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


class StatefulHandoffTests(unittest.TestCase):
    def test_targeted_query_and_logout_use_historical_ip(self):
        session = MagicMock()
        session.get.side_effect = [
            FakeResponse('callback({"error":"ok","online_ip":"10.250.1.23"})'),
            FakeResponse('callback({"error":"ok","res":"logout_ok"})'),
        ]

        hitsz_net.query_user_info(session, "10.250.1.23")
        with patch.object(hitsz_net.time, "time", return_value=1_700_000_000):
            result = hitsz_net.logout_target_session(session, "student", "10.250.1.23")

        self.assertEqual(result["error"], "ok")
        query_params = session.get.call_args_list[0].kwargs["params"]
        logout_params = session.get.call_args_list[1].kwargs["params"]
        self.assertEqual(query_params["ip"], "10.250.1.23")
        self.assertEqual(logout_params["user_ip"], "10.250.1.23")
        self.assertEqual(logout_params["unbind"], "1")
        self.assertEqual(
            logout_params["sign"],
            hitsz_net.srun_sha1("1700000000student10.250.1.2311700000000"),
        )

    def test_state_round_trip_is_owner_only(self):
        state = hitsz_net.empty_session_state()
        state["accounts"]["student"] = {"interfaces": {}}
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "session-state.json"
            hitsz_net.save_session_state(state, path)
            loaded = hitsz_net.load_session_state(path)

            self.assertEqual(loaded, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    @patch.object(hitsz_net, "get_interface_mac", return_value="aa:bb:cc:dd:ee:ff")
    def test_remember_session_keeps_ip_and_mac_as_supplement(self, interface_mac):
        state = hitsz_net.empty_session_state()
        info = {
            "error": "ok",
            "online_ip": "10.250.1.23",
            "user_name": "student",
            "user_mac": "02:11:22:33:44:55",
        }

        changed = hitsz_net.remember_session(
            state,
            "student",
            "en0",
            {"hardware_port": "Wi-Fi"},
            "10.250.1.23",
            info,
            observed_at=100,
        )

        record = state["accounts"]["student"]["interfaces"]["en0"]["sessions"][
            "10.250.1.23"
        ]
        self.assertTrue(changed)
        self.assertEqual(record["portal_mac"], "021122334455")
        self.assertTrue(
            hitsz_net.verify_historical_session(
                {
                    "error": "ok",
                    "online_ip": "10.250.1.23",
                    "user_name": "student",
                    "user_mac": "02:aa:bb:cc:dd:ee",
                },
                "student",
                "10.250.1.23",
            )
        )

    @patch.object(hitsz_net.time, "sleep")
    @patch.object(hitsz_net, "notify")
    @patch.object(hitsz_net, "logout_target_session", return_value={"error": "ok"})
    @patch.object(hitsz_net, "query_user_info")
    @patch.object(hitsz_net, "create_portal_session")
    @patch.object(hitsz_net, "get_interface_ipv4", return_value="10.250.2.34")
    @patch.object(
        hitsz_net,
        "get_hardware_ports",
        return_value={"en7": {"hardware_port": "USB 10/100/1000 LAN"}},
    )
    @patch.object(hitsz_net, "get_default_interface")
    def test_mac_change_notifies_but_does_not_block_account_logout(
        self,
        default_interface,
        hardware_ports,
        interface_ipv4,
        create_session,
        query_user_info,
        logout_session,
        notify,
        sleep,
    ):
        default_interface.side_effect = ["en7", "en7"]
        create_session.return_value.__enter__.return_value = MagicMock()
        query_user_info.side_effect = [
            {
                "error": "ok",
                "online_ip": "10.250.1.23",
                "user_name": "student",
                "user_mac": "02:aa:bb:cc:dd:ee",
            },
            {"error": "not_online_error", "client_ip": "10.250.2.34"},
        ]
        state = hitsz_net.empty_session_state()
        state["accounts"]["student"] = {
            "interfaces": {
                "en0": {
                    "hardware_port": "Wi-Fi",
                    "hardware_mac": "aabbccddeeff",
                    "sessions": {
                        "10.250.1.23": {
                            "first_seen": 10,
                            "last_seen": 20,
                            "portal_mac": "021122334455",
                            "rad_online_id": "",
                        }
                    },
                }
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "session-state.json"
            hitsz_net.save_session_state(state, path)
            removed = hitsz_net.reconcile_historical_sessions("student", path)
            updated = hitsz_net.load_session_state(path)

        self.assertEqual(removed, 1)
        logout_session.assert_called_once()
        notify.assert_called_once()
        self.assertNotIn(
            "10.250.1.23",
            updated["accounts"]["student"]["interfaces"]["en0"]["sessions"],
        )
        sleep.assert_called_once_with(1)

    @patch.object(hitsz_net, "logout_target_session")
    @patch.object(hitsz_net, "query_user_info")
    @patch.object(hitsz_net, "create_portal_session")
    @patch.object(hitsz_net, "get_interface_ipv4", return_value="10.250.2.34")
    @patch.object(
        hitsz_net,
        "get_hardware_ports",
        return_value={"en7": {"hardware_port": "USB LAN"}},
    )
    @patch.object(hitsz_net, "get_default_interface", return_value="en7")
    def test_other_account_is_not_logged_out(
        self,
        default_interface,
        hardware_ports,
        interface_ipv4,
        create_session,
        query_user_info,
        logout_session,
    ):
        create_session.return_value.__enter__.return_value = MagicMock()
        query_user_info.return_value = {
            "error": "ok",
            "online_ip": "10.250.1.23",
            "user_name": "someone-else",
            "user_mac": "02:11:22:33:44:55",
        }
        state = hitsz_net.empty_session_state()
        state["accounts"]["student"] = {
            "interfaces": {
                "en0": {
                    "sessions": {
                        "10.250.1.23": {
                            "last_seen": 20,
                            "portal_mac": "021122334455",
                        }
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "session-state.json"
            hitsz_net.save_session_state(state, path)
            self.assertEqual(
                hitsz_net.reconcile_historical_sessions("student", path), 0
            )

        logout_session.assert_not_called()

    @patch.object(
        hitsz_net,
        "route_description",
        return_value="interface=en7 port=USB LAN ip=10.250.2.34",
    )
    @patch.object(hitsz_net, "create_default_route_session")
    def test_login_returns_capacity_result_from_portal_response(
        self, create_session, route
    ):
        session = create_session.return_value
        session.get.side_effect = [
            FakeResponse(
                'callback({"error":"not_online_error",'
                '"online_ip":"10.250.2.34","online_device_total":5})'
            ),
            FakeResponse('callback({"challenge":"token"})'),
            FakeResponse(
                'callback({"ecode":"E2620","error":"login_error",'
                '"error_msg":"online device count reached limit",'
                '"online_device_total":5})'
            ),
        ]

        result = hitsz_net.login("student", "password")

        self.assertIsInstance(result, hitsz_net.LoginResult)
        self.assertFalse(result)
        self.assertTrue(result.capacity_exceeded)
        self.assertIn("E2620", result.detail)
        self.assertIn("interface=en7", result.detail)
        self.assertEqual(session.get.call_count, 3)

    @patch.object(hitsz_net, "login")
    @patch.object(hitsz_net, "observe_default_session", return_value=True)
    @patch.object(hitsz_net, "check_internet", return_value=True)
    @patch.object(hitsz_net, "reconcile_historical_sessions")
    def test_online_monitor_reconciles_again_after_observation(
        self, reconcile, check_internet, observe, login
    ):
        result = hitsz_net.run_monitor_check("student", "password")

        self.assertIsNone(result)
        self.assertEqual(reconcile.call_count, 2)
        reconcile.assert_any_call("student")
        observe.assert_called_once_with("student")
        login.assert_not_called()

    @patch.object(hitsz_net, "notify")
    @patch.object(
        hitsz_net,
        "login",
        return_value=hitsz_net.LoginResult(False, "ecode=E2620; interface=en7", True),
    )
    @patch.object(hitsz_net, "check_internet", return_value=False)
    @patch.object(hitsz_net, "reconcile_historical_sessions")
    def test_capacity_result_is_forwarded_to_notification(
        self, reconcile, check_internet, login, notify
    ):
        result = hitsz_net.run_monitor_check("student", "password")

        self.assertTrue(result.capacity_exceeded)
        notify.assert_called_with(
            "HITSZ Net：在线设备数已满", "ecode=E2620; interface=en7"
        )

    @patch.object(
        hitsz_net,
        "route_description",
        return_value="interface=en7 port=USB LAN ip=10.250.2.34",
    )
    def test_capacity_failure_contains_debug_context(self, route):
        result = hitsz_net.login_failure_detail(
            {
                "ecode": "E2620",
                "error": "login_error",
                "error_msg": "online device count reached limit",
                "data": [
                    {
                        "ip": "10.250.1.23",
                        "user_mac": "02:11:22:33:44:55",
                        "os_name": "Mac OS",
                        "add_time": "123",
                    }
                ],
            },
            {"online_device_total": 5},
        )

        self.assertFalse(result)
        self.assertTrue(result.capacity_exceeded)
        self.assertIn("E2620", result.detail)
        self.assertIn("interface=en7", result.detail)
        self.assertIn("online_device_total=5", result.detail)
        self.assertIn("10.250.1.23", result.detail)


if __name__ == "__main__":
    unittest.main()
