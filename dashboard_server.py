"""Local-only dashboard/API for J-ROC AI CAM Repair Pro.

Uses only Python's standard library. Binds to loopback by default and never
performs device-changing operations. Bench sessions are stored in SQLite.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import logging
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

from backend_bus.port_listener import discover_devices, records_as_dicts
from backend_bus.model_router import load_model_targets
from device_tools import collect_diagnostics
from config.settings import get_settings
from core_swarm.agent_registry import AgentKey
from core_swarm.orchestrator import dispatch

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "dashboard_ui"
DB_PATH = Path(os.environ.get("JROC_CAM_DB", ROOT / "data" / "bench_sessions.sqlite3"))
LOGGER = logging.getLogger("jroc_cam.dashboard")
DB_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(path: Path = DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS bench_sessions (
                id TEXT PRIMARY KEY,
                session_code TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL CHECK(status IN ('open','paused','completed','cancelled')),
                customer_reference TEXT,
                device_make TEXT,
                device_model TEXT,
                device_serial_hash TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_status_created ON bench_sessions(status, created_at DESC)")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                entity_id TEXT,
                detail_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC)")


def list_sessions(path: Path = DB_PATH) -> list[dict]:
    init_db(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT id, session_code, status, customer_reference,
            device_make, device_model, notes, created_at, updated_at
            FROM bench_sessions ORDER BY created_at DESC LIMIT 100""").fetchall()
    return [dict(row) for row in rows]


def record_audit(event_type: str, entity_id: str | None, detail: dict, path: Path = DB_PATH) -> None:
    init_db(path)
    with closing(sqlite3.connect(path)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO audit_events (id, event_type, entity_id, detail_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), event_type, entity_id, json.dumps(detail, ensure_ascii=False), utc_now()),
            )


