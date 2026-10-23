"""Environment-backed local dashboard settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    model_config_path: Path
    allow_remote_models: bool


def get_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    config_path = Path(os.environ.get("JROC_CAM_MODEL_CONFIG", root / "config" / "model_endpoints.json"))
    allow_remote = os.environ.get("JROC_CAM_ALLOW_REMOTE_MODELS", "false").strip().lower() in {"1", "true", "yes"}
    return Settings(model_config_path=config_path, allow_remote_models=allow_remote)
