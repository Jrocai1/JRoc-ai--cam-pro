import { useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, BadgeCheck, BookOpen, Check, ChevronDown, ClipboardCheck,
  CircleHelp, Clock3, Cpu, FileText, Gauge, Headphones, Laptop, LayoutDashboard, RotateCcw,
  Menu, MonitorSmartphone, Plus, Search, Settings2, ShieldCheck, Smartphone,
  Tablet, Wrench, X, Zap
} from "lucide-react";
import UnlockForm from "./UnlockForm.jsx";
import { isStripeConfigured, isSupabaseConfigured } from "./supabaseClient.js";
import TrackRequest from "./TrackRequest.jsx";
import AdminRecoveryWorkbench from "./AdminRecoveryWorkbench.jsx";
import BenchDashboard from "./BenchDashboard.jsx";

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "new-request", label: "New service request", icon: Plus },
  { id: "track", label: "Track request", icon: Activity },
  { id: "device-tools", label: "Device tools", icon: Cpu },
  { id: "unlock-assistant", label: "AI Unlock Assistant", icon: ShieldCheck },
  { id: "recovery-restore", label: "Recovery & Restore", icon: RotateCcw },
  { id: "admin-workbench", label: "Admin Recovery Workbench", icon: ClipboardCheck },
  { id: "local-bench", label: "Local Bench Console", icon: Wrench },
  { id: "help", label: "Workflow guide", icon: BookOpen }
];

const supported = [
  { name: "iPhone", brand: "Apple", icon: Smartphone, description: "Diagnostics, repair intake and eligible carrier service" },
  { name: "iPad", brand: "Apple", icon: Tablet, description: "Tablet repairs and eligible cellular-device service" },
  { name: "MacBook", brand: "Apple", icon: Laptop, description: "Laptop intake, service tracking and repair workflow" },
  { name: "Galaxy phones", brand: "Samsung", icon: Smartphone, description: "Diagnostics, repair intake and eligible carrier service" },
  { name: "Galaxy Tab", brand: "Samsung", icon: Tablet, description: "Tablet repairs and eligible cellular-device service" },
  { name: "Galaxy Book", brand: "Samsung", icon: Laptop, description: "Laptop intake, diagnostics and service tracking" }
];

