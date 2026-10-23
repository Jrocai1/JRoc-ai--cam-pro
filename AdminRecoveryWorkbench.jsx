import { useMemo, useState } from "react";
import { ClipboardCheck, Download, Plus, ShieldCheck, Trash2 } from "lucide-react";

const INITIAL_CHECKS = [
  { id: "ownership", label: "Proof of ownership reviewed" },
  { id: "consent", label: "Written customer authorization recorded" },
  { id: "backup", label: "Data-loss and backup warning explained" },
  { id: "route", label: "Official manufacturer/carrier route selected" },
  { id: "result", label: "Final device state verified with customer/technician" }
];

/**
 * Extensible, client-side case workbench.
 * This deliberately does not execute device commands, remove FRP, or claim remote audit security.
 * Replace the storage and service adapters only after adding authenticated server-side authorization.
 */
export default function AdminRecoveryWorkbench() {
  const [caseData, setCaseData] = useState({
    caseId: "",
    technician: "",
    brand: "Samsung",
    deviceType: "Phone",
    model: "",
    identifierLast4: "",
    customerConsent: false,
    operation: "Official account recovery",
    notes: ""
  });
  const [checks, setChecks] = useState({});
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("Open");

  const completed = useMemo(() => INITIAL_CHECKS.filter((item) => checks[item.id]).length, [checks]);
  const ready = completed === INITIAL_CHECKS.length && caseData.customerConsent && caseData.caseId.trim() && caseData.technician.trim();

  function addEvent(action, detail) {
    setEvents((current) => [...current, {
      at: new Date().toISOString(),
      action,
      detail,
      actor: caseData.technician.trim() || "Unassigned technician"
    }]);
  }

  function update(field, value) {
    setCaseData((current) => ({ ...current, [field]: value }));
  }

  function toggleCheck(id, value) {
    setChecks((current) => ({ ...current, [id]: value }));
    const label = INITIAL_CHECKS.find((item) => item.id === id)?.label || id;
    addEvent(value ? "Checklist completed" : "Checklist reopened", label);
  }

  function saveCase() {
    if (!caseData.caseId.trim() || !caseData.technician.trim()) {
      window.alert("Enter a case ID and technician name before recording a case event.");
      return;
    }
    addEvent("Case snapshot recorded", "Status: " + status + "; operation: " + caseData.operation);
    window.alert("Case event added to this browser session. Export the JSON report to retain it; this is not a server-side audit log.");
  }

  function exportReport() {
    const report = {
      schemaVersion: "1.0.0",
      product: "J-ROC AI Universal Repair Suite PRO",
      reportType: "authorized-recovery-case",
      generatedAt: new Date().toISOString(),
      securityNotice: "Client-generated report. It is not cryptographically signed and does not prove ownership or successful device modification.",
      case: { ...caseData, identifierLast4: caseData.identifierLast4.replace(/[^0-9A-Za-z]/g, "").slice(-4) },
      checklist: INITIAL_CHECKS.map((item) => ({ ...item, complete: Boolean(checks[item.id]) })),
      completion: { checksComplete: completed, checksTotal: INITIAL_CHECKS.length, readyForOfficialWorkflow: Boolean(ready) },
      status,
      events
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = (caseData.caseId.trim().replace(/[^a-zA-Z0-9_-]/g, "-") || "jroc-recovery-case") + ".json";
    anchor.click();
    URL.revokeObjectURL(url);
    addEvent("Report exported", "A JSON case report was downloaded locally.");
  }

  function resetCase() {
    if (!window.confirm("Clear this workbench session? Export the case report first if you need a copy.")) return;
    setCaseData({ caseId: "", technician: "", brand: "Samsung", deviceType: "Phone", model: "", identifierLast4: "", customerConsent: false, operation: "Official account recovery", notes: "" });
    setChecks({});
    setEvents([]);
    setStatus("Open");
  }

  return (
    <div className="animate-fade-in mx-auto max-w-5xl space-y-6">
      <div>
        <p className="eyebrow">Extensible technician workspace</p>
        <h1 className="mt-1 text-3xl font-semibold text-white">Admin Recovery Workbench</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">A working case checklist and JSON report exporter for authorized Apple/Samsung recovery. The code is intentionally open for your own adapters and workflows. This page does not bypass FRP or Activation Lock, run device commands, or authenticate an administrator.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel-card"><p className="text-xs uppercase tracking-wider text-slate-500">Checklist</p><p className="mt-2 text-2xl font-semibold text-white">{completed}/{INITIAL_CHECKS.length}</p><p className="mt-1 text-xs text-slate-400">Required steps recorded</p></div>
        <div className="panel-card"><p className="text-xs uppercase tracking-wider text-slate-500">Case status</p><p className="mt-2 text-2xl font-semibold text-white">{status}</p><p className="mt-1 text-xs text-slate-400">Local workbench state</p></div>
        <div className="panel-card"><p className="text-xs uppercase tracking-wider text-slate-500">Device action</p><p className="mt-2 text-2xl font-semibold text-white">Not run</p><p className="mt-1 text-xs text-slate-400">No device command is issued here</p></div>
      </div>

      <section className="panel-card space-y-5">
        <div className="flex items-center gap-2"><ClipboardCheck className="text-mint" size={20}/><h2 className="text-lg font-semibold text-white">Case details</h2></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-slate-300">Case ID *
            <input value={caseData.caseId} onChange={(e) => update("caseId", e.target.value)} placeholder="e.g. JROC-2026-0001" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"/>
          </label>
          <label className="text-sm text-slate-300">Technician *
            <input value={caseData.technician} onChange={(e) => update("technician", e.target.value)} placeholder="Technician name or internal ID" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"/>
          </label>
          <label className="text-sm text-slate-300">Manufacturer
            <select value={caseData.brand} onChange={(e) => update("brand", e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"><option>Apple</option><option>Samsung</option></select>
          </label>
          <label className="text-sm text-slate-300">Device type
            <select value={caseData.deviceType} onChange={(e) => update("deviceType", e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"><option>Phone</option><option>Tablet</option><option>Laptop</option></select>
          </label>
          <label className="text-sm text-slate-300">Model
            <input value={caseData.model} onChange={(e) => update("model", e.target.value)} placeholder="Model / model number" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"/>
          </label>
          <label className="text-sm text-slate-300">Identifier last 4 characters only
            <input maxLength={4} value={caseData.identifierLast4} onChange={(e) => update("identifierLast4", e.target.value.replace(/[^0-9A-Za-z]/g, "").slice(-4))} placeholder="Avoid full IMEI or serial here" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 font-mono text-white"/>
          </label>
          <label className="text-sm text-slate-300 sm:col-span-2">Authorized operation
            <select value={caseData.operation} onChange={(e) => update("operation", e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white">
              <option>Official account recovery</option><option>Carrier unlock eligibility</option><option>Official firmware restore</option><option>Manufacturer-authorized service</option><option>Diagnostics / repair intake</option>
            </select>
          </label>
          <label className="flex items-start gap-3 text-sm leading-6 text-slate-300 sm:col-span-2">
            <input type="checkbox" checked={caseData.customerConsent} onChange={(e) => { update("customerConsent", e.target.checked); addEvent(e.target.checked ? "Consent recorded" : "Consent withdrawn", "Customer authorization checkbox changed."); }} className="mt-1 h-4 w-4 accent-emerald-400"/>
            <span>Customer authorization has been obtained and recorded in the business's approved records. This checkbox is an operator attestation, not identity verification.</span>
          </label>
          <label className="text-sm text-slate-300 sm:col-span-2">Technician notes (do not enter passwords or device passcodes)
            <textarea value={caseData.notes} onChange={(e) => update("notes", e.target.value)} rows={3} placeholder="Record symptoms, checks performed, and official support case number…" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"/>
          </label>
        </div>
      </section>

      <section className="panel-card space-y-4">
        <div className="flex items-center gap-2"><ShieldCheck className="text-mint" size={20}/><h2 className="text-lg font-semibold text-white">Authorized recovery checklist</h2></div>
        {INITIAL_CHECKS.map((item) => <label key={item.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-ink/40 p-3 text-sm leading-6 text-slate-300">
          <input type="checkbox" checked={Boolean(checks[item.id])} onChange={(e) => toggleCheck(item.id, e.target.checked)} className="mt-1 h-4 w-4 accent-emerald-400"/>
          <span>{item.label}</span>
        </label>)}
        <label className="block max-w-xs text-sm text-slate-300">Case status
          <select value={status} onChange={(e) => { setStatus(e.target.value); addEvent("Status changed", e.target.value); }} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white"><option>Open</option><option>Awaiting owner</option><option>Awaiting manufacturer</option><option>In repair</option><option>Resolved</option><option>Escalated</option></select>
        </label>
        <div className="rounded-xl border border-line bg-ink/50 p-4 text-sm leading-6 text-slate-300">
          <strong className="text-white">{ready ? "Checklist complete." : "Checklist incomplete."}</strong> {ready ? "This case is ready for an official workflow handoff. No device action has been performed." : "Complete all five checks, enter a case ID and technician, and record consent before marking the case ready."}
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={saveCase} className="btn-primary"><Plus size={16}/> Record case event</button>
          <button type="button" onClick={exportReport} className="btn-secondary"><Download size={16}/> Export JSON report</button>
          <button type="button" onClick={resetCase} className="btn-secondary"><Trash2 size={16}/> Clear session</button>
        </div>
      </section>

      <section className="panel-card space-y-3">
        <h2 className="text-lg font-semibold text-white">Session event log</h2>
        {events.length === 0 ? <p className="text-sm text-slate-400">No events yet. Checklist and status changes appear here during this browser session.</p> : [...events].reverse().map((event, index) => <div key={event.at + event.action + index} className="border-b border-line py-3 last:border-0"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-medium text-white">{event.action}</span><time className="text-xs text-slate-500">{new Date(event.at).toLocaleString()}</time></div><p className="mt-1 text-sm text-slate-400">{event.detail}</p><p className="mt-1 text-xs text-slate-500">Actor: {event.actor}</p></div>)}
      </section>
      <p className="text-xs leading-5 text-slate-500">Developer note: this workbench keeps data in React memory only. Exported JSON is not a secure, immutable, server-side audit record. Add authenticated staff roles, server validation, encrypted persistence, retention policy, and append-only audit storage before multi-user production use.</p>
    </div>
  );
}
