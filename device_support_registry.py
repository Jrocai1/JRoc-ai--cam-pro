"""Model-aware device-family registry for J-ROC AI Universal Repair Suite PRO.

This module is a policy/metadata foundation, not a hardware driver. A capability
being listed here does not mean the connected device supports it; runtime adapters
must probe the device and report evidence before enabling an operation.
"""
from dataclasses import dataclass
from enum import Enum


class DeviceFamily(str, Enum):
    SMARTPHONE = "smartphone"
    TABLET = "tablet"
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    WORKSTATION = "workstation"
    MINI_PC = "mini_pc"
    WEARABLE = "wearable"
    PRINTER = "printer"
    CAMERA = "camera"
    NETWORK_DEVICE = "network_device"
    STORAGE_DEVICE = "storage_device"
    OTHER = "other"


class Operation(str, Enum):
    INVENTORY = "inventory"
    READ_ONLY_DIAGNOSTICS = "read_only_diagnostics"
    LOG_COLLECTION = "log_collection"
    OS_RECOVERY_GUIDANCE = "os_recovery_guidance"
    FIRMWARE_INTEGRITY_CHECK = "firmware_integrity_check"
    FIRMWARE_WRITE = "firmware_write"
    FACTORY_RESET = "factory_reset"
    HARDWARE_CONTROL = "hardware_control"


@dataclass(frozen=True)
class CapabilityPolicy:
    """Default safety policy for a device family.

    These are application policy defaults, not proof that a device supports an
    operation. Vendor/model adapters must verify compatibility independently.
    """
    family: DeviceFamily
    default_operations: tuple[Operation, ...]
    requires_explicit_approval: tuple[Operation, ...] = (
        Operation.FIRMWARE_WRITE,
        Operation.FACTORY_RESET,
        Operation.HARDWARE_CONTROL,
    )


_READ_ONLY = (
    Operation.INVENTORY,
    Operation.READ_ONLY_DIAGNOSTICS,
    Operation.LOG_COLLECTION,
    Operation.OS_RECOVERY_GUIDANCE,
    Operation.FIRMWARE_INTEGRITY_CHECK,
)

_POLICIES = {
    family: CapabilityPolicy(family=family, default_operations=_READ_ONLY)
    for family in DeviceFamily
}


def get_policy(family: DeviceFamily) -> CapabilityPolicy:
    """Return conservative default policy for a device family."""
    return _POLICIES[family]


def requires_approval(operation: Operation) -> bool:
    """Fail-safe approval rule for destructive or device-changing operations."""
    return operation in {
        Operation.FIRMWARE_WRITE,
        Operation.FACTORY_RESET,
        Operation.HARDWARE_CONTROL,
    }


def can_run_without_probe(operation: Operation) -> bool:
    """Only non-destructive informational operations may run before probing.

    This is not authorization to access a device. Runtime permission checks and
    model-specific capability checks are still mandatory.
    """
    return operation in {
        Operation.INVENTORY,
        Operation.READ_ONLY_DIAGNOSTICS,
        Operation.LOG_COLLECTION,
        Operation.OS_RECOVERY_GUIDANCE,
        Operation.FIRMWARE_INTEGRITY_CHECK,
    }