function App() {
  const [active, setActive] = useState("overview");
  const [mobileNav, setMobileNav] = useState(false);
  const [requestType, setRequestType] = useState("repair");
  const [showRequest, setShowRequest] = useState(false);

  function startRequest(service) {
    setRequestType(service);
    setActive("new-request");
    setShowRequest(true);
    setMobileNav(false);
  }

  const backendReady = isSupabaseConfigured;
  const stripeReady = isStripeConfigured;

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-line bg-[#121a26] transition-transform duration-200 lg:translate-x-0 ${mobileNav ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-[84px] items-center gap-3 border-b border-line px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-mint text-ink shadow-glow"><Wrench size={21} strokeWidth={2.5} /></div>
          <div>
            <div className="text-sm font-bold tracking-wide text-white">J-ROC AI</div>
            <div className="text-xs text-slate-400">Mobile Repair</div>
          </div>
          <button onClick={() => setMobileNav(false)} className="ml-auto rounded-lg p-1 text-slate-400 hover:bg-panel lg:hidden" aria-label="Close navigation"><X size={19} /></button>
        </div>
        <div className="px-4 pb-2 pt-6 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Workspace</div>
        <nav className="space-y-1 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const selected = active === item.id;
            return <button key={item.id} onClick={() => { setActive(item.id); setShowRequest(item.id === "new-request"); setMobileNav(false); }}
              className={`nav-item ${selected ? "nav-item-active" : ""}`}>
              <Icon size={17} /> <span>{item.label}</span>{selected && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-mint" />}
            </button>;
          })}
        </nav>
        <div className="mt-7 px-4 pb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Supported devices</div>
        <div className="mx-4 rounded-2xl border border-line bg-ink/70 p-3">
          <div className="flex items-center gap-2 text-sm font-semibold"><Smartphone size={16} className="text-mint" /> Apple</div>
          <p className="mt-1 pl-6 text-xs leading-5 text-slate-400">iPhone · iPad · MacBook</p>
          <div className="mt-3 flex items-center gap-2 text-sm font-semibold"><Tablet size={16} className="text-sky" /> Samsung</div>
          <p className="mt-1 pl-6 text-xs leading-5 text-slate-400">Galaxy phones · Tab · Book</p>
        </div>
        <div className="mt-auto p-4">
          <div className="rounded-2xl border border-line bg-panel/65 p-3">
            <div className="flex items-center gap-2 text-xs font-semibold"><ShieldCheck size={15} className="text-mint" /> Secure service workflow</div>
            <p className="mt-2 text-xs leading-5 text-slate-400">No account passwords or screen lock codes requested.</p>
          </div>
          <div className="mt-4 flex items-center justify-between text-[11px] text-slate-500"><span>J-Roc AI Mobile Repair</span><span>v0.3.0</span></div>
        </div>
      </aside>

      {mobileNav && <button className="fixed inset-0 z-30 bg-black/60 lg:hidden" onClick={() => setMobileNav(false)} aria-label="Close menu overlay" />}

      <main className="min-h-screen lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-line bg-ink/90 px-4 backdrop-blur-xl sm:px-7">
          <div className="flex items-center gap-3">
            <button className="rounded-xl border border-line p-2 text-slate-300 lg:hidden" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={18} /></button>
            <div>
              <div className="text-sm font-semibold text-white">{navItems.find((item) => item.id === active)?.label || "Overview"}</div>
              <div className="hidden text-xs text-slate-500 sm:block">Apple and Samsung device service workspace</div>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className={`hidden items-center gap-2 rounded-full border px-3 py-1.5 text-xs sm:flex ${backendReady ? "border-mint/20 bg-mint/5 text-mint" : "border-amber-400/20 bg-amber-300/5 text-amber-200"}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${backendReady ? "bg-mint" : "bg-amber-300"}`} />
              {backendReady ? "Backend configured" : "Preview mode"}
            </div>
            <button onClick={() => startRequest("repair")} className="btn-primary !px-3 !py-2 text-xs sm:!px-4 sm:text-sm"><Plus size={16} /> New request</button>
          </div>
        </header>

        <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-7 sm:py-8">
          {active === "overview" && (
            <Overview onStart={startRequest} backendReady={backendReady} stripeReady={stripeReady} />
          )}
          {active === "new-request" && (
            <ServiceRequest requestType={requestType} setRequestType={setRequestType} showRequest={showRequest} onStart={startRequest} />
          )}
          {active === "track" && <TrackRequest />}
          {active === "device-tools" && <DeviceTools />}
          {active === "unlock-assistant" && <UnlockEligibilityAssistant onStart={startRequest} />}
          {active === "recovery-restore" && <RecoveryRestore />}
          {active === "admin-workbench" && <AdminRecoveryWorkbench />}
          {active === "local-bench" && <BenchDashboard />}
          {active === "help" && <WorkflowGuide onStart={startRequest} />}
        </div>
        <footer className="mx-auto flex max-w-[1500px] flex-col gap-2 border-t border-line px-4 py-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <span>© {new Date().getFullYear()} J-ROC AI · Mobile Repair</span>
          <span>Restricted scope: Apple and Samsung phones, tablets and laptops.</span>
        </footer>
      </main>
    </div>
  );
}

