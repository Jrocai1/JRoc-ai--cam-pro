import { useCallback, useEffect, useState } from "react";
import { Activity, Cable, CircleAlert, ClipboardList, RefreshCw, Server, ShieldCheck, Wrench } from "lucide-react";

const API_BASE = (import.meta.env.VITE_CAM_API_BASE_URL || "http://127.0.0.1:8787").replace(/\/$/, "");
const STATUSES = ["open", "paused", "completed", "cancelled"];

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    cache: "no-store"
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Local CAM API returned HTTP ${response.status}`);
  return body;
}

function Panel({ title, icon: Icon, children, action }) {
  return <section className="panel-card">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-white"><Icon size={18} className="text-mint" />{title}</h2>
      {action}
    </div>
    {children}
  </section>;
}

export default function BenchDashboard() {
  const [connection, setConnection] = useState({ loading: true, error: "", status: null });
  const [devices, setDevices] = useState(null);
  const [diagnostics, setDiagnostics] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ customer_reference: "", device_make: "Samsung", device_model: "", notes: "" });

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const status = await api("/api/status");
      setConnection({ loading: false, error: "", status });
      const [sessionData, auditData] = await Promise.all([api("/api/sessions"), api("/api/audit")]);
      setSessions(sessionData.sessions || []);
      setAudit(auditData.events || []);
    } catch (err) {
      setConnection({ loading: false, error: err.message, status: null });
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function scanDevices() {
    setError("");
    try {
      const [inventory, report] = await Promise.all([api("/api/devices"), api("/api/diagnostics")]);
      setDevices(inventory);
      setDiagnostics(report);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createSession(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/sessions", { method: "POST", body: JSON.stringify(form) });
      setForm({ customer_reference: "", device_make: "Samsung", device_model: "", notes: "" });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeStatus(session, status) {
    setError("");
    try {
      await api(`/api/sessions/${session.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  const mode = connection.status?.mode;
  return <div className="animate-fade-in space-y-6">
    <div className="relative overflow-hidden rounded-[28px] border border-line bg-gradient-to-br from-[#202e41] via-[#182536] to-[#14202c] p-6 sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="eyebrow">Local Windows repair bench</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">CAM PRO Bench Console</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">This screen reads the Python bench API on this PC. Device inventory and diagnostics are read-only; no device-changing commands are exposed.</p>
        </div>
        <div className={`rounded-2xl border p-3 ${connection.status ? "border-mint/25 bg-mint/10 text-mint" : "border-amber-300/25 bg-amber-300/10 text-amber-200"}`}>
          <Server size={24} />
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className={`rounded-full border px-3 py-1.5 text-xs ${connection.status ? "border-mint/25 text-mint" : "border-amber-300/25 text-amber-200"}`}>
          {connection.loading ? "Connecting…" : connection.status ? `API online · ${mode === "mock" ? "SIMULATION MODE" : "READ-ONLY MODE"}` : "Local API offline"}
        </span>
        <span className="text-xs text-slate-400">{API_BASE}</span>
        <button className="btn-secondary !px-3 !py-2 text-xs" onClick={refresh} disabled={loading}><RefreshCw size={14} /> Refresh records</button>
      </div>
    </div>

    {error && <div role="alert" className="flex gap-3 rounded-2xl border border-rose-400/25 bg-rose-400/5 p-4 text-sm text-rose-200"><CircleAlert size={18} className="mt-0.5 shrink-0" /><div><strong>Local bench request failed</strong><p className="mt-1 break-words">{error}</p><p className="mt-2 text-rose-100/80">Start dashboard_server.py on this PC and confirm the frontend origin is listed in CAM_ALLOWED_ORIGINS.</p></div></div>}

    {mode === "mock" && <div className="rounded-xl border border-amber-300/25 bg-amber-300/5 p-3 text-sm text-amber-100">Simulation is enabled. Synthetic device rows are not physical hardware detections.</div>}

    <div className="grid gap-4 sm:grid-cols-3">
      <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Saved bench records</span><ClipboardList size={18} className="text-mint" /></div><div className="metric-value">{sessions.length}</div><div className="metric-foot">Read from local SQLite</div></div>
      <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Inventory result</span><Cable size={18} className="text-sky" /></div><div className="metric-value">{devices ? devices.count : "—"}</div><div className="metric-foot">{devices ? (devices.mock ? "Synthetic test data" : "Read-only host inventory") : "Scan to query USB/COM"}</div></div>
      <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Audit events</span><ShieldCheck size={18} className="text-mint" /></div><div className="metric-value">{audit.length}</div><div className="metric-foot">Local session events</div></div>
    </div>

    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Read-only device discovery" icon={Cable} action={<button className="btn-primary !px-3 !py-2 text-xs" onClick={scanDevices}><Activity size={14} /> Scan this PC</button>}>
        <p className="mb-4 text-sm leading-6 text-slate-400">Uses Windows Plug-and-Play metadata and available serial-port/Android platform tools. Detection depends on drivers, cables, device mode and installed tools.</p>
        {!devices && <p className="text-sm text-slate-500">No scan result yet. Select “Scan this PC” to run the local inventory.</p>}
        {devices && (devices.devices || []).length === 0 && <p className="rounded-xl border border-line p-4 text-sm text-slate-400">No USB/COM devices were reported. This is a real empty result, not a simulated success.</p>}
        {devices && (devices.devices || []).length > 0 && <div className="space-y-2">{devices.devices.map((device, index) => <div key={device.device_id + index} className="rounded-xl border border-line bg-ink/40 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm text-white">{device.product || device.description || device.device_id}</strong><span className={`rounded-full px-2 py-1 text-[10px] ${device.mock ? "bg-amber-300/10 text-amber-200" : "bg-mint/10 text-mint"}`}>{device.mock ? "SIMULATED" : "DETECTED"}</span></div>
          <p className="mt-1 break-all text-xs text-slate-400">{device.bus} · {device.port || "No COM port"} · VID {device.vid || "—"} / PID {device.pid || "—"}</p>
        </div>)}</div>}
        {diagnostics && <details className="mt-4 rounded-xl border border-line p-3"><summary className="cursor-pointer text-sm text-slate-200">Android / host diagnostic details</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs text-slate-400">{JSON.stringify(diagnostics.diagnostics, null, 2)}</pre></details>}
      </Panel>

      <Panel title="Create a persistent repair record" icon={Wrench}>
        <form onSubmit={createSession} className="space-y-3">
          <label className="field-label">Ticket / customer reference<input className="field-control" maxLength={160} value={form.customer_reference} onChange={e => setForm({ ...form, customer_reference: e.target.value })} placeholder="Optional ticket number" /></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="field-label">Manufacturer<select className="field-control" value={form.device_make} onChange={e => setForm({ ...form, device_make: e.target.value })}><option>Samsung</option><option>Apple</option><option>Other / unknown</option></select></label>
            <label className="field-label">Device model<input className="field-control" maxLength={160} value={form.device_model} onChange={e => setForm({ ...form, device_model: e.target.value })} placeholder="Exact model if known" /></label>
          </div>
          <label className="field-label">Intake / symptoms<textarea className="field-control min-h-24" maxLength={2000} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Reported fault and observations; no passwords or unlock codes" /></label>
          <button className="btn-primary" type="submit" disabled={!connection.status || loading}><Wrench size={16} /> Save to local SQLite</button>
          <p className="text-xs leading-5 text-slate-500">Creates a real local record and an audit event. This is not a cloud-synced customer service order.</p>
        </form>
      </Panel>
    </div>

    <Panel title="Saved repair-bench records" icon={ClipboardList} action={<button className="btn-secondary !px-3 !py-2 text-xs" onClick={refresh} disabled={loading}><RefreshCw size={14} /> Reload</button>}>
      {sessions.length === 0 ? <p className="text-sm text-slate-500">No records returned by the local API yet.</p> : <div className="space-y-3">{sessions.map(session => <div key={session.id} className="rounded-2xl border border-line bg-ink/40 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><strong className="text-sm text-white">{session.session_code}</strong><p className="mt-1 text-sm text-slate-300">{[session.device_make, session.device_model].filter(Boolean).join(" ") || "Device not specified"}</p><p className="mt-1 text-xs text-slate-500">{session.customer_reference || "No ticket reference"} · {session.created_at ? new Date(session.created_at).toLocaleString() : "Date not reported"}</p></div>
          <select aria-label={`Status for ${session.session_code}`} className="field-control !w-auto" value={session.status} onChange={e => changeStatus(session, e.target.value)}>{STATUSES.map(status => <option key={status} value={status}>{status}</option>)}</select>
        </div>
        {session.notes && <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-400">{session.notes}</p>}
      </div>)}</div>}
    </Panel>

    <Panel title="Recent audit trail" icon={ShieldCheck}>
      {audit.length === 0 ? <p className="text-sm text-slate-500">No audit events yet. Creating or changing a session status records an event.</p> : <div className="space-y-2">{audit.slice(0, 12).map(event => <div key={event.id} className="flex flex-wrap justify-between gap-2 border-b border-line py-2 last:border-0"><div><p className="text-sm text-slate-200">{event.event_type}</p><p className="text-xs text-slate-500">{event.details?.session_code || event.entity_id || "Bench event"} {event.details?.from ? `· ${event.details.from} → ${event.details.to}` : ""}</p></div><time className="text-xs text-slate-500">{event.created_at ? new Date(event.created_at).toLocaleString() : "—"}</time></div>)}</div>}
    </Panel>
  </div>;
}
