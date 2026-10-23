import { createClient } from "@supabase/supabase-js";
import { loadStripe } from "@stripe/stripe-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabasePublicKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();
const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY?.trim();

export const isSupabaseConfigured = Boolean(
  supabaseUrl && supabasePublicKey && !supabaseUrl.includes("YOUR_PROJECT_REF")
);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabasePublicKey, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false }
    })
  : null;

export const isStripeConfigured = Boolean(
  stripePublishableKey && stripePublishableKey.startsWith("pk_") &&
  !stripePublishableKey.includes("REPLACE_ME")
);

export const stripePromise = isStripeConfigured
  ? loadStripe(stripePublishableKey)
  : null;

/**
 * Call only deployed Edge Functions. This browser module never receives a
 * Supabase service-role key or Stripe secret key.
 */
export async function invokePublicFunction(name, body) {
  if (!supabase) {
    throw new Error("Cloud services are not configured. Set the VITE_* values in web/.env.local.");
  }
  const { data, error } = await supabase.functions.invoke(name, { body });
  if (error) {
    let detail = error.message || "The service request failed.";
    try {
      const context = error.context;
      if (context && typeof context.json === "function") {
        const payload = await context.json();
        detail = payload.error || payload.message || detail;
      }
    } catch {
      // Keep the SDK error message when no structured response exists.
    }
    throw new Error(detail);
  }
  if (!data) throw new Error("The service returned an empty response.");
  return data;
}