function Overview({ onStart, backendReady, stripeReady }) {
  return (
    <div className="animate-fade-in space-y-7">
      <div className="relative overflow-hidden rounded-[28px] border border-line bg-gradient-to-br from-[#202e41] via-[#182536] to-[#14202c] p-6 shadow-glow sm:p-9">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-mint/10 blur-3xl" />
        <div className="absolute bottom-[-90px] right-[28%] h-52 w-52 rounded-full bg-sky/10 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.45fr_0.75fr] lg:items-center">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-mint/25 bg-mint/5 px-3 py-1.5 text-xs font-medium text-mint"><Activity size={14} /> Repair workflow, under one roof</div>
            <h1 className="max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white sm:text-4xl lg:text-[42px]">One workspace for every <span className="text-mint">Apple & Samsung</span> service job.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">Capture intake details, open repair requests, run read-only device diagnostics, record work, and guide each job through estimate, approval and quality control.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button className="btn-primary" onClick={() => onStart("repair")}><Plus size={17} /> Start a repair request</button>
              <button className="btn-secondary" onClick={() => onStart("unlock")}><ShieldCheck size={17} /> Request eligible carrier service</button>
            </div>
          </div>
          <div className="relative rounded-3xl border border-white/10 bg-ink/50 p-5 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Device scope</p>
                <p className="mt-1 text-xl font-semibold text-white">6 service families</p>
              </div>
              <div className="rounded-2xl bg-mint/10 p-3 text-mint"><MonitorSmartphone size={25} /></div>
            </div>
            <div className="mt-5 space-y-3">
              {[
                ["Apple phones", "iPhone", Smartphone],
                ["Apple tablets", "iPad", Tablet],
                ["Apple laptops", "MacBook", Laptop],
                ["Samsung phones", "Galaxy", Smartphone],
                ["Samsung tablets", "Galaxy Tab", Tablet],
                ["Samsung laptops", "Galaxy Book", Laptop]
              ].map(([label, details, Icon]) => <div key={label} className="flex items-center gap-3 border-b border-white/5 pb-3 last:border-0 last:pb-0">
                <div className="rounded-xl bg-white/5 p-2 text-slate-300"><Icon size={16} /></div>
                <div className="flex-1 text-sm text-slate-200">{label}</div>
                <span className="text-xs text-slate-500">{details}</span>
              </div>)}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Device manufacturers</span><MonitorSmartphone className="text-mint" size={18} /></div><div className="metric-value">02</div><div className="metric-foot">Apple · Samsung only</div></div>
        <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Device categories</span><Smartphone className="text-sky" size={18} /></div><div className="metric-value">03</div><div className="metric-foot">Phones · Tablets · Laptops</div></div>
        <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Cloud services</span><Zap className="text-amber-300" size={18} /></div><div className="metric-value text-2xl">{backendReady ? "Connected" : "Setup needed"}</div><div className="metric-foot">{backendReady ? "Supabase browser key detected" : "Configure Supabase public values"}</div></div>
        <div className="metric-card"><div className="flex items-center justify-between"><span className="metric-label">Stripe checkout</span><CreditCardIcon /></div><div className="metric-value text-2xl">{stripeReady ? "Configured" : "Setup needed"}</div><div className="metric-foot">Publishable key only in browser</div></div>
      </div>

      <section>
        <div className="mb-4 flex items-end justify-between">
          <div><p className="eyebrow">Supported equipment</p><h2 className="mt-1 text-xl font-semibold text-white sm:text-2xl">Built around the devices you service.</h2></div>
          <span className="hidden rounded-full border border-line px-3 py-1.5 text-xs text-slate-400 sm:block">Apple + Samsung only</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {supported.map((device) => {
            const Icon = device.icon;
            return <div className="device-card" key={device.name}>
              <div className="flex items-start justify-between">
                <div className="rounded-2xl border border-line bg-ink/70 p-3 text-slate-200"><Icon size={22} /></div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${device.brand === "Apple" ? "bg-slate-200/10 text-slate-200" : "bg-sky/10 text-sky"}`}>{device.brand}</span>
              </div>
              <h3 className="mt-4 text-base font-semibold text-white">{device.name}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">{device.description}</p>
              <button className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-mint hover:text-white" onClick={() => onStart("repair")}>Create service request <ArrowRight size={15} /></button>
            </div>;
          })}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div><p className="eyebrow">Standard service lifecycle</p><h2 className="mt-1 text-lg font-semibold text-white">Keep every repair traceable.</h2></div>
            <div className="rounded-xl bg-mint/10 p-2 text-mint"><Gauge size={20} /></div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {["Intake", "Diagnose", "Estimate & approve", "Repair & QC"].map((step, index) => <div key={step} className="rounded-2xl border border-line bg-ink/60 p-3">
              <span className="text-[11px] font-semibold tracking-widest text-mint">0{index + 1}</span>
              <div className="mt-2 text-sm font-medium text-slate-200">{step}</div>
            </div>)}
          </div>
        </div>
        <div className="panel-card">
          <div className="flex items-center gap-2"><CircleHelp size={18} className="text-sky" /><h2 className="text-lg font-semibold text-white">Before you get started</h2></div>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
            <li className="flex gap-2"><Check size={16} className="mt-1 shrink-0 text-mint" /> Select only Apple or Samsung hardware.</li>
            <li className="flex gap-2"><Check size={16} className="mt-1 shrink-0 text-mint" /> Carrier unlock requires a 15-digit IMEI and eligible phone/cellular tablet.</li>
            <li className="flex gap-2"><Check size={16} className="mt-1 shrink-0 text-mint" /> Laptops use repair intake, not IMEI-based carrier unlocking.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}

function CreditCardIcon() {
  return <div className="rounded-lg bg-mint/10 p-1.5 text-mint"><ShieldCheck size={17} /></div>;
}

function ServiceRequest({ requestType, setRequestType, showRequest, onStart }) {
  return (
    <div className="animate-fade-in mx-auto max-w-4xl space-y-6">
      <div>
        <p className="eyebrow">Service desk</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">Start a request</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Choose a supported Apple or Samsung device. Carrier service is offered only for eligible phones and cellular tablets; laptops are routed through repair intake.</p>
      </div>
      <div className="panel-card">
        <div className="mb-6 flex flex-wrap gap-2 border-b border-line pb-5">
          <button className={`filter-chip ${requestType === "repair" ? "filter-chip-active" : ""}`} onClick={() => setRequestType("repair")}><Wrench size={15} /> Repair & diagnostics</button>
          <button className={`filter-chip ${requestType === "unlock" ? "filter-chip-active" : ""}`} onClick={() => setRequestType("unlock")}><ShieldCheck size={15} /> Carrier unlock</button>
        </div>
        <UnlockForm initialDeviceType="Phone" initialServiceType={requestType} key={requestType} />
      </div>
      <div className="flex gap-3 rounded-2xl border border-line bg-panel/60 p-4 text-sm leading-6 text-slate-400">
        <ShieldCheck size={19} className="mt-0.5 shrink-0 text-mint" />
        Only use this service for devices you own or are authorized to service. The form does not request screen-lock codes, Apple Account credentials or Google credentials.
      </div>
    </div>
  );
}

function DeviceTools() {
  const tools = [
    { title: "Read-only device discovery", icon: Search, status: "Requires configured Edge Function", detail: "Connects to authorized ADB/Fastboot checks and Windows USB diagnostics. Download Mode may not appear in ADB." },
    { title: "Firmware package inspection", icon: FileText, status: "Local desktop tool", detail: "Archives can be inventoried and hashed; this does not authenticate official origin or model/bootloader compatibility." },
    { title: "Device compatibility", icon: BadgeCheck, status: "Manual verification required", detail: "Confirm the exact Apple or Samsung product model and service path before any device-altering operation." }
  ];
  return <div className="animate-fade-in space-y-6">
    <div><p className="eyebrow">Service utilities</p><h1 className="mt-1 text-3xl font-semibold text-white">Device tools</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Utilities remain limited to Apple and Samsung phones, tablets and laptops. This web UI does not directly issue firmware-write commands.</p></div>
    <div className="grid gap-4 lg:grid-cols-3">
      {tools.map(({ title, icon: Icon, status, detail }) => <div className="panel-card" key={title}>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-mint/10 text-mint"><Icon size={21} /></div>
        <h2 className="mt-4 font-semibold text-white">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p>
        <div className="mt-5 border-t border-line pt-4 text-xs text-amber-200">{status}</div>
      </div>)}
    </div>
    <div className="rounded-2xl border border-amber-400/20 bg-amber-300/5 p-5"><div className="flex gap-3"><ShieldCheck size={20} className="mt-0.5 shrink-0 text-amber-200" /><div><h3 className="font-semibold text-white">Flashing engine is disabled</h3><p className="mt-1 text-sm leading-6 text-slate-400">Use official manufacturer recovery procedures. This frontend and its current backend do not bypass Activation Lock, Google/FRP verification, screen locks or account security.</p></div></div></div>
  </div>;
}


function UnlockEligibilityAssistant({ onStart }) {
  const [brand, setBrand] = useState("Samsung");
  const [deviceType, setDeviceType] = useState("Phone");
  const [carrier, setCarrier] = useState("");
  const [country, setCountry] = useState("United States");
  const [paidOff, setPaidOff] = useState(false);
  const [accountCurrent, setAccountCurrent] = useState(false);
  const [proofOfOwnership, setProofOfOwnership] = useState(false);
  const [imei, setImei] = useState("");
  const [result, setResult] = useState(null);

  function validImei(value) {
    if (!/^\d{15}$/.test(value)) return false;
    let sum = 0;
    for (let i = 0; i < value.length; i++) {
      let digit = Number(value[value.length - 1 - i]);
      if (i % 2 === 1) { digit *= 2; if (digit > 9) digit -= 9; }
      sum += digit;
    }
    return sum % 10 === 0;
  }

  function assess(event) {
    event.preventDefault();
    if (deviceType === "Laptop") {
      setResult({ title: "Carrier unlocking not applicable", details: "Laptop service does not use IMEI-based carrier unlocking. Choose repair and diagnostics instead.", kind: "info" });
      return;
    }
    if (deviceType === "Tablet" && !imei.trim()) {
      setResult({ title: "Cellular tablet check required", details: "Enter the 15-digit IMEI for a cellular tablet. Wi-Fi-only tablets do not use carrier unlocking.", kind: "info" });
      return;
    }
    if (imei.trim() && !validImei(imei.trim())) {
      setResult({ title: "Check the IMEI", details: "The entry must be a valid 15-digit IMEI with a valid check digit. The value is checked in this browser only and is not sent to a service.", kind: "warning" });
      return;
    }
    if (!carrier.trim()) {
      setResult({ title: "Carrier information needed", details: "Enter the current or original carrier so you can use its official unlock eligibility process.", kind: "info" });
      return;
    }
    const missing = [];
    if (!paidOff) missing.push("confirm the device meets the carrier's payment or financing requirements");
    if (!accountCurrent) missing.push("confirm the account is in good standing and the carrier's policy is met");
    if (!proofOfOwnership) missing.push("prepare proof of ownership or purchase");
    const suffix = missing.length ? " Before requesting an unlock, " + missing.join("; ") + "." : " Your answers are a pre-check only; the carrier must verify eligibility and approve the unlock.";
    setResult({
      title: missing.length ? "Ready for official eligibility review" : "Pre-check complete — carrier approval required",
      details: "Device: " + brand + " " + deviceType + ". Carrier: " + carrier.trim() + ". Country: " + country + "." + suffix + " This tool does not bypass carrier controls, Activation Lock, FRP, or account security.",
      kind: missing.length ? "info" : "success"
    });
  }

  return (
    <div className="animate-fade-in mx-auto max-w-5xl space-y-6">
      <div>
        <p className="eyebrow">Authorized unlocking workflow</p>
        <h1 className="mt-1 text-3xl font-semibold text-white">AI Unlock Eligibility Assistant</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">A guided pre-check for eligible Apple and Samsung phones and cellular tablets. It helps prepare an official carrier request; it does not claim to unlock a device itself. No AI provider or carrier API is connected by this screen.</p>
      </div>
      <form onSubmit={assess} className="panel-card space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm text-slate-300">Manufacturer
            <select value={brand} onChange={(e) => setBrand(e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white">
              <option>Apple</option><option>Samsung</option>
            </select>
          </label>
          <label className="block text-sm text-slate-300">Device type
            <select value={deviceType} onChange={(e) => setDeviceType(e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white">
              <option>Phone</option><option>Tablet</option><option>Laptop</option>
            </select>
          </label>
          <label className="block text-sm text-slate-300">Current or original carrier
            <input value={carrier} onChange={(e) => setCarrier(e.target.value)} placeholder="Enter carrier name" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white placeholder:text-slate-600" />
          </label>
          <label className="block text-sm text-slate-300">Country
            <select value={country} onChange={(e) => setCountry(e.target.value)} className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 text-white">
              <option>United States</option><option>Canada</option><option>United Kingdom</option><option>Other</option>
            </select>
          </label>
          {deviceType !== "Laptop" && <label className="block text-sm text-slate-300 sm:col-span-2">IMEI (optional for phones; required for cellular tablets)
            <input inputMode="numeric" autoComplete="off" maxLength={15} value={imei} onChange={(e) => setImei(e.target.value.replace(/\D/g, "").slice(0, 15))} placeholder="15 digits — checked locally only" className="mt-2 w-full rounded-xl border border-line bg-ink px-3 py-3 font-mono text-white placeholder:text-slate-600" />
            <span className="mt-1 block text-xs text-slate-500">Do not enter account passwords, passcodes, or other credentials. This screen does not transmit or store the IMEI.</span>
          </label>}
        </div>
        <div className="space-y-3 border-t border-line pt-5">
          <p className="text-sm font-semibold text-white">Eligibility checklist</p>
          {[
            [paidOff, setPaidOff, "I have confirmed the device meets payment/financing requirements."],
            [accountCurrent, setAccountCurrent, "I have confirmed the carrier account is in good standing."],
            [proofOfOwnership, setProofOfOwnership, "I can provide proof of ownership or purchase if requested."]
          ].map(([checked, setter, label]) => <label key={label} className="flex cursor-pointer items-start gap-3 text-sm leading-6 text-slate-300">
            <input type="checkbox" checked={checked} onChange={(e) => setter(e.target.checked)} className="mt-1 h-4 w-4 accent-emerald-400" />
            <span>{label}</span>
          </label>)}
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="submit" className="btn-primary"><ShieldCheck size={17} /> Check eligibility readiness</button>
          <button type="button" className="btn-secondary" onClick={() => onStart("unlock")}>Open carrier service request <ArrowRight size={16} /></button>
        </div>
      </form>
      {result && <div className={`rounded-2xl border p-5 ${result.kind === "warning" ? "border-amber-400/30 bg-amber-300/5" : result.kind === "success" ? "border-mint/30 bg-mint/5" : "border-line bg-panel/60"}`}>
        <div className="flex items-start gap-3">
          <ShieldCheck size={20} className="mt-0.5 shrink-0 text-mint" />
          <div><h2 className="font-semibold text-white">{result.title}</h2><p className="mt-2 text-sm leading-6 text-slate-300">{result.details}</p></div>
        </div>
      </div>}
      <div className="rounded-2xl border border-amber-400/20 bg-amber-300/5 p-5 text-sm leading-6 text-slate-300">
        <strong className="text-white">Security boundary:</strong> this assistant cannot remove Apple Activation Lock, Samsung/Google FRP, screen locks, or account protections. For those cases, use the manufacturer's official recovery or an authorized service channel.
      </div>
    </div>
  );
}

function WorkflowGuide({ onStart }) {
  const phases = [
    ["01", "Customer & device", "Record contact details, brand/model, serial/IMEI if relevant, condition and accessories."],
    ["02", "Intake & diagnosis", "Record symptoms, evidence and the next diagnostic step before making changes."],
    ["03", "Estimate & consent", "Provide a written estimate and record customer approval before discretionary paid work."],
    ["04", "Repair & QC", "Log performed work and run relevant post-repair checks with pass/fail evidence."],
    ["05", "Complete & notify", "Create invoice, record payment status, notify through an authorized channel and close the job."]
  ];
  return <div className="animate-fade-in mx-auto max-w-4xl space-y-6">
    <div><p className="eyebrow">Operator guide</p><h1 className="mt-1 text-3xl font-semibold text-white">A consistent workflow protects the customer and the shop.</h1><p className="mt-3 text-sm leading-6 text-slate-400">Adapted to this release and the supported-device boundary.</p></div>
    <div className="panel-card space-y-1">
      {phases.map(([num, title, detail]) => <div className="flex gap-4 border-b border-line py-5 last:border-0" key={num}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-mint/10 font-mono text-sm text-mint">{num}</div>
        <div><h3 className="font-semibold text-white">{title}</h3><p className="mt-1 text-sm leading-6 text-slate-400">{detail}</p></div>
      </div>)}
    </div>
    <button className="btn-primary" onClick={() => onStart("repair")}>Start new service request <ArrowRight size={16} /></button>
  </div>;
}

export default App;
