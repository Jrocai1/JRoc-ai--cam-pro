import { useMemo, useState } from "react";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { CheckCircle2, CreditCard, LoaderCircle, ShieldCheck, Smartphone, Wrench } from "lucide-react";
import {
  invokePublicFunction,
  isStripeConfigured,
  stripePromise
} from "./supabaseClient.js";
import {
  SUPPORTED_BRANDS as BRANDS,
  SUPPORTED_DEVICE_TYPES as DEVICE_TYPES,
  SERVICE_TYPES,
  validateServiceForm
} from "./validation.js";

function PaymentStep({ clientSecret, onPaid, onBack }) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handlePayment(event) {
    event.preventDefault();
    setError("");
    if (!stripe || !elements) {
      setError("Secure payment is still loading. Try again in a moment.");
      return;
    }
    setBusy(true);
    try {
      const result = await stripe.confirmPayment({
        elements,
        redirect: "if_required",
        confirmParams: { return_url: window.location.href }
      });
      if (result.error) {
        setError(result.error.message || "Payment could not be confirmed.");
        return;
      }
      const status = result.paymentIntent?.status;
      if (status === "succeeded" || status === "processing" || status === "requires_capture") {
        onPaid(status);
      } else {
        setError("Stripe did not report a completed payment. Check the payment method and try again.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handlePayment} className="space-y-5">
      <div className="rounded-2xl border border-line bg-ink/60 p-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
          <ShieldCheck size={17} className="text-mint" /> Secure payment
        </div>
        <PaymentElement options={{ layout: "tabs" }} />
      </div>
      {error && <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</div>}
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onBack} disabled={busy} className="btn-secondary">Back to details</button>
        <button type="submit" disabled={!stripe || busy} className="btn-primary">
          {busy ? <><LoaderCircle size={17} className="animate-spin" /> Processing…</> : <><CreditCard size={17} /> Pay securely</>}
        </button>
      </div>
      <p className="text-xs leading-5 text-slate-400">Payment is processed by Stripe. Your card details are not stored by this application.</p>
    </form>
  );
}

export default function UnlockForm({ initialDeviceType = "Phone", initialServiceType = "repair", onClose }) {
  const [form, setForm] = useState({
    brand: "Apple",
    deviceType: DEVICE_TYPES.includes(initialDeviceType) ? initialDeviceType : "Phone",
    serviceType: initialServiceType === "unlock" && initialDeviceType !== "Laptop" ? "unlock" : "repair",
    model: "",
    network: "",
    email: "",
    imei: "",
    issue: ""
  });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [apiError, setApiError] = useState("");
  const [payment, setPayment] = useState(null);
  const [complete, setComplete] = useState(null);

  const isUnlock = form.serviceType === "unlock";
  const canUnlock = form.deviceType !== "Laptop";
  const service = useMemo(() => SERVICE_TYPES.find((item) => item.value === form.serviceType), [form.serviceType]);

  function update(key, value) {
    setForm((old) => {
      const next = { ...old, [key]: value };
      if (key === "deviceType" && value === "Laptop" && next.serviceType === "unlock") next.serviceType = "repair";
      return next;
    });
    setErrors((old) => ({ ...old, [key]: undefined, serviceType: key === "deviceType" ? undefined : old.serviceType }));
    setApiError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const found = validateServiceForm(form);
    setErrors(found);
    setApiError("");
    if (Object.keys(found).length) return;

    setBusy(true);
    try {
      if (isUnlock) {
        if (!isStripeConfigured || !stripePromise) {
          throw new Error("Stripe isn't configured yet. Add VITE_STRIPE_PUBLISHABLE_KEY to web/.env.local and set the Stripe secrets for the Edge Functions.");
        }
        const data = await invokePublicFunction("create-unlock-order", {
          brand: form.brand,
          deviceType: form.deviceType,
          model: form.model.trim(),
          network: form.network.trim(),
          email: form.email.trim().toLowerCase(),
          imei: form.imei
        });
        if (!data.clientSecret || !data.orderId || !data.publicReference) {
          throw new Error("The unlock service returned an incomplete checkout response.");
        }
        setPayment({
          clientSecret: data.clientSecret,
          orderId: data.orderId,
          publicReference: data.publicReference,
          lookupToken: data.lookupToken || ""
        });
      } else {
        const data = await invokePublicFunction("create-repair-request", {
          brand: form.brand,
          deviceType: form.deviceType,
          model: form.model.trim(),
          email: form.email.trim().toLowerCase(),
          imei: form.imei || null,
          issue: form.issue.trim()
        });
        setComplete({
          type: "repair",
          reference: data.publicReference || data.requestId || "Request received",
          lookupToken: data.lookupToken || "",
          message: "Your service request has been recorded. Save the private lookup token below; it is shown only on this screen. The shop will review the details and contact you using the email you supplied."
        });
      }
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "The request could not be sent. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (complete) {
    return (
      <div className="animate-fade-in rounded-3xl border border-mint/20 bg-mint/5 p-7">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-mint/15 text-mint"><CheckCircle2 size={27} /></div>
        <p className="eyebrow">Request received</p>
        <h3 className="mt-2 text-2xl font-semibold text-white">You’re in the queue.</h3>
        <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">{complete.message}</p>
        <div className="mt-5 rounded-2xl border border-line bg-ink/70 p-4">
          <div className="text-xs uppercase tracking-[0.16em] text-slate-400">Your reference</div>
          <div className="mt-1 break-all font-mono text-lg text-mint">{complete.reference}</div>
        </div>
        {complete.lookupToken && <div className="mt-3 rounded-2xl border border-amber-300/20 bg-amber-300/5 p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-200">Private tracking token — save it now</div>
          <div className="mt-2 break-all font-mono text-sm text-white">{complete.lookupToken}</div>
          <button type="button" className="mt-3 text-xs font-semibold text-mint hover:text-white" onClick={() => navigator.clipboard?.writeText(complete.lookupToken)}>Copy token</button>
        </div>}
        <button className="btn-primary mt-6" onClick={() => { setComplete(null); setForm({ brand: "Apple", deviceType: "Phone", serviceType: "repair", model: "", network: "", email: "", imei: "", issue: "" }); }}>Create another request</button>
      </div>
    );
  }

  if (payment) {
    return (
      <div className="animate-fade-in space-y-5">
        <div className="rounded-2xl border border-mint/20 bg-mint/5 p-4">
          <p className="eyebrow">Unlock checkout</p>
          <div className="mt-1 text-lg font-semibold text-white">{payment.publicReference}</div>
          <p className="mt-2 text-sm leading-6 text-slate-300">Complete the Stripe payment below. Your unlock request is sent to the service supplier after Stripe verifies successful payment.</p>
        </div>
        <Elements stripe={stripePromise} options={{ clientSecret: payment.clientSecret, appearance: { theme: "night", variables: { colorPrimary: "#7be0c3", colorBackground: "#111824", colorText: "#e8edf5", borderRadius: "12px" } } }}>
          <PaymentStep
            clientSecret={payment.clientSecret}
            onPaid={(status) => setComplete({
              type: "unlock",
              reference: payment.publicReference,
              lookupToken: payment.lookupToken,
              message: status === "succeeded"
                ? "Stripe confirmed payment. The supplier handoff runs from the secure webhook; status may take a short time to update."
                : "Stripe is processing the payment. Keep this reference for support while the payment settles."
            })}
            onBack={() => setPayment(null)}
          />
        </Elements>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">Manufacturer
          <select value={form.brand} onChange={(e) => update("brand", e.target.value)} className="field-control">
            {BRANDS.map((brand) => <option key={brand} value={brand}>{brand}</option>)}
          </select>
          {errors.brand && <span className="field-error">{errors.brand}</span>}
        </label>
        <label className="field-label">Device type
          <select value={form.deviceType} onChange={(e) => update("deviceType", e.target.value)} className="field-control">
            {DEVICE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
          {errors.deviceType && <span className="field-error">{errors.deviceType}</span>}
        </label>
      </div>

      <fieldset>
        <legend className="mb-3 text-sm font-medium text-slate-200">What do you need?</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {SERVICE_TYPES.map((item) => {
            const disabled = item.value === "unlock" && !canUnlock;
            const selected = form.serviceType === item.value;
            const Icon = item.value === "unlock" ? ShieldCheck : Wrench;
            return (
              <button type="button" key={item.value} disabled={disabled}
                onClick={() => update("serviceType", item.value)}
                className={`rounded-2xl border p-4 text-left transition ${selected ? "border-mint/60 bg-mint/10 ring-1 ring-mint/20" : "border-line bg-ink/45 hover:border-slate-500"} ${disabled ? "cursor-not-allowed opacity-40" : ""}`}>
                <span className="flex items-center gap-2 text-sm font-semibold text-white"><Icon size={17} className={selected ? "text-mint" : "text-slate-400"} />{item.label}</span>
                <span className="mt-2 block text-xs leading-5 text-slate-400">{disabled ? "Not offered for laptops" : item.description}</span>
              </button>
            );
          })}
        </div>
        {errors.serviceType && <p className="field-error mt-2">{errors.serviceType}</p>}
      </fieldset>

      <label className="field-label">Exact model
        <input value={form.model} onChange={(e) => update("model", e.target.value)} className="field-control" placeholder={form.brand === "Apple" ? (form.deviceType === "Laptop" ? "MacBook Pro 14-inch (M3)" : form.deviceType === "Tablet" ? "iPad Pro 11-inch" : "iPhone 15 Pro") : (form.deviceType === "Laptop" ? "Galaxy Book4 Pro" : form.deviceType === "Tablet" ? "Galaxy Tab S9" : "Galaxy S24 Ultra")} autoComplete="off" />
        {errors.model && <span className="field-error">{errors.model}</span>}
      </label>

      <label className="field-label">Email for service updates
        <input type="email" autoComplete="email" value={form.email} onChange={(e) => update("email", e.target.value)} className="field-control" placeholder="you@example.com" />
        {errors.email && <span className="field-error">{errors.email}</span>}
      </label>

      {isUnlock ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="field-label">Current carrier / network
            <input value={form.network} onChange={(e) => update("network", e.target.value)} className="field-control" placeholder="e.g. AT&T, T-Mobile" />
            {errors.network && <span className="field-error">{errors.network}</span>}
          </label>
          <label className="field-label">15-digit IMEI
            <input inputMode="numeric" autoComplete="off" maxLength={15} value={form.imei} onChange={(e) => update("imei", e.target.value.replace(/\D/g, "").slice(0, 15))} className="field-control font-mono tracking-wider" placeholder="000000000000000" aria-describedby="imei-help" />
            <span id="imei-help" className="field-hint">{form.imei.length}/15 digits. Only eligible cellular devices.</span>
            {errors.imei && <span className="field-error">{errors.imei}</span>}
          </label>
        </div>
      ) : (
        <>
          <label className="field-label">Describe the issue
            <textarea rows={4} value={form.issue} onChange={(e) => update("issue", e.target.value)} className="field-control resize-y" placeholder="Tell us what's happening, when it started, and any visible damage." />
            {errors.issue && <span className="field-error">{errors.issue}</span>}
          </label>
          {form.deviceType !== "Laptop" && (
            <label className="field-label">IMEI (optional)
              <input inputMode="numeric" autoComplete="off" maxLength={15} value={form.imei} onChange={(e) => update("imei", e.target.value.replace(/\D/g, "").slice(0, 15))} className="field-control font-mono tracking-wider" placeholder="15 digits if known" />
              {errors.imei && <span className="field-error">{errors.imei}</span>}
            </label>
          )}
        </>
      )}

      {apiError && <div role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm leading-5 text-rose-100">{apiError}</div>}
      <div className="flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2 text-xs leading-5 text-slate-400">
          <ShieldCheck size={16} className="mt-0.5 shrink-0 text-mint" />
          Your device details are sent to the configured service backend. Never share a passcode or account password in this form.
        </div>
        <button type="submit" disabled={busy} className="btn-primary shrink-0">
          {busy ? <><LoaderCircle size={17} className="animate-spin" /> Sending…</> : isUnlock ? <><CreditCard size={17} /> Continue to secure payment</> : <><Wrench size={17} /> Submit repair request</>}
        </button>
      </div>
      {onClose && <button type="button" className="btn-secondary w-full" onClick={onClose}>Cancel</button>}
    </form>
  );
}
