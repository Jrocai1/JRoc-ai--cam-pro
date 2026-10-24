import tempfile
import unittest
from pathlib import Path

from jroc_mobile.core import RepairDatabase
from jroc_mobile.device_tools import inspect_firmware, sha256_file


class MobileRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = RepairDatabase(Path(self.temp_dir.name) / "shop.sqlite3")

    def create_test_job(self):
        customer_id = self.db.add_customer("Test Customer", phone="555-0100")
        device_id = self.db.add_device(customer_id, "Galaxy S24", "Phone", "Samsung",
                                       serial_number="TEST-SERIAL", reported_issue="Won't charge")
        job_id = self.db.create_job(customer_id, device_id, "Won't charge", "No liquid damage")
        return customer_id, device_id, job_id

    def test_customer_device_and_repair_job_lifecycle(self):
        customer_id, device_id, job_id = self.create_test_job()
        job = self.db.list_jobs()[0]
        self.assertEqual(job["customer_id"], customer_id)
        self.assertEqual(job["device_id"], device_id)
        self.assertTrue(job["job_number"].startswith("JRM-"))
        self.assertEqual(job["status"], "New")
        self.db.update_job_status(job_id, "Diagnosing")
        self.db.add_diagnostic(job_id, "Power", "No current draw on known-good charger", "Inspect port")
        self.db.add_repair_log(job_id, "Cleaned port and retested", 15)
        self.assertEqual(self.db.list_jobs()[0]["status"], "Diagnosing")
        self.assertEqual(len(self.db.list_diagnostics(job_id)), 1)
        self.assertEqual(len(self.db.list_repair_logs(job_id)), 1)

    def test_estimate_approval_invoice_payment(self):
        _, _, job_id = self.create_test_job()
        estimate_id = self.db.create_estimate(job_id, [
            {"description": "Charging port", "quantity": 1, "unit_price": 80},
            {"description": "Labor", "quantity": 1, "unit_price": 40},
        ], tax_rate=5)
        estimate = self.db.list_estimates()[0]
        self.assertEqual(estimate["total"], 126.0)
        with self.assertRaises(ValueError):
            self.db.create_invoice(job_id)
        self.db.set_estimate_status(estimate_id, "Approved")
        invoice_id = self.db.create_invoice(job_id)
        self.db.record_payment(invoice_id, 50, "Card", "test-reference")
        invoice = self.db.list_invoices()[0]
        self.assertEqual(invoice["status"], "Partially Paid")
        self.db.record_payment(invoice_id, 76, "Cash")
        self.assertEqual(self.db.list_invoices()[0]["status"], "Paid")

    def test_inventory_adjustment_consumption_and_low_stock(self):
        _, _, job_id = self.create_test_job()
        part_id = self.db.add_part("PORT-GS24", "Galaxy S24 charge port",
                                   quantity=4, min_quantity=1, unit_cost=12.5, retail_price=25)
        self.db.consume_part(job_id, part_id, 2)
        self.assertEqual(self.db.list_parts()[0]["quantity"], 2)
        self.db.adjust_inventory(part_id, -1, "Damaged stock")
        self.assertEqual(self.db.list_parts(low_stock_only=True)[0]["quantity"], 1)
        self.assertEqual(len(self.db.inventory_history(part_id)), 3)
        with self.assertRaises(ValueError):
            self.db.consume_part(job_id, part_id, 10)

    def test_qc_audit_settings_backup_and_integrity(self):
        _, _, job_id = self.create_test_job()
        self.db.add_qc_check(job_id, "Charging", True, "Stable charging verified")
        self.assertTrue(self.db.list_qc_checks(job_id)[0]["passed"])
        self.db.set_setting("shop_name", "J-Roc AI Mobile Repair Lab")
        self.assertEqual(self.db.get_setting("shop_name"), "J-Roc AI Mobile Repair Lab")
        self.assertGreater(len(self.db.list_audit()), 0)
        self.assertEqual(self.db.integrity_check(), "ok")
        backup = Path(self.temp_dir.name) / "backup.sqlite3"
        self.db.backup_database(backup)
        self.assertTrue(backup.is_file())
        self.assertGreater(backup.stat().st_size, 0)

    def test_bad_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.db.add_customer(" ")
        customer_id = self.db.add_customer("Owner")
        other_customer_id = self.db.add_customer("Other")
        device_id = self.db.add_device(customer_id, "iPhone 14", manufacturer="Apple")
        with self.assertRaises(ValueError):
            self.db.create_job(other_customer_id, device_id, "Screen broken")

    def test_warranty_case_and_notification_drafts(self):
        _, _, job_id = self.create_test_job()
        warranty_id = self.db.create_warranty_case(job_id, "90-day charging port warranty", "2027-01-01")
        self.assertEqual(self.db.list_warranty_cases()[0]["status"], "Open")
        self.db.update_warranty_status(warranty_id, "Closed")
        self.assertEqual(self.db.list_warranty_cases()[0]["status"], "Closed")
        self.db.queue_notification(job_id, "SMS", "555-0100", "Repair ready for pickup.")
        notice = self.db.list_notifications()[0]
        self.assertEqual(notice["status"], "Draft")
        self.assertEqual(notice["job_number"], self.db.list_jobs()[0]["job_number"])

    def test_rejects_unsupported_brands_and_device_types(self):
        customer_id = self.db.add_customer("Scope Test")
        with self.assertRaises(ValueError):
            self.db.add_device(customer_id, "Pixel 9", "Phone", "Google")
        with self.assertRaises(ValueError):
            self.db.add_device(customer_id, "Gaming console", "Console", "Samsung")
        with self.assertRaises(ValueError):
            self.db.add_device(customer_id, "Generic Notebook", "Laptop", "Other")

    def test_sha256_and_safe_firmware_inspection(self):
        sample = Path(self.temp_dir.name) / "sample.bin"
        sample.write_bytes(b"jroc-mobile-test")
        self.assertEqual(len(sha256_file(sample)), 64)
        result = inspect_firmware(sample)
        self.assertFalse(result["authenticity_verified"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
