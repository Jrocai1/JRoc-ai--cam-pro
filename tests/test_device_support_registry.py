import unittest

from device_support_registry import (
    DeviceFamily,
    Operation,
    can_run_without_probe,
    get_policy,
    requires_approval,
)


class DeviceSupportRegistryTests(unittest.TestCase):
    def test_all_device_families_have_conservative_policy(self):
        for family in DeviceFamily:
            with self.subTest(family=family):
                policy = get_policy(family)
                self.assertEqual(policy.family, family)
                self.assertIn(Operation.READ_ONLY_DIAGNOSTICS, policy.default_operations)
                self.assertNotIn(Operation.FIRMWARE_WRITE, policy.default_operations)

    def test_destructive_operations_require_approval(self):
        for operation in (
            Operation.FIRMWARE_WRITE,
            Operation.FACTORY_RESET,
            Operation.HARDWARE_CONTROL,
        ):
            with self.subTest(operation=operation):
                self.assertTrue(requires_approval(operation))
                self.assertFalse(can_run_without_probe(operation))

    def test_read_only_operations_are_allowed_by_default_policy(self):
        for operation in (
            Operation.INVENTORY,
            Operation.READ_ONLY_DIAGNOSTICS,
            Operation.LOG_COLLECTION,
            Operation.OS_RECOVERY_GUIDANCE,
            Operation.FIRMWARE_INTEGRITY_CHECK,
        ):
            with self.subTest(operation=operation):
                self.assertTrue(can_run_without_probe(operation))
                self.assertFalse(requires_approval(operation))


if __name__ == "__main__":
    unittest.main()
