"""Fail-safe advisory triage with optional local Ollama inference.

The orchestrator never executes a device command. Model output is untrusted advice
and always requires technician review.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .agent_registry import AgentKey


@dataclass(frozen=True, slots=True)
class WorkerResult:
    role: AgentKey
    summary: str
    model_used: str
    attempts: tuple[str, ...]
    requires_technician_review: bool = True


@dataclass(frozen=True, slots=True)
class DispatchResult:
    worker: WorkerResult
    elapsed_ms: float
    fallback_used: bool


def _safe_local_url(value: str, allow_remote: bool) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "http" or not parsed.hostname:
        return False
    if allow_remote:
        return True
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _offline_advice(task: str) -> str:
    lowered = task.lower()
    actions = []
    if any(term in lowered for term in ("water", "liquid", "wet", "corrosion")):
        actions.append("Power the device off and do not apply charging power until liquid exposure is assessed.")
    if any(term in lowered for term in ("battery", "swollen", "puffed", "heat", "hot")):
        actions.append("If the battery is swollen, hot, punctured, or venting, isolate the device and follow the shop battery-safety procedure.")
    if any(term in lowered for term in ("no power", "won't turn on", "dead", "boot")):
        actions.append("Record current draw with approved equipment and verify the known-good charger, cable, and connector before component-level work.")
    if any(term in lowered for term in ("firmware", "flash", "edl", "brom", "unlock", "erase")):
        actions.append("Do not run a state-changing operation from this triage result; verify exact model, authorization, firmware provenance, and a recovery plan first.")
    if not actions:
        actions.append("Capture symptoms, exact model, recent events, visual condition, and non-invasive test results before selecting the next diagnostic step.")
    actions.append("This is rule-based guidance, not a confirmed diagnosis. A qualified technician must verify each step.")
    return " ".join(actions)


def _ollama_chat(base_url: str, model: str, task: str, timeout: float) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": "You are a cautious electronics repair triage assistant. Give non-destructive diagnostic guidance only. Never claim certainty, never instruct bypassing locks or unauthorized access, and require technician verification. Do not issue commands to connected devices."},
            {"role": "user", "content": task},
        ],
    }
    url = base_url.rstrip("/") + "/api/chat"
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data: Any = json.loads(response.read(1_000_000).decode("utf-8"))
    message = data.get("message", {}) if isinstance(data, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Local model returned an empty response.")
    return content.strip()[:12000]


def dispatch(task_id: str, role: AgentKey, task: str, *, targets: list[dict] | None = None,
             allow_remote: bool = False) -> DispatchResult:
    started = time.perf_counter()
    attempts: list[str] = []
    for target in targets or []:
        if not isinstance(target, dict) or not target.get("enabled", False):
            continue
        name = str(target.get("name") or target.get("model") or "configured-model")[:80]
        base_url = str(target.get("base_url") or "")
        model = str(target.get("model") or "")
        try:
            timeout = min(max(float(target.get("timeout_seconds", 5)), 0.5), 20.0)
        except (TypeError, ValueError):
            timeout = 5.0
        if not model or not _safe_local_url(base_url, allow_remote and bool(target.get("allow_remote", False))):
            attempts.append(f"{name}: skipped (target not approved)")
            continue
        try:
            summary = _ollama_chat(base_url, model, task, timeout)
            attempts.append(f"{name}: success")
            worker = WorkerResult(role, summary, model, tuple(attempts))
            return DispatchResult(worker, (time.perf_counter() - started) * 1000, False)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            attempts.append(f"{name}: unavailable ({type(exc).__name__})")
    summary = _offline_advice(task)
    worker = WorkerResult(role, summary, "offline-rule-based", tuple(attempts or ["No enabled model target"]), True)
    return DispatchResult(worker, (time.perf_counter() - started) * 1000, bool(attempts))


def load_model_targets(path: str) -> tuple[list[dict], bool]:
    """Load model targets from JSON; malformed or missing config fails closed."""
    from pathlib import Path
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], False
    if not isinstance(payload, dict) or not isinstance(payload.get("targets", []), list):
        return [], False
    targets = [item for item in payload["targets"] if isinstance(item, dict)]
    remote_configured = any(bool(item.get("allow_remote", False)) for item in targets)
    return targets, remote_configured
