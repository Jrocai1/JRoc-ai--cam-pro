"""Regression tests for the CAM PRO local bench foundation."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend_bus.port_listener import discover_devices, records_as_dicts
from backend_bus.model_router import load_model_targets
from config.settings import get_settings
from core_swarm.agent_registry import AgentKey
from core_swarm.orchestrator import dispatch
from dashboard_server import create_session, init_db, list_audit_events, list_sessions, update_session


class DeviceDiscoveryTests(unittest.TestCase):
    def test_mock_inventory_is_explicitly_synthetic(self):
        records = records_as_dicts(discover_devices(mock=True))
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["mock"])
        self.assertEqual(records[0]["mode"], "mock")
        self.assertIn("Synthetic", records[0]["description"])

    def test_real_inventory_does_not_enable_mock_records(self):
        records = records_as_dicts(discover_devices(mock=False))
        self.assertTrue(all(not record["mock"] for record in records))


class ConfigurationAndTriageTests(unittest.TestCase):
    def test_missing_model_config_fails_closed(self):
        targets, remote = load_model_targets("this-path-should-not-exist-cam-pro.json")
        self.assertEqual(targets, [])
        self.assertFalse(remote)

    def test_offline_triage_is_advisory_and_review_required(self):
        result = dispatch("test-task", AgentKey.COMMAND_BRAIN, "Phone has liquid damage and will not power on")
        self.assertEqual(result.worker.model_used, "offline-rule-based")
        self.assertTrue(result.worker.requires_technician_review)
        self.assertIn("Power the device off", result.worker.summary)
        self.assertIn("technician must verify", result.worker.summary)
        self.assertGreaterEqual(result.elapsed_ms, 0)


class BenchSessionTests(unittest.TestCase):
    def test_session_persists_and_does_not_store_serial(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "bench.sqlite3"
            init_db(database)
            session = create_session({
                "customer_reference": "CASE-100",
                "device_make": "Samsung",
                "device_model": "Galaxy S24",
                "notes": "No power; inspect with approved equipment.",
            }, database)
            rows = list_sessions(database)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], session["id"])
            self.assertTrue(rows[0]["session_code"].startswith("CAM-"))
            self.assertNotIn("device_serial", rows[0])
            self.assertNotIn("device_serial_hash", rows[0])

    def test_session_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "bench.sqlite3"
            with self.assertRaisesRegex(ValueError, "Unsupported fields"):
                create_session({"serial_number": "123"}, database)

    def test_session_status_update_persists_and_creates_audit_event(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "bench.sqlite3"
            session = create_session({"device_make": "Samsung", "device_model": "Galaxy S24"}, database)
            updated = update_session(session["id"], {"status": "completed"}, database)
            self.assertEqual(updated["status"], "completed")
            self.assertGreaterEqual(updated["updated_at"], session["updated_at"])
            events = list_audit_events(database)
            self.assertEqual([event["event_type"] for event in events], ["session.status_changed", "session.created"])
            self.assertEqual(events[0]["details"]["from"], "open")
            self.assertEqual(events[0]["details"]["to"], "completed")

    def test_session_status_update_rejects_unapproved_fields_and_statuses(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "bench.sqlite3"
            session = create_session({}, database)
            with self.assertRaisesRegex(ValueError, "only the status"):
                update_session(session["id"], {"status": "completed", "notes": "changed"}, database)
            with self.assertRaisesRegex(ValueError, "status must be"):
                update_session(session["id"], {"status": "flashed"}, database)


if __name__ == "__main__":
    unittest.main()
