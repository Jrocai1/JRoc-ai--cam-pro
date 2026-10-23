import { createAdminClient, jsonResponse, safeError } from "../_shared/common.ts";

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") return jsonResponse({ error: "Method not allowed." }, 405);

  const expectedSecret = Deno.env.get("UNLOCK_POLL_SECRET");
  const suppliedSecret = request.headers.get("x-cron-secret");
  if (!expectedSecret || !suppliedSecret || suppliedSecret !== expectedSecret) {
    return jsonResponse({ error: "Unauthorized scheduled request." }, 401);
  }

  const statusTemplate = Deno.env.get("WHOLESALER_STATUS_URL_TEMPLATE");
  const supplierKey = Deno.env.get("WHOLESALER_API_KEY");
  if (!statusTemplate || !supplierKey) {
    return jsonResponse({ error: "Supplier polling is not configured." }, 503);
  }

  try {
    const admin = createAdminClient();
    const { data: orders, error } = await admin.from("orders")
      .select("id,supplier_order_id,status,poll_attempts")
      .eq("status", "Processing")
      .not("supplier_order_id", "is", null)
      .limit(100);

    if (error) throw new Error("Could not fetch processing orders: " + error.message);

    const result = { checked: 0, completed: 0, supplierFailures: 0, stillProcessing: 0 };
    for (const order of orders ?? []) {
      if (!order.supplier_order_id) continue;
      result.checked += 1;
      await admin.from("orders").update({
        last_supplier_poll_at: new Date().toISOString(),
        poll_attempts: Number(order.poll_attempts ?? 0) + 1,
        supplier_error: null
      }).eq("id", order.id);

      const endpoint = statusTemplate.replace("{supplier_order_id}", encodeURIComponent(order.supplier_order_id));
      let url: URL;
      try {
        url = new URL(endpoint);
      } catch {
        result.supplierFailures += 1;
        await admin.from("orders").update({ supplier_error: "Configured supplier status URL is invalid." }).eq("id", order.id);
        continue;
      }
      if (url.protocol !== "https:") {
        result.supplierFailures += 1;
        await admin.from("orders").update({ supplier_error: "Supplier status URL must use HTTPS." }).eq("id", order.id);
        continue;
      }

      try {
        const response = await fetch(url, {
          method: "GET",
          headers: { "Authorization": `Bearer ${supplierKey}`, "Accept": "application/json" },
          signal: AbortSignal.timeout(10000)
        });
        if (!response.ok) {
          result.supplierFailures += 1;
          await admin.from("orders").update({
            supplier_error: `Supplier status endpoint returned HTTP ${response.status}.`
          }).eq("id", order.id);
          continue;
        }

        const body = await response.json();
        const supplierStatus = String(body.status ?? "").toLowerCase();
        if (supplierStatus === "completed") {
          const code = typeof body.code === "string" ? body.code.trim() : "";
          if (!code || code.length > 500) {
            result.supplierFailures += 1;
            await admin.from("orders").update({
              supplier_error: "Supplier reports completed without a valid unlock code."
            }).eq("id", order.id);
            continue;
          }
          const { error: updateError } = await admin.from("orders").update({
            status: "Completed",
            unlock_code: code,
            supplier_error: null
          }).eq("id", order.id);
          if (updateError) {
            result.supplierFailures += 1;
            console.error("Could not persist completed unlock state.", updateError.message);
            continue;
          }
          result.completed += 1;
        } else if (["failed", "rejected", "cancelled"].includes(supplierStatus)) {
          result.supplierFailures += 1;
          await admin.from("orders").update({
            status: "Supplier Error",
            supplier_error: `Supplier status: ${supplierStatus}`
          }).eq("id", order.id);
        } else {
          result.stillProcessing += 1;
        }
      } catch (pollError) {
        result.supplierFailures += 1;
        await admin.from("orders").update({
          supplier_error: "Supplier status check failed: " + safeError(pollError)
        }).eq("id", order.id);
      }
    }

    return jsonResponse(result);
  } catch (error) {
    console.error("poll-unlock-orders failed.", safeError(error));
    return jsonResponse({ error: "Scheduled status polling failed." }, 500);
  }
});