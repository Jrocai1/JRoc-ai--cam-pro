import { createClient } from "npm:@supabase/supabase-js@2.57.4";

export const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-cron-secret, stripe-signature",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store"
};

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: CORS_HEADERS });
}

export function handleOptions(request: Request): Response | null {
  if (request.method === "OPTIONS") return new Response("ok", { headers: CORS_HEADERS });
  if (request.method !== "POST") return jsonResponse({ error: "Method not allowed." }, 405);
  return null;
}

export function createAdminClient() {
  const url = Deno.env.get("SUPABASE_URL");
  let secret = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  // Newer Supabase runtimes can expose service keys as a JSON map.
  if (!secret) {
    try {
      const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
      secret = keys.default ?? Object.values(keys)[0];
    } catch {
      // A missing/invalid secret is reported by the validation below.
    }
  }

  if (!url || !secret || typeof secret !== "string") {
    throw new Error("Server-side Supabase credentials are not configured.");
  }

  return createClient(url, secret, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false }
  });
}

export async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function newLookupToken(): string {
  // Two random UUIDs make this a high-entropy customer-held secret.
  return crypto.randomUUID().replaceAll("-", "") + crypto.randomUUID().replaceAll("-", "");
}

export function newPublicReference(prefix = "JRM"): string {
  return prefix + "-" + crypto.randomUUID().replaceAll("-", "").slice(0, 12).toUpperCase();
}

export function validEmail(value: string): boolean {
  return value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function validBrand(value: unknown): value is "Apple" | "Samsung" {
  return value === "Apple" || value === "Samsung";
}

export function safeError(value: unknown): string {
  return value instanceof Error ? value.message.slice(0, 400) : "Unexpected server error.";
}