def list_audit_events(path: Path = DB_PATH, limit: int = 100) -> list[dict]:
    init_db(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, event_type, entity_id, detail_json, created_at FROM audit_events ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        try:
            item["details"] = json.loads(item.pop("detail_json"))
        except json.JSONDecodeError:
            item["details"] = {}
        output.append(item)
    return output


def update_session(session_id: str, payload: dict, path: Path = DB_PATH) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"status"}:
        raise ValueError("Session updates accept only the status field.")
    status = payload.get("status")
    allowed_statuses = {"open", "paused", "completed", "cancelled"}
    if not isinstance(status, str) or status not in allowed_statuses:
        raise ValueError("status must be open, paused, completed, or cancelled.")
    init_db(path)
    now = utc_now()
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            row = conn.execute("SELECT * FROM bench_sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise LookupError("Bench session not found.")
            previous = row["status"]
            conn.execute("UPDATE bench_sessions SET status = ?, updated_at = ? WHERE id = ?", (status, now, session_id))
            updated = conn.execute(
                "SELECT id, session_code, status, customer_reference, device_make, device_model, notes, created_at, updated_at FROM bench_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
    record_audit("session.status_changed", session_id, {"session_code": updated["session_code"], "from": previous, "to": status}, path)
    return dict(updated)


def create_session(payload: dict, path: Path = DB_PATH) -> dict:
    allowed = {"customer_reference", "device_make", "device_model", "notes"}
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("Unsupported fields: " + ", ".join(sorted(unknown)))
    cleaned: dict[str, str] = {}
    for key in allowed:
        value = payload.get(key, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text.")
        value = value.strip()
        if len(value) > (2000 if key == "notes" else 160):
            raise ValueError(f"{key} exceeds the allowed length.")
        cleaned[key] = value
    now = utc_now()
    session = {
        "id": str(uuid.uuid4()),
        "session_code": "CAM-" + uuid.uuid4().hex[:8].upper(),
        "status": "open",
        **cleaned,
        "created_at": now,
        "updated_at": now,
    }
    init_db(path)
    with closing(sqlite3.connect(path)) as conn:
        with conn:
            conn.execute("""INSERT INTO bench_sessions
            (id, session_code, status, customer_reference, device_make, device_model,
             notes, created_at, updated_at)
            VALUES (:id, :session_code, :status, :customer_reference, :device_make,
                    :device_model, :notes, :created_at, :updated_at)""", session)
    record_audit("session.created", session["id"], {"session_code": session["session_code"], "device_make": session["device_make"], "device_model": session["device_model"]}, path)
    return session


def allowed_origins() -> set[str]:
    defaults = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"}
    configured = ",".join((
        os.environ.get("CAM_ALLOWED_ORIGINS", ""),
        os.environ.get("JROC_CAM_CORS_ORIGINS", ""),
    ))
    return defaults | {origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()}


def make_handler(*, mock: bool, db_path: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "JROCCAM/0.1"

        def log_message(self, fmt, *args):
            LOGGER.info("%s - %s", self.address_string(), fmt % args)

        def send_json(self, code: int, payload: dict | list) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            origin = self.headers.get("Origin", "").rstrip("/")
            if origin and origin in allowed_origins():
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            origin = self.headers.get("Origin", "").rstrip("/")
            if origin not in allowed_origins():
                self.send_json(403, {"error": "Origin is not allowed. Configure CAM_ALLOWED_ORIGINS for this frontend."})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/status":
                self.send_json(200, {
                    "application": "J-ROC AI CAM Repair Pro",
                    "version": "0.1.0",
                    "mode": "mock" if mock else "read-only-discovery",
                    "device_changes_enabled": False,
                    "database": "sqlite",
                    "time_utc": utc_now(),
                })
                return
            if path == "/api/devices":
                try:
                    devices = records_as_dicts(discover_devices(mock=mock))
                    self.send_json(200, {"count": len(devices), "devices": devices, "mock": mock})
                except Exception:
                    LOGGER.exception("Device discovery failed")
                    self.send_json(500, {"error": "Device discovery failed; see local server log."})
                return
            if path == "/api/sessions":
                self.send_json(200, {"sessions": list_sessions(db_path)})
                return
            if path == "/api/audit":
                self.send_json(200, {"events": list_audit_events(db_path)})
                return
            if path == "/api/diagnostics":
                try:
                    self.send_json(200, {"mode": "read-only", "diagnostics": collect_diagnostics()})
                except Exception:
                    LOGGER.exception("Read-only diagnostics failed")
                    self.send_json(500, {"error": "Diagnostics failed; see local server log."})
                return
            if path.startswith("/api/"):
                self.send_json(404, {"error": "Not found"})
                return

            # Prefer the built React app for the normal product URL. The older
            # standalone HTML dashboard remains available at /legacy.
            dist_root = ROOT / "dist"
            if path in ("/legacy", "/legacy/", "/legacy/index.html"):
                target = WEB_ROOT / "index.html"
                content_type = "text/html; charset=utf-8"
            elif (dist_root / "index.html").is_file():
                relative = unquote(path.lstrip("/")) or "index.html"
                root_resolved = dist_root.resolve()
                target = (dist_root / relative).resolve()
                try:
                    target.relative_to(root_resolved)
                except ValueError:
                    self.send_json(403, {"error": "Invalid path"})
                    return
                if not target.is_file():
                    target = dist_root / "index.html"
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in ("application/javascript", "application/json", "image/svg+xml"):
                    content_type += "; charset=utf-8"
            elif path in ("/", "/index.html"):
                target = WEB_ROOT / "index.html"
                content_type = "text/html; charset=utf-8"
            else:
                self.send_json(404, {"error": "Not found"})
                return

            try:
                body = target.read_bytes()
            except OSError:
                self.send_json(500, {"error": "Dashboard asset is missing."})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        def do_PATCH(self):
            route = urlparse(self.path).path
            match = re.fullmatch(r"/api/sessions/([0-9a-fA-F-]{36})", route)
            if not match:
                self.send_json(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4096:
                    self.send_json(413, {"error": "Request body must be between 1 and 4096 bytes."})
                    return
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                with DB_LOCK:
                    session = update_session(match.group(1), payload, db_path)
                self.send_json(200, {"session": session})
            except LookupError as exc:
                self.send_json(404, {"error": str(exc)})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_json(400, {"error": str(exc)})
            except Exception:
                LOGGER.exception("Bench session update failed")
                self.send_json(500, {"error": "Session update failed; see local server log."})

        def do_POST(self):
            route = urlparse(self.path).path
            if route not in ("/api/sessions", "/api/triage"):
                self.send_json(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16384:
                    self.send_json(413, {"error": "Request body must be between 1 and 16384 bytes."})
                    return
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if route == "/api/sessions":
                    with DB_LOCK:
                        session = create_session(payload, db_path)
                    self.send_json(201, {"session": session})
                    return
                if not isinstance(payload, dict) or set(payload) - {"role", "task"}:
                    self.send_json(400, {"error": "Triage expects only role and task fields."})
                    return
                role = payload.get("role", "COMMAND_BRAIN")
                task = payload.get("task", "")
                if not isinstance(role, str) or not isinstance(task, str) or not task.strip():
                    self.send_json(400, {"error": "role must be text and task must be non-empty text."})
                    return
                if len(task) > 12000:
                    self.send_json(413, {"error": "Task exceeds 12000 characters."})
                    return
                try:
                    selected_role = AgentKey(role)
                except ValueError:
                    self.send_json(400, {"error": "Unknown worker role."})
                    return
                settings = get_settings()
                targets, configured_remote = load_model_targets(str(settings.model_config_path))
                remote_opt_in = configured_remote and settings.allow_remote_models
                result = dispatch(
                    "dashboard-triage",
                    selected_role,
                    task,
                    targets=targets,
                    allow_remote=remote_opt_in,
                )
                self.send_json(200, {
                    "role": result.worker.role.value,
                    "summary": result.worker.summary,
                    "model_used": result.worker.model_used,
                    "attempts": list(result.worker.attempts),
                    "elapsed_ms": round(result.elapsed_ms, 3),
                    "fallback_used": result.fallback_used,
                    "requires_technician_review": result.worker.requires_technician_review,
                    "remote_models_allowed": remote_opt_in,
                })
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_json(400, {"error": str(exc)})
            except Exception:
                LOGGER.exception("Dashboard POST request failed")
                self.send_json(500, {"error": "Request failed; see local server log."})

    return DashboardHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the local J-ROC CAM Repair Pro dashboard")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--mock", action="store_true", help="show a synthetic device; no hardware scan")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite session database path")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db(args.db)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(mock=args.mock, db_path=args.db))
    LOGGER.info("Dashboard running at http://127.0.0.1:%s (mock=%s)", args.port, args.mock)
    LOGGER.info("Local-only server. Device-changing operations are disabled.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
