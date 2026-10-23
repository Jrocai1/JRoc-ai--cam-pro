"""J-Roc AI Mobile Repair — local-first repair shop and device service desktop app."""
from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from jroc_mobile import __version__
from jroc_mobile.core import JOB_STATUSES, PRIORITIES, RepairDatabase
from jroc_mobile.device_tools import collect_diagnostics, format_report, inspect_firmware

APP_NAME = "J-Roc AI Mobile Repair"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "JROC" / "MobileRepair"
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=DATA_DIR / "application.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
DB_PATH = DATA_DIR / "mobile_repair.sqlite3"


def _money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _choice_id(value):
    if not value or str(value).startswith("Unassigned"):
        return None
    try:
        return int(str(value).split(" | ", 1)[0])
    except (ValueError, TypeError):
        return None


class FormDialog(tk.Toplevel):
    """Small validated modal form used for owner/technician data entry."""

    def __init__(self, parent, title, fields):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, True)
        self.transient(parent)
        self.result = None
        self.variables = {}
        self.field_specs = {field["key"]: field for field in fields}
        self.configure(padx=16, pady=14)
        ttk.Label(self, text=title, font=("Segoe UI Semibold", 14)).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        for index, field in enumerate(fields, start=1):
            ttk.Label(self, text=field["label"]).grid(row=index, column=0, sticky="w", padx=(0, 14), pady=5)
            variable = tk.StringVar(value=str(field.get("default", "")))
            self.variables[field["key"]] = variable
            choices = field.get("choices")
            if choices:
                widget = ttk.Combobox(self, textvariable=variable, values=choices, state="readonly", width=42)
                if variable.get() not in choices:
                    variable.set(choices[0] if choices else "")
            else:
                widget = ttk.Entry(self, textvariable=variable, width=45)
            widget.grid(row=index, column=1, sticky="ew", pady=5)
        buttons = ttk.Frame(self)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save", command=self._save).pack(side="right")
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.grab_set()
        self.update_idletasks()
        x = parent.winfo_rootx() + max(20, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(20, (parent.winfo_height() - self.winfo_height()) // 3)
        self.geometry(f"+{x}+{y}")
        self.wait_window(self)

    def _save(self):
        values = {key: variable.get().strip() for key, variable in self.variables.items()}
        for key, field in self.field_specs.items():
            if field.get("required") and not values.get(key):
                messagebox.showerror("Required field", f"{field['label']} is required.", parent=self)
                return
        self.result = values
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{__version__}")
        self.geometry("1280x820")
        self.minsize(1020, 680)
        self.configure(bg="#10151d")
        self.db = RepairDatabase(DB_PATH)
        self._style()
        self._build()
        self.refresh_all()
        self._tool_log("Ready. Local repair-shop database initialized.")
        self._tool_log("Device diagnostics are read-only. Firmware writing is disabled.")

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#10151d")
        style.configure("Panel.TFrame", background="#1a2230")
        style.configure("TLabel", background="#10151d", foreground="#e5ebf4", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 23), foreground="#ffffff")
        style.configure("Subtitle.TLabel", foreground="#a7b5c8")
        style.configure("TButton", padding=(10, 7), font=("Segoe UI", 9))
        style.configure("Treeview", background="#151c27", foreground="#e5ebf4",
                        fieldbackground="#151c27", rowheight=25, borderwidth=0)
        style.configure("Treeview.Heading", background="#263449", foreground="#ffffff",
                        font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#304f76")])
        style.configure("TNotebook", background="#10151d", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 8), background="#202a39", foreground="#e5ebf4")
        style.map("TNotebook.Tab", background=[("selected", "#365579")])

    def _build(self):
        header = ttk.Frame(self, padding=(20, 16, 20, 12))
        header.pack(fill="x")
        left = ttk.Frame(header)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="J-ROC AI", style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(left, text="Mobile Repair", style="Title.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(left, text="Repair operations • Device diagnostics • Shop management • Local-first",
                  style="Subtitle.TLabel").pack(anchor="w")
        ttk.Button(header, text="+ New Repair Job", command=self.new_job).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Refresh Workspace", command=self.refresh_all).pack(side="right")
        status = ttk.Frame(self, style="Panel.TFrame", padding=(14, 9))
        status.pack(fill="x", padx=20, pady=(0, 10))
        ttk.Label(status, text="LOCAL OWNER WORKSTATION", background="#1a2230",
                  foreground="#9dd6bc").pack(side="left")
        ttk.Label(status, text=f"Version {__version__}  •  Data: {DB_PATH}",
                  background="#1a2230", foreground="#a7b5c8").pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self._build_dashboard_tab()
        self._build_customers_tab()
        self._build_devices_tab()
        self._build_jobs_tab()
        self._build_inventory_tab()
        self._build_technicians_tab()
        self._build_billing_tab()
        self._build_qc_reports_tab()
        self._build_warranty_tab()
        self._build_device_tools_tab()
        self._build_settings_tab()

    def _tab(self, title):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text=title)
        return frame

    def _tree(self, parent, columns, height=15):
        tree = ttk.Treeview(parent, columns=[col[0] for col in columns], show="headings", height=height)
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=60, stretch=True)
        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return tree

    def _buttons(self, parent, buttons):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 10))
        for label, command in buttons:
            ttk.Button(bar, text=label, command=command).pack(side="left", padx=(0, 7))
        return bar

    def _populate(self, tree, rows, mapping):
        tree.delete(*tree.get_children())
        for row in rows:
            values = [mapping(row, key) for key in tree["columns"]]
            tree.insert("", "end", values=values)

    def _form(self, title, fields):
        dialog = FormDialog(self, title, fields)
        return dialog.result

    def _run_action(self, action, refresh=True):
        try:
            result = action()
            if result is not None:
                self._tool_log(str(result))
            if refresh:
                self.refresh_all()
            return result
        except Exception as exc:
            logging.exception("UI action failed")
            messagebox.showerror("J-Roc AI Mobile Repair", str(exc), parent=self)
            return None

    def _selected_id(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Select a record", "Select a row first.", parent=self)
            return None
        values = tree.item(selection[0], "values")
        try:
            return int(values[0])
        except (ValueError, TypeError, IndexError):
            return None

    def _selected_job_id(self):
        return self._selected_id(self.jobs_tree)

    def _customer_choices(self):
        return [f"{row['id']} | {row['name']} | {row['phone']}" for row in self.db.list_customers()]

    def _device_choices(self):
        return [
            f"{row['id']} | {row['manufacturer']} {row['model']} | {row['customer_name']}"
            for row in self.db.list_devices()
        ]

    def _technician_choices(self):
        return ["Unassigned"] + [
            f"{row['id']} | {row['name']} ({row['role']})" for row in self.db.list_technicians()
        ]

    def _job_choices(self):
        return [f"{row['id']} | {row['job_number']} | {row['customer_name']} | {row['model']}"
                for row in self.db.list_jobs()]

    def _part_choices(self):
        return [f"{row['id']} | {row['sku']} | {row['name']} (stock {row['quantity']})"
                for row in self.db.list_parts()]

    def _money(self, amount):
        return _money(amount)

    # Dashboard
    def _build_dashboard_tab(self):
        tab = self._tab("Overview")
        ttk.Label(tab, text="Owner Command Center", font=("Segoe UI Semibold", 17)).pack(anchor="w")
        ttk.Label(tab, text="Review exceptions first: jobs waiting, QC, stock shortages and outstanding balances.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(3, 12))
        tiles = ttk.Frame(tab)
        tiles.pack(fill="x", pady=(0, 12))
        self.summary_vars = {}
        for key, label in [
            ("open_jobs", "Open Jobs"), ("waiting_approval", "Awaiting Approval"),
            ("qc_pending", "Jobs in QC"), ("low_stock", "Low-Stock Parts"),
            ("payments_today", "Payments Today"), ("outstanding_balance", "Outstanding Balance")
        ]:
            box = ttk.Frame(tiles, style="Panel.TFrame", padding=12)
            box.pack(side="left", fill="both", expand=True, padx=(0, 7))
            ttk.Label(box, text=label, background="#1a2230", foreground="#a7b5c8").pack(anchor="w")
            variable = tk.StringVar(value="0")
            self.summary_vars[key] = variable
            ttk.Label(box, textvariable=variable, background="#1a2230",
                      foreground="#ffffff", font=("Segoe UI Semibold", 19)).pack(anchor="w", pady=(5, 0))
        ttk.Label(tab, text="Latest repair jobs", font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(4, 7))
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.dashboard_jobs_tree = self._tree(holder, [
            ("id", "ID", 55), ("job_number", "Job Number", 155), ("customer_name", "Customer", 170),
            ("model", "Device", 170), ("status", "Status", 140), ("priority", "Priority", 85),
            ("created_at", "Created", 175),
        ], height=12)
        self._buttons(tab, [("New Customer", self.new_customer), ("New Device", self.new_device),
                            ("New Repair Job", self.new_job), ("Refresh", self.refresh_all)])

    # Customers
    def _build_customers_tab(self):
        tab = self._tab("Customers")
        self._buttons(tab, [("+ Add Customer", self.new_customer), ("Refresh", self.refresh_customers)])
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.customers_tree = self._tree(holder, [
            ("id", "ID", 60), ("name", "Customer", 210), ("phone", "Phone", 140),
            ("email", "Email", 220), ("address", "Address", 300), ("created_at", "Added", 170),
        ])

    # Devices
    def _build_devices_tab(self):
        tab = self._tab("Devices")
        self._buttons(tab, [("+ Register Device", self.new_device), ("Refresh", self.refresh_devices)])
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.devices_tree = self._tree(holder, [
            ("id", "ID", 55), ("customer_name", "Customer", 165), ("device_type", "Type", 100),
            ("manufacturer", "Manufacturer", 130), ("model", "Model", 155), ("serial_number", "Serial", 155),
            ("imei", "IMEI", 150), ("condition_notes", "Condition / Damage", 240),
        ])

    # Jobs
    def _build_jobs_tab(self):
        tab = self._tab("Repair Jobs")
        self._buttons(tab, [
            ("+ New Job", self.new_job), ("Update Status", self.update_job_status),
            ("Assign Technician", self.assign_job), ("Add Diagnosis", self.add_diagnostic),
            ("Log Repair Work", self.add_repair_log), ("Use Part", self.consume_part),
            ("Add QC Check", self.add_qc_check), ("Queue Ready Notice", self.queue_ready_notice),
            ("Refresh", self.refresh_jobs),
        ])
        ttk.Label(tab, text="Workflow: intake → diagnose → estimate → approval → parts → repair → QC → invoice → return.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(0, 8))
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.jobs_tree = self._tree(holder, [
            ("id", "ID", 48), ("job_number", "Job #", 145), ("customer_name", "Customer", 145),
            ("device_type", "Type", 80), ("manufacturer", "Brand", 95), ("model", "Model", 130),
            ("status", "Status", 140), ("priority", "Priority", 80), ("technician_name", "Technician", 120),
            ("complaint", "Reported Issue", 230), ("created_at", "Created", 160),
        ])

    # Inventory
    def _build_inventory_tab(self):
        tab = self._tab("Parts & Inventory")
        self._buttons(tab, [
            ("+ Add Part", self.new_part), ("Adjust Stock", self.adjust_stock),
            ("Use Part on Selected Job", self.consume_part), ("Show Low Stock", self.show_low_stock),
            ("Inventory History", self.show_inventory_history), ("Refresh", self.refresh_inventory),
        ])
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.inventory_tree = self._tree(holder, [
            ("id", "ID", 50), ("sku", "SKU", 125), ("name", "Part", 240), ("category", "Category", 120),
            ("quantity", "On Hand", 80), ("min_quantity", "Minimum", 80), ("unit_cost", "Unit Cost", 90),
            ("retail_price", "Retail Price", 95), ("supplier", "Supplier", 160),
        ])

    # Technicians
    def _build_technicians_tab(self):
        tab = self._tab("Technicians")
        self._buttons(tab, [("+ Add Technician", self.new_technician), ("Refresh", self.refresh_technicians)])
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self.technicians_tree = self._tree(holder, [
            ("id", "ID", 60), ("name", "Name", 220), ("role", "Role", 140),
            ("phone", "Phone", 150), ("email", "Email", 240), ("active", "Active", 80),
        ])

    # Estimates / billing
    def _build_billing_tab(self):
        tab = self._tab("Estimates & Invoices")
        self._buttons(tab, [
            ("+ Create Estimate for Job", self.new_estimate), ("Approve Estimate", self.approve_estimate),
            ("Decline Estimate", self.decline_estimate), ("Create Invoice", self.create_invoice),
            ("Record Payment", self.record_payment), ("Refresh", self.refresh_billing),
        ])
        panels = ttk.Panedwindow(tab, orient="vertical")
        panels.pack(fill="both", expand=True)
        estimate_frame = ttk.Labelframe(panels, text="Estimates — approval required before paid repair work")
        invoice_frame = ttk.Labelframe(panels, text="Invoices and payments")
        panels.add(estimate_frame, weight=1)
        panels.add(invoice_frame, weight=1)
        est_holder = ttk.Frame(estimate_frame)
        est_holder.pack(fill="both", expand=True, padx=6, pady=6)
        self.estimates_tree = self._tree(est_holder, [
            ("id", "ID", 45), ("job_number", "Job #", 145), ("customer_name", "Customer", 170),
            ("model", "Device", 130), ("status", "Status", 120), ("subtotal", "Subtotal", 90),
            ("tax_amount", "Tax", 80), ("total", "Total", 90), ("created_at", "Created", 150),
        ], height=5)
        inv_holder = ttk.Frame(invoice_frame)
        inv_holder.pack(fill="both", expand=True, padx=6, pady=6)
        self.invoices_tree = self._tree(inv_holder, [
            ("id", "ID", 45), ("invoice_number", "Invoice #", 225), ("job_number", "Job #", 140),
            ("customer_name", "Customer", 155), ("total", "Total", 85), ("amount_paid", "Paid", 85),
            ("balance", "Balance", 90), ("status", "Status", 110),
        ], height=5)

    # QC / Reports
    def _build_qc_reports_tab(self):
        tab = self._tab("QC & Reports")
        self._buttons(tab, [
            ("Add QC Check for Selected Job", self.add_qc_check), ("Refresh QC", self.refresh_qc),
            ("Export Jobs CSV", self.export_jobs), ("Queue Customer Message", self.queue_ready_notice),
            ("Refresh Report Summary", self.refresh_report_summary),
        ])
        panels = ttk.Panedwindow(tab, orient="vertical")
        panels.pack(fill="both", expand=True)
        qc_frame = ttk.Labelframe(panels, text="Quality-control checks")
        report_frame = ttk.Labelframe(panels, text="Operations / finance report")
        panels.add(qc_frame, weight=2)
        panels.add(report_frame, weight=1)
        qc_holder = ttk.Frame(qc_frame)
        qc_holder.pack(fill="both", expand=True, padx=6, pady=6)
        self.qc_tree = self._tree(qc_holder, [
            ("id", "ID", 50), ("job_number", "Job #", 145), ("check_name", "Check", 200),
            ("passed", "Result", 85), ("notes", "Notes", 350), ("technician_name", "Technician", 150),
            ("created_at", "Logged", 165),
        ], height=7)
        self.report_output = tk.Text(report_frame, height=8, bg="#111720", fg="#dce6f5",
                                     relief="flat", wrap="word", font=("Consolas", 10), padx=10, pady=8)
        self.report_output.pack(fill="both", expand=True, padx=6, pady=6)

    # Warranty and notification drafts
    def _build_warranty_tab(self):
        tab = self._tab("Warranty & Notices")
        self._buttons(tab, [
            ("+ Warranty Case", self.new_warranty_case),
            ("Update Warranty Status", self.update_warranty_status),
            ("+ Notification Draft", self.new_notification_draft),
            ("Refresh", self.refresh_warranty_notices),
        ])
        panels = ttk.Panedwindow(tab, orient="vertical")
        panels.pack(fill="both", expand=True)
        warranty_frame = ttk.Labelframe(panels, text="Warranty / service cases")
        notices_frame = ttk.Labelframe(panels, text="Customer notification queue (draft-only)")
        panels.add(warranty_frame, weight=1)
        panels.add(notices_frame, weight=1)
        warranty_holder = ttk.Frame(warranty_frame)
        warranty_holder.pack(fill="both", expand=True, padx=6, pady=6)
        self.warranties_tree = self._tree(warranty_holder, [
            ("id", "ID", 45), ("original_job_number", "Original Job", 140),
            ("new_job_number", "Follow-up Job", 140), ("customer_name", "Customer", 160),
            ("model", "Device", 130), ("terms", "Terms / Issue", 250),
            ("expires_at", "Expires", 105), ("status", "Status", 100),
        ], height=5)
        notice_holder = ttk.Frame(notices_frame)
        notice_holder.pack(fill="both", expand=True, padx=6, pady=6)
        self.notifications_tree = self._tree(notice_holder, [
            ("id", "ID", 45), ("job_number", "Job #", 140), ("channel", "Channel", 85),
            ("recipient", "Recipient", 150), ("message", "Message", 330),
            ("status", "Status", 90), ("created_at", "Created", 150),
        ], height=5)

    # Device tools
    def _build_device_tools_tab(self):
        tab = self._tab("Device Tools")
        ttk.Label(tab, text="Device Diagnostics & Firmware Center", font=("Segoe UI Semibold", 16)).pack(anchor="w")
        ttk.Label(tab, text="Read-only ADB/Fastboot/USB discovery and firmware package inspection. "
                            "Only official, exact-model-compatible firmware should be considered.",
                  style="Subtitle.TLabel", wraplength=1000).pack(anchor="w", pady=(3, 10))
        panel = ttk.Frame(tab, style="Panel.TFrame", padding=12)
        panel.pack(fill="x", pady=(0, 10))
        ttk.Label(panel, text="FIRMWARE WRITING: DISABLED", background="#1a2230",
                  foreground="#ffcc80", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(panel, text="This build does not flash partitions, bypass device security, or guarantee firmware authenticity.",
                  background="#1a2230", foreground="#a7b5c8").pack(anchor="w", pady=(4, 0))
        self._buttons(tab, [
            ("Run Device Diagnostics", self.run_diagnostics), ("Inspect Firmware Package", self.choose_firmware),
            ("Save Tool Report", self.save_tool_report), ("Clear Output", self.clear_tool_output),
        ])
        self.tools_output = tk.Text(tab, bg="#0b0f15", fg="#dce6f5", insertbackground="white",
                                    relief="flat", wrap="word", font=("Consolas", 10), padx=12, pady=12)
        self.tools_output.pack(fill="both", expand=True)
        self._tool_log("Tools ready. Connect a device with a known-good USB cable; ensure official drivers are installed.")
        self._tool_log("For Android-state detection, install Android Platform Tools. Download Mode may not appear in ADB.")

    # Settings / audit
    def _build_settings_tab(self):
        tab = self._tab("Settings & Audit")
        panels = ttk.Panedwindow(tab, orient="horizontal")
        panels.pack(fill="both", expand=True)
        settings_frame = ttk.Labelframe(panels, text="Shop / owner settings")
        audit_frame = ttk.Labelframe(panels, text="Local audit trail")
        panels.add(settings_frame, weight=1)
        panels.add(audit_frame, weight=2)
        self.settings_vars = {}
        setting_fields = [
            ("shop_name", "Business Name"), ("shop_address", "Address"),
            ("shop_phone", "Phone"), ("shop_email", "Email"),
            ("currency", "Currency"), ("tax_rate", "Default Tax Rate (%)"),
        ]
        for index, (key, label) in enumerate(setting_fields):
            ttk.Label(settings_frame, text=label).grid(row=index, column=0, sticky="w", padx=10, pady=6)
            var = tk.StringVar(value=self.db.get_setting(key))
            self.settings_vars[key] = var
            ttk.Entry(settings_frame, textvariable=var, width=32).grid(
                row=index, column=1, sticky="ew", padx=10, pady=6
            )
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).grid(
            row=len(setting_fields), column=0, sticky="w", padx=10, pady=10
        )
        ttk.Button(settings_frame, text="Back Up Database", command=self.backup_database).grid(
            row=len(setting_fields), column=1, sticky="e", padx=10, pady=10
        )
        ttk.Button(settings_frame, text="Check Database Health", command=self.check_database).grid(
            row=len(setting_fields) + 1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10)
        )
        audit_bar = ttk.Frame(audit_frame)
        audit_bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(audit_bar, text="Refresh Audit", command=self.refresh_audit).pack(side="left")
        audit_holder = ttk.Frame(audit_frame)
        audit_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.audit_tree = self._tree(audit_holder, [
            ("id", "ID", 55), ("created_at", "When", 165), ("user_name", "User", 100),
            ("action", "Action", 110), ("entity_type", "Record Type", 120),
            ("entity_id", "Record ID", 85), ("details", "Details", 280),
        ], height=16)
        ttk.Label(settings_frame, text="Local single-user owner profile. Multi-user logins, external SMS/email delivery, "
                                       "payment-gateway integration and a customer portal are not connected in this build.",
                  wraplength=360, foreground="#a7b5c8").grid(
            row=len(setting_fields) + 2, column=0, columnspan=2, sticky="w", padx=10, pady=12
        )

    # Refresh helpers
    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_customers()
        self.refresh_devices()
        self.refresh_jobs()
        self.refresh_inventory()
        self.refresh_technicians()
        self.refresh_billing()
        self.refresh_qc()
        self.refresh_warranty_notices()
        self.refresh_audit()
        self.refresh_report_summary()

    def refresh_dashboard(self):
        summary = self.db.dashboard_summary()
        for key, variable in self.summary_vars.items():
            value = summary[key]
            variable.set(self._money(value) if key in ("payments_today", "outstanding_balance") else str(value))
        rows = self.db.list_jobs()[:30]
        self._populate(self.dashboard_jobs_tree, rows,
                       lambda row, key: self._money(row.get(key)) if key in ("subtotal", "total") else row.get(key, ""))

    def refresh_customers(self):
        self._populate(self.customers_tree, self.db.list_customers(), lambda r, k: r.get(k, ""))

    def refresh_devices(self):
        self._populate(self.devices_tree, self.db.list_devices(), lambda r, k: r.get(k, ""))

    def refresh_jobs(self):
        self._populate(self.jobs_tree, self.db.list_jobs(), lambda r, k: r.get(k, ""))

    def refresh_inventory(self, low_stock=False):
        rows = self.db.list_parts(low_stock_only=low_stock)
        self._populate(self.inventory_tree, rows,
                       lambda r, k: self._money(r.get(k)) if k in ("unit_cost", "retail_price") else r.get(k, ""))

    def refresh_technicians(self):
        rows = self.db.list_technicians(active_only=False)
        self._populate(self.technicians_tree, rows,
                       lambda r, k: ("Yes" if r.get(k) else "No") if k == "active" else r.get(k, ""))

    def refresh_billing(self):
        self._populate(self.estimates_tree, self.db.list_estimates(), lambda r, k:
                       self._money(r.get(k)) if k in ("subtotal", "tax_amount", "total") else r.get(k, ""))
        invoices = self.db.list_invoices()
        self._populate(self.invoices_tree, invoices, lambda r, k:
                       self._money(r.get("total", 0) - r.get("amount_paid", 0)) if k == "balance"
                       else self._money(r.get(k)) if k in ("total", "amount_paid") else r.get(k, ""))

    def refresh_qc(self):
        self._populate(self.qc_tree, self.db.list_qc_checks(),
                       lambda r, k: ("PASS" if r.get(k) else "FAIL") if k == "passed" else r.get(k, ""))

    def refresh_audit(self):
        self._populate(self.audit_tree, self.db.list_audit(),
                       lambda r, k: r.get(k, ""))

    def refresh_warranty_notices(self):
        self._populate(self.warranties_tree, self.db.list_warranty_cases(),
                       lambda r, k: r.get(k, ""))
        self._populate(self.notifications_tree, self.db.list_notifications(),
                       lambda r, k: r.get(k, ""))

    def refresh_report_summary(self):
        summary = self.db.dashboard_summary()
        jobs = self.db.list_jobs()
        invoices = self.db.list_invoices()
        by_status = {}
        for job in jobs:
            by_status[job["status"]] = by_status.get(job["status"], 0) + 1
        total_invoiced = sum(float(x["total"]) for x in invoices if x["status"] != "Void")
        total_paid = sum(float(x["amount_paid"]) for x in invoices if x["status"] != "Void")
        report = [
            "J-ROC AI MOBILE REPAIR — CURRENT OWNER SUMMARY",
            "=" * 54,
            f"Shop: {self.db.get_setting('shop_name', APP_NAME)}",
            f"Open jobs: {summary['open_jobs']}",
            f"Waiting for customer approval: {summary['waiting_approval']}",
            f"Jobs in QC: {summary['qc_pending']}",
            f"Low-stock parts: {summary['low_stock']}",
            f"Payments recorded today: {self._money(summary['payments_today'])}",
            f"Outstanding balance: {self._money(summary['outstanding_balance'])}",
            f"Invoiced (all non-void invoices): {self._money(total_invoiced)}",
            f"Paid against invoices: {self._money(total_paid)}",
            "",
            "Jobs by status:",
        ]
        report.extend([f"  {status}: {count}" for status, count in sorted(by_status.items())] or ["  No jobs yet."])
        report.extend(["", "Operational flow:", "Customer → Device → Job → Diagnostics → Estimate → Approval → Parts",
                       "→ Repair → QC → Invoice/Payment → Device Return → Reporting"])
        self.report_output.configure(state="normal")
        self.report_output.delete("1.0", "end")
        self.report_output.insert("end", "\n".join(report))
        self.report_output.configure(state="disabled")

    # Customer and device entry
    def new_customer(self):
        values = self._form("Add Customer", [
            {"key": "name", "label": "Customer / business name", "required": True},
            {"key": "phone", "label": "Phone"},
            {"key": "email", "label": "Email"},
            {"key": "address", "label": "Address"},
            {"key": "notes", "label": "Private service notes"},
            {"key": "preferences", "label": "Communication preferences"},
        ])
        if values:
            self._run_action(lambda: f"Created customer record #{self.db.add_customer(**values)}")

    def new_device(self):
        customers = self._customer_choices()
        if not customers:
            messagebox.showinfo("Customer required", "Create a customer before registering a device.", parent=self)
            self.notebook.select(1)
            return
        values = self._form("Register Device", [
            {"key": "customer", "label": "Customer", "choices": customers, "required": True},
            {"key": "device_type", "label": "Device type",
             "choices": ["Phone", "Tablet", "Laptop"],
             "default": "Phone", "required": True},
            {"key": "manufacturer", "label": "Manufacturer",
             "choices": ["Apple", "Samsung"], "default": "Apple", "required": True},
            {"key": "model", "label": "Model", "required": True},
            {"key": "serial_number", "label": "Serial number"},
            {"key": "imei", "label": "IMEI (when appropriate)"},
            {"key": "condition_notes", "label": "Condition / existing damage"},
            {"key": "reported_issue", "label": "Customer-reported issue"},
            {"key": "accessories", "label": "Accessories received"},
        ])
        if values:
            customer_id = _choice_id(values.pop("customer"))
            if customer_id is not None:
                self._run_action(lambda: f"Registered device #{self.db.add_device(customer_id, **values)}")

    def new_job(self):
        customers = self._customer_choices()
        devices = self._device_choices()
        if not customers or not devices:
            messagebox.showinfo("Intake needs customer and device",
                                "Create a customer and register their device before opening a repair job.", parent=self)
            return
        technicians = self._technician_choices()
        values = self._form("Create Repair Job", [
            {"key": "customer", "label": "Customer", "choices": customers, "required": True},
            {"key": "device", "label": "Device", "choices": devices, "required": True},
            {"key": "complaint", "label": "Reported issue / complaint", "required": True},
            {"key": "intake_notes", "label": "Intake / condition notes"},
            {"key": "priority", "label": "Priority", "choices": list(PRIORITIES), "default": "Normal"},
            {"key": "technician", "label": "Assigned technician", "choices": technicians, "default": "Unassigned"},
        ])
        if values:
            customer_id = _choice_id(values.pop("customer"))
            device_id = _choice_id(values.pop("device"))
            technician_id = _choice_id(values.pop("technician"))
            self._run_action(lambda: "Created repair job #" + str(self.db.create_job(customer_id, device_id, values["complaint"], values["intake_notes"], values["priority"], technician_id)))

    def _job_action_required(self):
        job_id = self._selected_job_id()
        return job_id

    def update_job_status(self):
        job_id = self._job_action_required()
        if job_id is None:
            return
        values = self._form("Update Job Status", [
            {"key": "status", "label": "New status", "choices": list(JOB_STATUSES), "required": True}
        ])
        if values:
            self._run_action(lambda: (self.db.update_job_status(job_id, values["status"]),
                                      f"Job #{job_id} status changed to {values['status']}")[1])

    def assign_job(self):
        job_id = self._job_action_required()
        if job_id is None:
            return
        choices = self._technician_choices()
        values = self._form("Assign Technician", [
            {"key": "technician", "label": "Technician", "choices": choices, "required": True}
        ])
        if values:
            technician_id = _choice_id(values["technician"])
            self._run_action(lambda: (self.db.assign_technician(job_id, technician_id),
                                      f"Updated technician assignment for job #{job_id}")[1])

    def add_diagnostic(self):
        job_id = self._job_action_required()
        if job_id is None:
            return
        values = self._form("Record Diagnostic", [
            {"key": "category", "label": "Category",
             "choices": ["Visual", "Power / Charging", "Battery", "Display / Touch", "Audio",
                         "Camera", "Connectivity", "Software", "Storage / Data", "Board-level", "Other"],
             "required": True},
            {"key": "findings", "label": "Findings / evidence", "required": True},
            {"key": "next_action", "label": "Suggested next action"},
            {"key": "technician", "label": "Technician", "choices": self._technician_choices(),
             "default": "Unassigned"},
        ])
        if values:
            technician_id = _choice_id(values.pop("technician"))
            self._run_action(lambda: "Recorded diagnostic #" + str(self.db.add_diagnostic(job_id, values["category"], values["findings"], values["next_action"], technician_id)))

    def add_repair_log(self):
        job_id = self._job_action_required()
        if job_id is None:
            return
        values = self._form("Log Repair Work", [
            {"key": "description", "label": "Work performed", "required": True},
            {"key": "duration", "label": "Duration (minutes)", "default": "0", "required": True},
            {"key": "technician", "label": "Technician", "choices": self._technician_choices(),
             "default": "Unassigned"},
        ])
        if values:
            technician_id = _choice_id(values.pop("technician"))
            try:
                duration = int(values["duration"])
            except ValueError:
                messagebox.showerror("Invalid duration", "Duration must be a whole number of minutes.", parent=self)
                return
            self._run_action(lambda: "Recorded repair log #" + str(self.db.add_repair_log(job_id, values["description"], duration, technician_id)))

    # Inventory
    def new_part(self):
        values = self._form("Add Inventory Part", [
            {"key": "sku", "label": "SKU / part number", "required": True},
            {"key": "name", "label": "Part name", "required": True},
            {"key": "category", "label": "Category", "default": "Mobile phone parts"},
            {"key": "quantity", "label": "Opening quantity", "default": "0", "required": True},
            {"key": "min_quantity", "label": "Low-stock threshold", "default": "1", "required": True},
            {"key": "unit_cost", "label": "Unit cost", "default": "0", "required": True},
            {"key": "retail_price", "label": "Retail price", "default": "0", "required": True},
            {"key": "supplier", "label": "Supplier"},
        ])
        if not values:
            return
        try:
            quantity = int(values.pop("quantity"))
            min_quantity = int(values.pop("min_quantity"))
            unit_cost = float(values.pop("unit_cost"))
            retail_price = float(values.pop("retail_price"))
        except ValueError:
            messagebox.showerror("Invalid stock or price", "Quantities must be whole numbers and prices numeric.", parent=self)
            return
        self._run_action(lambda: "Added part #" + str(self.db.add_part(values["sku"], values["name"], quantity, min_quantity, unit_cost, retail_price, values["category"], values["supplier"])))

    def adjust_stock(self):
        part_id = self._selected_id(self.inventory_tree)
        if part_id is None:
            return
        values = self._form("Adjust Inventory", [
            {"key": "delta", "label": "Quantity change (+/-)", "required": True},
            {"key": "reason", "label": "Reason / reference", "required": True},
        ])
        if not values:
            return
        try:
            delta = int(values["delta"])
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity change must be a whole number.", parent=self)
            return
        self._run_action(lambda: (self.db.adjust_inventory(part_id, delta, values["reason"]),
                                  f"Adjusted part #{part_id} stock by {delta}")[1])

    def consume_part(self):
        job_id = self._selected_job_id()
        if job_id is None:
            return
        parts = self._part_choices()
        if not parts:
            messagebox.showinfo("Inventory empty", "Add inventory parts first.", parent=self)
            return
        values = self._form("Use Part on Repair Job", [
            {"key": "part", "label": "Part", "choices": parts, "required": True},
            {"key": "quantity", "label": "Quantity used", "default": "1", "required": True},
        ])
        if not values:
            return
        part_id = _choice_id(values["part"])
        try:
            quantity = int(values["quantity"])
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a whole number.", parent=self)
            return
        self._run_action(lambda: (self.db.consume_part(job_id, part_id, quantity),
                                  f"Consumed {quantity} part(s) against job #{job_id}")[1])

    def show_low_stock(self):
        self.refresh_inventory(low_stock=True)
        self.notebook.select(4)

    def show_inventory_history(self):
        rows = self.db.inventory_history()
        if not rows:
            messagebox.showinfo("Inventory history", "No stock movements have been recorded.", parent=self)
            return
        lines = [
            f"{row['created_at']} | {row['sku']} {row['part_name']} | {row['delta']:+d} | "
            f"{row['reason']} | Job {row.get('job_number') or '-'}"
            for row in rows
        ]
        self._show_text_window("Inventory Movement History", "\n".join(lines))

    # Technicians
    def new_technician(self):
        values = self._form("Add Technician", [
            {"key": "name", "label": "Name", "required": True},
            {"key": "role", "label": "Role", "choices": ["Technician", "Manager", "Front Desk", "Owner"],
             "default": "Technician"},
            {"key": "phone", "label": "Phone"},
            {"key": "email", "label": "Email"},
        ])
        if values:
            self._run_action(lambda: "Created technician #" + str(self.db.add_technician(values["name"], values["phone"], values["email"], values["role"])))

    # Estimates and billing
    def new_estimate(self):
        jobs = self._job_choices()
        if not jobs:
            messagebox.showinfo("No repair jobs", "Create a repair job before making an estimate.", parent=self)
            return
        values = self._form("Create Estimate", [
            {"key": "job", "label": "Repair job", "choices": jobs, "required": True},
            {"key": "description", "label": "Line item", "default": "Diagnostic / repair service", "required": True},
            {"key": "quantity", "label": "Quantity", "default": "1", "required": True},
            {"key": "unit_price", "label": "Unit price", "default": "0", "required": True},
            {"key": "tax_rate", "label": "Tax rate (%)", "default": self.db.get_setting("tax_rate", "0"), "required": True},
        ])
        if not values:
            return
        try:
            job_id = _choice_id(values["job"])
            quantity = float(values["quantity"])
            unit_price = float(values["unit_price"])
            tax_rate = float(values["tax_rate"])
        except (ValueError, TypeError):
            messagebox.showerror("Invalid estimate", "Quantity and prices must be numeric.", parent=self)
            return
        self._run_action(lambda: "Created estimate #" + str(self.db.create_estimate(job_id, [{"description": values["description"], "quantity": quantity, "unit_price": unit_price}], tax_rate)))

    def _selected_estimate_id(self):
        return self._selected_id(self.estimates_tree)

    def approve_estimate(self):
        estimate_id = self._selected_estimate_id()
        if estimate_id is not None:
            self._run_action(lambda: (self.db.set_estimate_status(estimate_id, "Approved"),
                                      f"Approved estimate #{estimate_id}")[1])

    def decline_estimate(self):
        estimate_id = self._selected_estimate_id()
        if estimate_id is not None:
            if not messagebox.askyesno("Decline estimate", "Mark the selected estimate as declined?", parent=self):
                return
            self._run_action(lambda: (self.db.set_estimate_status(estimate_id, "Declined"),
                                      f"Declined estimate #{estimate_id}")[1])

    def create_invoice(self):
        jobs = self._job_choices()
        if not jobs:
            return
        values = self._form("Create Invoice", [
            {"key": "job", "label": "Repair job with an approved estimate", "choices": jobs, "required": True}
        ])
        if values:
            job_id = _choice_id(values["job"])
            self._run_action(lambda: f"Created invoice #{self.db.create_invoice(job_id)}")

    def record_payment(self):
        invoice_id = self._selected_id(self.invoices_tree)
        if invoice_id is None:
            return
        invoice = next((x for x in self.db.list_invoices() if x["id"] == invoice_id), None)
        if invoice is None:
            return
        balance = round(invoice["total"] - invoice["amount_paid"], 2)
        values = self._form("Record Invoice Payment", [
            {"key": "amount", "label": f"Amount due {self._money(balance)}", "default": str(balance), "required": True},
            {"key": "method", "label": "Payment method", "choices": ["Cash", "Card", "Bank transfer", "Other"],
             "default": "Cash"},
            {"key": "reference", "label": "Receipt / reference"},
        ])
        if not values:
            return
        try:
            amount = float(values["amount"])
        except ValueError:
            messagebox.showerror("Invalid payment", "Payment amount must be numeric.", parent=self)
            return
        self._run_action(lambda: (self.db.record_payment(invoice_id, amount, values["method"], values["reference"]),
                                  f"Recorded payment of {self._money(amount)} for invoice #{invoice_id}")[1])

    # Warranty / notification queue
    def new_warranty_case(self):
        jobs = self._job_choices()
        if not jobs:
            messagebox.showinfo("No repair jobs", "Create a repair job before opening a warranty case.", parent=self)
            return
        followups = ["None"] + jobs
        values = self._form("Create Warranty / Service Case", [
            {"key": "original_job", "label": "Original repair job", "choices": jobs, "required": True},
            {"key": "new_job", "label": "Linked follow-up job (optional)", "choices": followups, "default": "None"},
            {"key": "terms", "label": "Warranty terms or reported issue", "required": True},
            {"key": "expires_at", "label": "Expiry date (optional, YYYY-MM-DD)"},
        ])
        if values:
            original_id = _choice_id(values["original_job"])
            followup_id = _choice_id(values["new_job"])
            self._run_action(lambda: "Created warranty case #" + str(
                self.db.create_warranty_case(original_id, values["terms"], values["expires_at"], followup_id)
            ))

    def update_warranty_status(self):
        warranty_id = self._selected_id(self.warranties_tree)
        if warranty_id is None:
            return
        values = self._form("Update Warranty Status", [
            {"key": "status", "label": "Status",
             "choices": ["Open", "Approved", "Denied", "Expired", "Closed"], "required": True}
        ])
        if values:
            self._run_action(lambda: (self.db.update_warranty_status(warranty_id, values["status"]),
                                      "Updated warranty case #" + str(warranty_id) + " to " + values["status"])[1])

    def new_notification_draft(self):
        jobs = self._job_choices()
        if not jobs:
            messagebox.showinfo("No repair jobs", "Create a repair job before drafting a customer notice.", parent=self)
            return
        values = self._form("Create Customer Notification Draft", [
            {"key": "job", "label": "Repair job", "choices": jobs, "required": True},
            {"key": "channel", "label": "Channel", "choices": ["Manual", "Email", "SMS"], "default": "Manual"},
            {"key": "recipient", "label": "Recipient"},
            {"key": "message", "label": "Message", "default": "Your repair has a status update. Please contact our shop.", "required": True},
        ])
        if values:
            job_id = _choice_id(values["job"])
            self._run_action(lambda: "Saved notification draft #" + str(
                self.db.queue_notification(job_id, values["channel"], values["recipient"], values["message"])
            ) + ". No message was sent.")

    # QC and customer notices
    def add_qc_check(self):
        job_id = self._selected_job_id()
        if job_id is None:
            return
        values = self._form("Record Quality-Control Check", [
            {"key": "check_name", "label": "Test", "choices": [
                "Power-on / boot", "Charging", "Battery", "Display / touch", "Cameras",
                "Microphones / speakers", "Buttons", "Wi-Fi / Bluetooth", "Cellular / SIM",
                "Data connection", "Biometrics", "Physical assembly", "Customer-specific test", "Other"
            ], "required": True},
            {"key": "result", "label": "Result", "choices": ["PASS", "FAIL"], "required": True},
            {"key": "notes", "label": "Result notes / evidence"},
            {"key": "technician", "label": "Technician", "choices": self._technician_choices(),
             "default": "Unassigned"},
        ])
        if values:
            tech_id = _choice_id(values["technician"])
            self._run_action(lambda: "Logged QC check #" + str(self.db.add_qc_check(job_id, values["check_name"], values["result"] == "PASS", values["notes"], tech_id)))

    def queue_ready_notice(self):
        job_id = self._selected_job_id()
        if job_id is None:
            return
        job = next((row for row in self.db.list_jobs() if row["id"] == job_id), None)
        if not job:
            return
        message = f"Your device repair {job['job_number']} is marked for follow-up. Please contact the shop for details."
        values = self._form("Queue Customer Notice (Draft Only)", [
            {"key": "channel", "label": "Channel", "choices": ["Manual", "Email", "SMS"], "default": "Manual"},
            {"key": "recipient", "label": "Recipient", "default": job.get("customer_phone", "")},
            {"key": "message", "label": "Message", "default": message, "required": True},
        ])
        if values:
            self._run_action(lambda: "Saved customer notification draft #" + str(self.db.queue_notification(job_id, values["channel"], values["recipient"], values["message"])) + ". No message was sent.")

    def export_jobs(self):
        path = filedialog.asksaveasfilename(
            title="Export repair jobs", defaultextension=".csv",
            initialfile=f"J-Roc-AI-Mobile-Repair-Jobs-{datetime.now():%Y%m%d}.csv",
            filetypes=[("CSV file", "*.csv")], parent=self
        )
        if path:
            self._run_action(lambda: f"Exported repair jobs to {self.db.export_jobs_csv(path)}", refresh=False)

    # Device tools
    def run_diagnostics(self):
        self._tool_log("Running read-only device discovery...")
        def work():
            try:
                result = collect_diagnostics()
                self.after(0, lambda result=result: self._tool_log(format_report(result)))
            except Exception as exc:
                logging.exception("Device diagnostics failed")
                error = str(exc)
                self.after(0, lambda error=error: self._tool_log("Diagnostics failed: " + error))
        threading.Thread(target=work, daemon=True).start()

    def choose_firmware(self):
        name = filedialog.askopenfilename(
            title="Select official firmware package for inspection",
            filetypes=[("Firmware packages", "*.tar *.tar.md5 *.zip"), ("All files", "*.*")],
            parent=self,
        )
        if name:
            self._tool_log(f"Inspecting package: {Path(name).name}")
            def work():
                try:
                    result = inspect_firmware(name)
                    self.after(0, lambda result=result: self._tool_log(format_report(result)))
                except Exception as exc:
                    logging.exception("Firmware inspection failed")
                    error = str(exc)
                    self.after(0, lambda error=error: self._tool_log("Firmware inspection failed: " + error))
            threading.Thread(target=work, daemon=True).start()

    def _tool_log(self, text):
        if not hasattr(self, "tools_output"):
            return
        logging.info(text)
        self.tools_output.configure(state="normal")
        self.tools_output.insert("end", "[" + datetime.now().strftime("%H:%M:%S") + "] " + str(text) + "\n")
        self.tools_output.see("end")
        self.tools_output.configure(state="disabled")

    def clear_tool_output(self):
        self.tools_output.configure(state="normal")
        self.tools_output.delete("1.0", "end")
        self.tools_output.configure(state="disabled")

    def save_tool_report(self):
        path = filedialog.asksaveasfilename(
            title="Save device-service report", defaultextension=".txt",
            initialfile=f"J-Roc-AI-Mobile-Repair-Report-{datetime.now():%Y%m%d-%H%M%S}.txt",
            filetypes=[("Text report", "*.txt"), ("JSON report", "*.json")], parent=self,
        )
        if path:
            text = self.tools_output.get("1.0", "end")
            try:
                Path(path).write_text(text, encoding="utf-8")
                self._tool_log("Saved report to " + path)
            except OSError as exc:
                messagebox.showerror("Save report failed", str(exc), parent=self)

    # Settings and backups
    def save_settings(self):
        try:
            tax = float(self.settings_vars["tax_rate"].get())
            if tax < 0 or tax > 100:
                raise ValueError("Tax rate must be between 0 and 100.")
            for key, variable in self.settings_vars.items():
                self.db.set_setting(key, variable.get().strip())
            messagebox.showinfo("Settings saved", "Shop identity and default tax settings were saved locally.", parent=self)
            self.refresh_all()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc), parent=self)

    def backup_database(self):
        path = filedialog.asksaveasfilename(
            title="Back up local repair database", defaultextension=".sqlite3",
            initialfile=f"J-Roc-AI-Mobile-Repair-Backup-{datetime.now():%Y%m%d-%H%M%S}.sqlite3",
            filetypes=[("SQLite database backup", "*.sqlite3")], parent=self,
        )
        if path:
            try:
                self.db.backup_database(path)
                messagebox.showinfo("Backup created", f"Database backup saved to:\n{path}", parent=self)
            except Exception as exc:
                messagebox.showerror("Backup failed", str(exc), parent=self)

    def check_database(self):
        result = self.db.integrity_check()
        messagebox.showinfo("Database Health", "SQLite integrity check: " + result, parent=self)
        self._run_action(lambda: "Database integrity_check returned: " + result, refresh=False)

    def _show_text_window(self, title, content):
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("900x560")
        viewer = tk.Text(window, wrap="word", font=("Consolas", 10))
        viewer.pack(fill="both", expand=True, padx=10, pady=10)
        viewer.insert("1.0", content)
        viewer.configure(state="disabled")


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        logging.exception("Fatal startup error")
        raise
