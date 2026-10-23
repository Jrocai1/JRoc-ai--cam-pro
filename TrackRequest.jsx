import { useState } from "react";
import { AlertCircle, CheckCircle2, Clock3, LoaderCircle, Search, ShieldCheck } from "lucide-react";
import { invokePublicFunction } from "./supabaseClient.js";

export default function TrackRequest() {
  const [reference, setReference] = useState("");
  const [lookupToken, setLookupToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!/^JR[MR]-[A-F0-9]{12}$/.test(reference.trim().toUpperCase())) {
      setError("Check the service reference. It should look like JRM- followed by 12 letters or digits.");
      return;
    }
    if (lookupToken.trim().length < 40) {
      setError("Enter the private tracking token shown when you submitted the request.");
      return;
    }
    setBusy(true);
    try {
      const data = await invokePublicFunction("lookup-service-request", {
        reference: reference.trim().toUpperCase(),
        lookupToken: lookupToken.trim()
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The request could not be looked up.");
    } finally {
      setBusy(false);
    }
  }

  const completed = result?.status === "Completed";
  return (
    <div className="animate-fade-in mx-auto max-w-3xl space-y-6">
      <div>
        <p className="eyebrow">Private lookup</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">Track a service request</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Use the reference and the one-time private token shown after submission. No public directory of customer requests is exposed.</p>
      </div>
      <div className="panel-card">
        <form onSubmit={submit} className="space-y-5">
          <label className="field-label">Service reference
            <input value={reference} onChange={(e) => setReference(e.target.value.toUpperCase())} maxLength={16} className="field-control font-mono uppercase" placeholder="JRM-A1B2C3D4E5F6" autoComplete="off" />
          </label>
          <label className="field-label">Private tracking token
            <input value={lookupToken} onChange={(e) => setLookupToken(e.target.value)} className="field-control font-mono" placeholder="Paste the token from your confirmation screen" autoComplete="off" />
          </label>
          {error && <div role="alert" className="flex gap-2 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100"><AlertCircle size={17} className="mt-0.5 shrink-0" />{error}</div>}
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? <><LoaderCircle size={17} className="animate-spin" /> Checking…</> : <><Search size={17} /> Check status</>}
          </button>
        </form>
      </div>

      {result && <div className="panel-card animate-fade-in">
        <div className="flex items-start gap-3">
          <div className={`rounded-2xl p-3 ${completed ? "bg-mint/10 text-mint" : "bg-sky/10 text-sky"}`}>
            {completed ? <CheckCircle2 size={22} /> : <Clock3 size={22} />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="eyebrow">{result.serviceType}</p>
            <h2 className="mt-1 break-all text-xl font-semibold text-white">{result.publicReference}</h2>
            <p className="mt-1 text-sm text-slate-400">{result.brand} {result.deviceType} · {result.model}</p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-medium ${completed ? "border-mint/30 bg-mint/5 text-mint" : "border-sky/30 bg-sky/5 text-sky"}`}>{result.status}</span>
        </div>
        <div className="mt-5 border-t border-line pt-4">
          {completed && result.unlockCode ? <>
            <div className="flex items-center gap-2 text-sm font-semibold text-mint"><ShieldCheck size={17} /> Supplier returned a service result</div>
            <div className="mt-3 rounded-2xl border border-mint/20 bg-ink/70 p-4">
              <div className="text-xs uppercase tracking-[0.16em] text-slate-400">Unlock code / result</div>
              <div className="mt-2 break-all font-mono text-lg text-white">{result.unlockCode}</div>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">Use service results only with the correct device, model and authorized service procedure.</p>
          </> : <p className="text-sm leading-6 text-slate-400">No completion result is available yet. Supplier status checks run on a 15-minute schedule when the backend is configured. Keep the reference available if you contact the shop.</p>}
        </div>
      </div>}
      <div className="flex gap-3 rounded-2xl border border-line bg-panel/60 p-4 text-xs leading-5 text-slate-500">
        <ShieldCheck size={16} className="mt-0.5 shrink-0 text-mint" />
        Reference and token must both match. Keep the token private. If you lose it, contact the service desk; support should verify ownership rather than bypassing the lookup.
      </div>
    </div>
  );
}