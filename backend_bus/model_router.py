"""Model-target configuration loader for CAM PRO's local-first advisory router."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_model_targets(path: str) -> tuple[list[dict[str, Any]], bool]:
    """Return validated target mappings and whether any target requests remote use.

    Remote endpoints remain disabled unless both configuration and runtime settings
    explicitly allow them. The orchestrator performs the final endpoint validation.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], False
    if not isinstance(payload, dict):
        return [], False
    raw_targets = payload.get("targets", [])
    if not isinstance(raw_targets, list):
        return [], False
    targets = [target for target in raw_targets if isinstance(target, dict)]
    remote_requested = any(target.get("allow_remote") is True for target in targets)
    return targets, remote_requested
