"""Local-first repair-shop workflow and SQLite data layer."""
from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


JOB_STATUSES = (
    "New", "Intake", "Diagnosing", "Estimate", "Awaiting Approval",
    "Awaiting Parts", "Repairing", "QC", "Ready", "Completed",
    "On Hold", "Cancelled",
)
PRIORITIES = ("Low", "Normal", "High", "Urgent")
ESTIMATE_STATUSES = ("Draft", "Approved", "Declined", "Expired")
INVOICE_STATUSES = ("Unpaid", "Partially Paid", "Paid", "Void")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RepairDatabase:
    """SQLite repository for customers, devices, jobs, parts, billing and audit."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _audit(conn: sqlite3.Connection, action: str, entity_type: str,
               entity_id: int | str | None, details: str = "") -> None:
        conn.execute(
            "INSERT INTO audit_log(user_name, action, entity_type, entity_id, details, created_at) "
            "VALUES(?,?,?,?,?,?)",
            ("Local Owner", action, entity_type, str(entity_id or ""), details, now_iso()),
        )

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS customers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                preferences TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS technicians(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'Technician',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS devices(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                device_type TEXT NOT NULL DEFAULT 'Phone',
                manufacturer TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL,
                serial_number TEXT NOT NULL DEFAULT '',
                imei TEXT NOT NULL DEFAULT '',
                condition_notes TEXT NOT NULL DEFAULT '',
                reported_issue TEXT NOT NULL DEFAULT '',
                accessories TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_number TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                device_id INTEGER NOT NULL REFERENCES devices(id),
                complaint TEXT NOT NULL,
                intake_notes TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Normal',
                status TEXT NOT NULL DEFAULT 'New',
                technician_id INTEGER REFERENCES technicians(id),
                warranty_of INTEGER REFERENCES jobs(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS diagnostics(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                findings TEXT NOT NULL,
                next_action TEXT NOT NULL DEFAULT '',
                technician_id INTEGER REFERENCES technicians(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repair_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                technician_id INTEGER REFERENCES technicians(id),
                description TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS parts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                min_quantity INTEGER NOT NULL DEFAULT 0 CHECK(min_quantity >= 0),
                unit_cost REAL NOT NULL DEFAULT 0 CHECK(unit_cost >= 0),
                retail_price REAL NOT NULL DEFAULT 0 CHECK(retail_price >= 0),
                supplier TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inventory_movements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL REFERENCES parts(id),
                job_id INTEGER REFERENCES jobs(id),
                delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_parts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id),
                part_id INTEGER NOT NULL REFERENCES parts(id),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS estimates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id),
                status TEXT NOT NULL DEFAULT 'Draft',
                subtotal REAL NOT NULL,
                tax_rate REAL NOT NULL DEFAULT 0,
                tax_amount REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL,
                approved_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS estimate_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                quantity REAL NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                line_total REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS invoices(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                job_id INTEGER NOT NULL REFERENCES jobs(id),
                estimate_id INTEGER REFERENCES estimates(id),
                subtotal REAL NOT NULL,
                tax_rate REAL NOT NULL DEFAULT 0,
                tax_amount REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL,
                amount_paid REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Unpaid',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL REFERENCES invoices(id),
                amount REAL NOT NULL CHECK(amount > 0),
                method TEXT NOT NULL DEFAULT 'Cash',
                reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS qc_checks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                check_name TEXT NOT NULL,
                passed INTEGER NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                technician_id INTEGER REFERENCES technicians(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notification_queue(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER REFERENCES jobs(id),
                channel TEXT NOT NULL DEFAULT 'Manual',
                recipient TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft',
                created_at TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS warranty_cases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_job_id INTEGER NOT NULL REFERENCES jobs(id),
                new_job_id INTEGER REFERENCES jobs(id),
                terms TEXT NOT NULL DEFAULT '',
                expires_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL
            );
            """)
            defaults = {
                "shop_name": "J-Roc AI Mobile Repair",
                "shop_address": "",
                "shop_phone": "",
                "shop_email": "",
                "currency": "USD",
                "tax_rate": "0",
            }
            for key, value in defaults.items():
                db.execute(
                    "INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                    (key, value, now_iso()),
                )

    def add_customer(self, name: str, phone: str = "", email: str = "",
                     address: str = "", notes: str = "", preferences: str = "") -> int:
        name = name.strip()
        if not name:
            raise ValueError("Customer name is required.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO customers(name,phone,email,address,notes,preferences,created_at) VALUES(?,?,?,?,?,?,?)",
                (name, phone.strip(), email.strip(), address.strip(), notes.strip(),
                 preferences.strip(), now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "customer", ident, name)
            return ident

    def list_customers(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM customers ORDER BY name COLLATE NOCASE")]

    def add_technician(self, name: str, phone: str = "", email: str = "",
                       role: str = "Technician") -> int:
        if not name.strip():
            raise ValueError("Technician name is required.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO technicians(name,phone,email,role,created_at) VALUES(?,?,?,?,?)",
                (name.strip(), phone.strip(), email.strip(), role.strip() or "Technician", now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "technician", ident, name.strip())
            return ident

    def list_technicians(self, active_only: bool = True) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = "SELECT * FROM technicians"
            if active_only:
                sql += " WHERE active=1"
            sql += " ORDER BY name COLLATE NOCASE"
            return [dict(r) for r in db.execute(sql)]

    def add_device(self, customer_id: int, model: str, device_type: str = "Phone",
                   manufacturer: str = "", serial_number: str = "", imei: str = "",
                   condition_notes: str = "", reported_issue: str = "",
                   accessories: str = "") -> int:
        if not model.strip():
            raise ValueError("Device model is required.")
        manufacturer = manufacturer.strip().title()
        device_type = device_type.strip().title()
        if manufacturer not in ("Apple", "Samsung"):
            raise ValueError("This edition supports Apple and Samsung devices only.")
        if device_type not in ("Phone", "Tablet", "Laptop"):
            raise ValueError("This edition supports phones, tablets and laptops only.")
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM customers WHERE id=?", (customer_id,)).fetchone():
                raise ValueError("Select an existing customer.")
            cur = db.execute(
                "INSERT INTO devices(customer_id,device_type,manufacturer,model,serial_number,imei,"
                "condition_notes,reported_issue,accessories,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (customer_id, device_type.strip() or "Phone", manufacturer.strip(), model.strip(),
                 serial_number.strip(), imei.strip(), condition_notes.strip(), reported_issue.strip(),
                 accessories.strip(), now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "device", ident, f"{manufacturer} {model}".strip())
            return ident

    def list_devices(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT d.*, c.name AS customer_name FROM devices d "
                "JOIN customers c ON c.id=d.customer_id ORDER BY d.id DESC"
            )
            return [dict(r) for r in rows]

    def create_job(self, customer_id: int, device_id: int, complaint: str,
                   intake_notes: str = "", priority: str = "Normal",
                   technician_id: int | None = None, warranty_of: int | None = None) -> int:
        if not complaint.strip():
            raise ValueError("The reported issue is required.")
        if priority not in PRIORITIES:
            raise ValueError("Choose a valid priority.")
        with self._connect() as db:
            device = db.execute(
                "SELECT customer_id,manufacturer,device_type FROM devices WHERE id=?", (device_id,)
            ).fetchone()
            if not device or int(device["customer_id"]) != int(customer_id):
                raise ValueError("The selected device must belong to the selected customer.")
            if device["manufacturer"] not in ("Apple", "Samsung") or device["device_type"] not in ("Phone", "Tablet", "Laptop"):
                raise ValueError("This edition supports only Apple and Samsung phones, tablets and laptops.")
            created = now_iso()
            cur = db.execute(
                "INSERT INTO jobs(job_number,customer_id,device_id,complaint,intake_notes,priority,status,"
                "technician_id,warranty_of,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("PENDING", customer_id, device_id, complaint.strip(), intake_notes.strip(),
                 priority, "New", technician_id, warranty_of, created, created),
            )
            ident = int(cur.lastrowid)
            job_number = f"JRM-{datetime.now():%Y%m}-{ident:06d}"
            db.execute("UPDATE jobs SET job_number=? WHERE id=?", (job_number, ident))
            self._audit(db, "CREATE", "job", ident, f"{job_number}: {complaint.strip()}")
            return ident

    def list_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = (
                "SELECT j.*, c.name AS customer_name, c.phone AS customer_phone, "
                "d.device_type, d.manufacturer, d.model, d.serial_number, "
                "t.name AS technician_name FROM jobs j "
                "JOIN customers c ON c.id=j.customer_id JOIN devices d ON d.id=j.device_id "
                "LEFT JOIN technicians t ON t.id=j.technician_id"
            )
            args: tuple[Any, ...] = ()
            if status:
                sql += " WHERE j.status=?"
                args = (status,)
            sql += " ORDER BY j.id DESC"
            return [dict(r) for r in db.execute(sql, args)]

    def update_job_status(self, job_id: int, status: str) -> None:
        if status not in JOB_STATUSES:
            raise ValueError("Choose a valid job status.")
        with self._connect() as db:
            cur = db.execute(
                "UPDATE jobs SET status=?,updated_at=? WHERE id=?",
                (status, now_iso(), job_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Repair job not found.")
            self._audit(db, "STATUS", "job", job_id, status)

    def assign_technician(self, job_id: int, technician_id: int | None) -> None:
        with self._connect() as db:
            cur = db.execute(
                "UPDATE jobs SET technician_id=?,updated_at=? WHERE id=?",
                (technician_id, now_iso(), job_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Repair job not found.")
            self._audit(db, "ASSIGN", "job", job_id, f"technician_id={technician_id}")

    def add_diagnostic(self, job_id: int, category: str, findings: str,
                       next_action: str = "", technician_id: int | None = None) -> int:
        if not category.strip() or not findings.strip():
            raise ValueError("Diagnostic category and findings are required.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO diagnostics(job_id,category,findings,next_action,technician_id,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (job_id, category.strip(), findings.strip(), next_action.strip(), technician_id, now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "diagnostic", ident, f"job_id={job_id}; {category.strip()}")
            return ident

    def list_diagnostics(self, job_id: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = (
                "SELECT d.*, j.job_number, t.name AS technician_name FROM diagnostics d "
                "JOIN jobs j ON j.id=d.job_id LEFT JOIN technicians t ON t.id=d.technician_id"
            )
            args: tuple[Any, ...] = ()
            if job_id is not None:
                sql += " WHERE d.job_id=?"
                args = (job_id,)
            sql += " ORDER BY d.id DESC"
            return [dict(r) for r in db.execute(sql, args)]

    def add_repair_log(self, job_id: int, description: str,
                       duration_minutes: int = 0, technician_id: int | None = None) -> int:
        if not description.strip():
            raise ValueError("Repair work description is required.")
        if int(duration_minutes) < 0:
            raise ValueError("Duration cannot be negative.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO repair_logs(job_id,technician_id,description,duration_minutes,created_at) "
                "VALUES(?,?,?,?,?)",
                (job_id, technician_id, description.strip(), int(duration_minutes), now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "repair_log", ident, f"job_id={job_id}")
            return ident

    def list_repair_logs(self, job_id: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = ("SELECT r.*, j.job_number, t.name AS technician_name FROM repair_logs r "
                   "JOIN jobs j ON j.id=r.job_id LEFT JOIN technicians t ON t.id=r.technician_id")
            args: tuple[Any, ...] = ()
            if job_id is not None:
                sql += " WHERE r.job_id=?"
                args = (job_id,)
            sql += " ORDER BY r.id DESC"
            return [dict(r) for r in db.execute(sql, args)]

    def add_part(self, sku: str, name: str, quantity: int = 0, min_quantity: int = 0,
                 unit_cost: float = 0, retail_price: float = 0, category: str = "",
                 supplier: str = "") -> int:
        if not sku.strip() or not name.strip():
            raise ValueError("Part SKU and name are required.")
        if int(quantity) < 0 or int(min_quantity) < 0 or float(unit_cost) < 0 or float(retail_price) < 0:
            raise ValueError("Stock thresholds and prices cannot be negative.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO parts(sku,name,category,quantity,min_quantity,unit_cost,retail_price,supplier,"
                "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (sku.strip(), name.strip(), category.strip(), int(quantity), int(min_quantity),
                 float(unit_cost), float(retail_price), supplier.strip(), now_iso(), now_iso()),
            )
            ident = int(cur.lastrowid)
            if quantity:
                db.execute(
                    "INSERT INTO inventory_movements(part_id,delta,reason,created_at) VALUES(?,?,?,?)",
                    (ident, int(quantity), "Opening stock", now_iso()),
                )
            self._audit(db, "CREATE", "part", ident, f"{sku.strip()}: {name.strip()}")
            return ident

    def list_parts(self, low_stock_only: bool = False) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = "SELECT * FROM parts"
            if low_stock_only:
                sql += " WHERE quantity <= min_quantity"
            sql += " ORDER BY name COLLATE NOCASE"
            return [dict(r) for r in db.execute(sql)]

    def adjust_inventory(self, part_id: int, delta: int, reason: str,
                         reference: str = "") -> None:
        if int(delta) == 0:
            raise ValueError("Stock adjustment must be non-zero.")
        if not reason.strip():
            raise ValueError("A stock adjustment reason is required.")
        with self._connect() as db:
            row = db.execute("SELECT quantity FROM parts WHERE id=?", (part_id,)).fetchone()
            if not row:
                raise ValueError("Part not found.")
            new_qty = int(row["quantity"]) + int(delta)
            if new_qty < 0:
                raise ValueError("Stock cannot become negative.")
            db.execute("UPDATE parts SET quantity=?,updated_at=? WHERE id=?",
                       (new_qty, now_iso(), part_id))
            db.execute(
                "INSERT INTO inventory_movements(part_id,delta,reason,reference,created_at) "
                "VALUES(?,?,?,?,?)",
                (part_id, int(delta), reason.strip(), reference.strip(), now_iso()),
            )
            self._audit(db, "STOCK_ADJUST", "part", part_id,
                        f"delta={int(delta)}; new_qty={new_qty}; {reason.strip()}")

    def consume_part(self, job_id: int, part_id: int, quantity: int) -> int:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        with self._connect() as db:
            part = db.execute("SELECT * FROM parts WHERE id=?", (part_id,)).fetchone()
            if not part:
                raise ValueError("Part not found.")
            if int(part["quantity"]) < quantity:
                raise ValueError("Not enough stock is available.")
            if not db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                raise ValueError("Repair job not found.")
            unit_cost = float(part["unit_cost"])
            total_cost = round(unit_cost * quantity, 2)
            db.execute("UPDATE parts SET quantity=quantity-?,updated_at=? WHERE id=?",
                       (quantity, now_iso(), part_id))
            db.execute(
                "INSERT INTO inventory_movements(part_id,job_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (part_id, job_id, -quantity, "Consumed by repair job", now_iso()),
            )
            cur = db.execute(
                "INSERT INTO job_parts(job_id,part_id,quantity,unit_cost,total_cost,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (job_id, part_id, quantity, unit_cost, total_cost, now_iso()),
            )
            self._audit(db, "CONSUME_PART", "job", job_id,
                        f"part_id={part_id}; qty={quantity}; cost={total_cost:.2f}")
            return int(cur.lastrowid)

    def create_estimate(self, job_id: int, items: list[dict[str, Any]],
                        tax_rate: float | None = None) -> int:
        if not items:
            raise ValueError("Add at least one estimate item.")
        if tax_rate is None:
            tax_rate = float(self.get_setting("tax_rate", "0") or 0)
        tax_rate = float(tax_rate)
        if tax_rate < 0 or tax_rate > 100:
            raise ValueError("Tax rate must be between 0 and 100.")
        normalized = []
        subtotal = 0.0
        for item in items:
            desc = str(item.get("description", "")).strip()
            qty = float(item.get("quantity", 1))
            price = float(item.get("unit_price", 0))
            if not desc or qty <= 0 or price < 0:
                raise ValueError("Every estimate item needs a description, positive quantity and non-negative price.")
            line = round(qty * price, 2)
            subtotal += line
            normalized.append((desc, qty, price, line))
        subtotal = round(subtotal, 2)
        tax = round(subtotal * tax_rate / 100.0, 2)
        total = round(subtotal + tax, 2)
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                raise ValueError("Repair job not found.")
            cur = db.execute(
                "INSERT INTO estimates(job_id,status,subtotal,tax_rate,tax_amount,total,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (job_id, "Draft", subtotal, tax_rate, tax, total, now_iso()),
            )
            ident = int(cur.lastrowid)
            for desc, qty, price, line in normalized:
                db.execute(
                    "INSERT INTO estimate_items(estimate_id,description,quantity,unit_price,line_total) "
                    "VALUES(?,?,?,?,?)",
                    (ident, desc, qty, price, line),
                )
            db.execute("UPDATE jobs SET status='Estimate',updated_at=? WHERE id=?",
                       (now_iso(), job_id))
            self._audit(db, "CREATE", "estimate", ident, f"job_id={job_id}; total={total:.2f}")
            return ident

    def list_estimates(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT e.*, j.job_number, c.name AS customer_name, d.model FROM estimates e "
                "JOIN jobs j ON j.id=e.job_id JOIN customers c ON c.id=j.customer_id "
                "JOIN devices d ON d.id=j.device_id ORDER BY e.id DESC"
            )
            return [dict(r) for r in rows]

    def get_estimate_items(self, estimate_id: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM estimate_items WHERE estimate_id=? ORDER BY id", (estimate_id,)
            )]

    def set_estimate_status(self, estimate_id: int, status: str) -> None:
        if status not in ESTIMATE_STATUSES:
            raise ValueError("Choose a valid estimate status.")
        with self._connect() as db:
            row = db.execute("SELECT job_id FROM estimates WHERE id=?", (estimate_id,)).fetchone()
            if not row:
                raise ValueError("Estimate not found.")
            approved_at = now_iso() if status == "Approved" else ""
            db.execute("UPDATE estimates SET status=?,approved_at=? WHERE id=?",
                       (status, approved_at, estimate_id))
            job_status = "Awaiting Approval" if status == "Draft" else "Awaiting Parts" if status == "Approved" else "Estimate"
            db.execute("UPDATE jobs SET status=?,updated_at=? WHERE id=?",
                       (job_status, now_iso(), int(row["job_id"])))
            self._audit(db, "STATUS", "estimate", estimate_id, status)

    def create_invoice(self, job_id: int, tax_rate: float | None = None) -> int:
        with self._connect() as db:
            estimate = db.execute(
                "SELECT * FROM estimates WHERE job_id=? AND status='Approved' ORDER BY id DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            if not estimate:
                raise ValueError("Approve an estimate before creating an invoice.")
            rate = float(estimate["tax_rate"] if tax_rate is None else tax_rate)
            if rate < 0 or rate > 100:
                raise ValueError("Tax rate must be between 0 and 100.")
            subtotal = float(estimate["subtotal"])
            tax = round(subtotal * rate / 100.0, 2)
            total = round(subtotal + tax, 2)
            invoice_no = "JRM-INV-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            cur = db.execute(
                "INSERT INTO invoices(invoice_number,job_id,estimate_id,subtotal,tax_rate,tax_amount,total,"
                "amount_paid,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (invoice_no, job_id, int(estimate["id"]), subtotal, rate, tax, total, 0.0, "Unpaid", now_iso()),
            )
            ident = int(cur.lastrowid)
            db.execute("UPDATE jobs SET status='Ready',updated_at=? WHERE id=?",
                       (now_iso(), job_id))
            self._audit(db, "CREATE", "invoice", ident, f"{invoice_no}; total={total:.2f}")
            return ident

    def list_invoices(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT i.*, j.job_number, c.name AS customer_name FROM invoices i "
                "JOIN jobs j ON j.id=i.job_id JOIN customers c ON c.id=j.customer_id ORDER BY i.id DESC"
            )
            return [dict(r) for r in rows]

    def record_payment(self, invoice_id: int, amount: float, method: str = "Cash",
                       reference: str = "") -> None:
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        with self._connect() as db:
            invoice = db.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            if not invoice:
                raise ValueError("Invoice not found.")
            balance = round(float(invoice["total"]) - float(invoice["amount_paid"]), 2)
            if amount > balance + 0.005:
                raise ValueError(f"Payment exceeds the remaining balance of {balance:.2f}.")
            db.execute(
                "INSERT INTO payments(invoice_id,amount,method,reference,created_at) VALUES(?,?,?,?,?)",
                (invoice_id, amount, method.strip() or "Cash", reference.strip(), now_iso()),
            )
            paid = round(float(invoice["amount_paid"]) + amount, 2)
            status = "Paid" if paid >= float(invoice["total"]) - 0.005 else "Partially Paid"
            db.execute("UPDATE invoices SET amount_paid=?,status=? WHERE id=?",
                       (paid, status, invoice_id))
            self._audit(db, "PAYMENT", "invoice", invoice_id,
                        f"amount={amount:.2f}; method={method}; status={status}")

    def add_qc_check(self, job_id: int, check_name: str, passed: bool,
                     notes: str = "", technician_id: int | None = None) -> int:
        if not check_name.strip():
            raise ValueError("QC check name is required.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO qc_checks(job_id,check_name,passed,notes,technician_id,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (job_id, check_name.strip(), 1 if passed else 0, notes.strip(), technician_id, now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "QC_CHECK", "job", job_id,
                        f"{check_name.strip()}: {'PASS' if passed else 'FAIL'}")
            return ident

    def list_qc_checks(self, job_id: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = ("SELECT q.*, j.job_number, t.name AS technician_name FROM qc_checks q "
                   "JOIN jobs j ON j.id=q.job_id LEFT JOIN technicians t ON t.id=q.technician_id")
            args: tuple[Any, ...] = ()
            if job_id is not None:
                sql += " WHERE q.job_id=?"
                args = (job_id,)
            sql += " ORDER BY q.id DESC"
            return [dict(r) for r in db.execute(sql, args)]

    def queue_notification(self, job_id: int, channel: str, recipient: str, message: str) -> int:
        if not message.strip():
            raise ValueError("Notification message is required.")
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO notification_queue(job_id,channel,recipient,message,status,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (job_id, channel.strip() or "Manual", recipient.strip(), message.strip(), "Draft", now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "QUEUE", "notification", ident, f"job_id={job_id}; channel={channel}")
            return ident

    def list_audit(self, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (int(limit),))
            return [dict(r) for r in rows]

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        if not key.strip():
            raise ValueError("Setting key is required.")
        with self._connect() as db:
            db.execute(
                "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (key.strip(), str(value), now_iso()),
            )
            self._audit(db, "SETTING", "setting", key.strip(), str(value))

    def dashboard_summary(self) -> dict[str, float | int]:
        with self._connect() as db:
            open_count = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status NOT IN ('Completed','Cancelled')"
            ).fetchone()[0]
            waiting = db.execute("SELECT COUNT(*) FROM jobs WHERE status='Awaiting Approval'").fetchone()[0]
            qc_pending = db.execute("SELECT COUNT(*) FROM jobs WHERE status='QC'").fetchone()[0]
            low_stock = db.execute("SELECT COUNT(*) FROM parts WHERE quantity <= min_quantity").fetchone()[0]
            balance = db.execute("SELECT COALESCE(SUM(total-amount_paid),0) FROM invoices WHERE status!='Void'").fetchone()[0]
            revenue = db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM payments WHERE date(created_at)=date('now','localtime')"
            ).fetchone()[0]
            return {
                "open_jobs": int(open_count), "waiting_approval": int(waiting),
                "qc_pending": int(qc_pending), "low_stock": int(low_stock),
                "outstanding_balance": round(float(balance), 2),
                "payments_today": round(float(revenue), 2),
            }

    def export_jobs_csv(self, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.list_jobs()
        columns = ["job_number", "customer_name", "device_type", "manufacturer", "model",
                   "serial_number", "complaint", "priority", "status", "technician_name",
                   "created_at", "updated_at"]
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def backup_database(self, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as source:
            target = sqlite3.connect(str(path))
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()
        return path

    def integrity_check(self) -> str:
        with self._connect() as db:
            result = db.execute("PRAGMA integrity_check").fetchone()[0]
            return str(result)

    def inventory_history(self, part_id: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            sql = (
                "SELECT m.*, p.sku, p.name AS part_name, j.job_number FROM inventory_movements m "
                "JOIN parts p ON p.id=m.part_id LEFT JOIN jobs j ON j.id=m.job_id"
            )
            args: tuple[Any, ...] = ()
            if part_id is not None:
                sql += " WHERE m.part_id=?"
                args = (part_id,)
            sql += " ORDER BY m.id DESC"
            return [dict(r) for r in db.execute(sql, args)]

    def create_warranty_case(self, original_job_id: int, terms: str,
                             expires_at: str = "", new_job_id: int | None = None) -> int:
        if not terms.strip():
            raise ValueError("Warranty terms or reported warranty issue are required.")
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM jobs WHERE id=?", (original_job_id,)).fetchone():
                raise ValueError("Original repair job not found.")
            if new_job_id is not None and not db.execute(
                "SELECT 1 FROM jobs WHERE id=?", (new_job_id,)
            ).fetchone():
                raise ValueError("Linked follow-up job not found.")
            cur = db.execute(
                "INSERT INTO warranty_cases(original_job_id,new_job_id,terms,expires_at,status,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (original_job_id, new_job_id, terms.strip(), expires_at.strip(), "Open", now_iso()),
            )
            ident = int(cur.lastrowid)
            self._audit(db, "CREATE", "warranty_case", ident,
                        f"original_job_id={original_job_id}; follow_up_job_id={new_job_id}")
            return ident

    def list_warranty_cases(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT w.*, o.job_number AS original_job_number, "
                "n.job_number AS new_job_number, c.name AS customer_name, d.model "
                "FROM warranty_cases w JOIN jobs o ON o.id=w.original_job_id "
                "JOIN customers c ON c.id=o.customer_id JOIN devices d ON d.id=o.device_id "
                "LEFT JOIN jobs n ON n.id=w.new_job_id ORDER BY w.id DESC"
            )
            return [dict(r) for r in rows]

    def update_warranty_status(self, warranty_id: int, status: str) -> None:
        if status not in ("Open", "Approved", "Denied", "Expired", "Closed"):
            raise ValueError("Choose a valid warranty status.")
        with self._connect() as db:
            cur = db.execute("UPDATE warranty_cases SET status=? WHERE id=?", (status, warranty_id))
            if cur.rowcount == 0:
                raise ValueError("Warranty case not found.")
            self._audit(db, "STATUS", "warranty_case", warranty_id, status)

    def list_notifications(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT n.*, j.job_number FROM notification_queue n "
                "LEFT JOIN jobs j ON j.id=n.job_id ORDER BY n.id DESC"
            )
            return [dict(r) for r in rows]
