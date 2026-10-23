import Stripe from "npm:stripe@22.0.0";
import { createAdminClient, jsonResponse, safeError } from "../_shared/common.ts";

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") return jsonResponse({ error: "Method not allowed." }, 405);

  const signature = request.headers.get("stripe-signature");
  const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET");
  const stripeSecret = Deno.env.get("STRIPE_SECRET_KEY");
  if (!signature || !webhookSecret || !stripeSecret) {
    return jsonResponse({ error: "Webhook server configuration is incomplete." }, 503);
  }

  const payload = await request.text();
  const stripe = new Stripe(stripeSecret);
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(
      payload,
      signature,
      webhookSecret,
      undefined,
      Stripe.createSubtleCryptoProvider()
    );
  } catch (error) {
    console.warn("Stripe webhook signature verification failed.", safeError(error));
    return jsonResponse({ error: "Invalid Stripe webhook signature." }, 400);
  }

  if (event.type !== "payment_intent.succeeded") {
    return jsonResponse({ received: true, ignored: event.type });
  }

  const intent = event.data.object as Stripe.PaymentIntent;
  const orderId = intent.metadata?.order_id;
  if (!orderId) {
    console.error("Succeeded PaymentIntent has no order_id metadata.");
    return jsonResponse({ error: "Payment metadata is incomplete." }, 400);
  }

  try {
    const admin = createAdminClient();
    let query = await admin.from("orders")
      .select("id,public_reference,imei,brand,model,device_type,network,email,status,supplier_order_id")
      .eq("id", orderId)
      .maybeSingle();

    if (!query.data) {
      query = await admin.from("orders")
        .select("id,public_reference,imei,brand,model,device_type,network,email,status,supplier_order_id")
        .eq("stripe_intent_id", intent.id)
        .maybeSingle();
    }

    const order = query.data;
    if (query.error || !order) {
      console.error("Paid order could not be located.", query.error?.message ?? "no matching row");
      return jsonResponse({ error: "Paid order could not be located; Stripe may retry." }, 500);
    }

    // Stripe can retry webhooks; the presence of supplier_order_id makes this
    // handoff idempotent. We also send a stable supplier Idempotency-Key.
    if (order.supplier_order_id) {
      return jsonResponse({ received: true, duplicate: true, publicReference: order.public_reference });
    }

    const { error: statusError } = await admin.from("orders")
      .update({ status: "Processing", supplier_error: null })
      .eq("id", order.id);
    if (statusError) {
      console.error("Could not mark paid order Processing.", statusError.message);
      return jsonResponse({ error: "Order status update failed; Stripe may retry." }, 500);
    }

    const supplierUrl = Deno.env.get("WHOLESALER_ORDER_URL");
    const supplierKey = Deno.env.get("WHOLESALER_API_KEY");
    if (!supplierUrl || !supplierKey) {
      const message = "Supplier credentials or endpoint are not configured.";
      await admin.from("orders").update({ status: "Supplier Error", supplier_error: message }).eq("id", order.id);
      console.error(message);
      return jsonResponse({ error: "Payment recorded but supplier processing is not configured." }, 503);
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(supplierUrl);
    } catch {
      await admin.from("orders").update({ status: "Supplier Error", supplier_error: "Supplier URL is invalid." }).eq("id", order.id);
      return jsonResponse({ error: "Supplier integration URL is invalid." }, 503);
    }
    if (parsedUrl.protocol !== "https:") {
      await admin.from("orders").update({ status: "Supplier Error", supplier_error: "Supplier URL must use HTTPS." }).eq("id", order.id);
      return jsonResponse({ error: "Supplier integration must use HTTPS." }, 503);
    }

    let supplierResponse: Response;
    try {
      supplierResponse = await fetch(supplierUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${supplierKey}`,
          "Content-Type": "application/json",
          "Idempotency-Key": `jroc-${order.id}`
        },
        body: JSON.stringify({
          reference: order.public_reference,
          imei: order.imei,
          brand: order.brand,
          device_type: order.device_type,
          model: order.model,
          network: order.network,
          customer_email: order.email
        }),
        signal: AbortSignal.timeout(12000)
      });
    } catch (error) {
      const message = "Supplier network request failed: " + safeError(error);
      await admin.from("orders").update({ status: "Supplier Error", supplier_error: message }).eq("id", order.id);
      return jsonResponse({ error: "Payment recorded; supplier request failed and can be retried." }, 502);
    }

    const responseText = await supplierResponse.text();
    let responseData: Record<string, unknown> = {};
    try { responseData = JSON.parse(responseText); } catch { /* vendor must return JSON for a valid order */ }

    const supplierId = String(
      responseData.order_id ?? responseData.id ??
      (typeof responseData.order === "object" && responseData.order !== null
        ? (responseData.order as Record<string, unknown>).id ?? "" : "")
    );

    if (!supplierResponse.ok || !supplierId || supplierId.length > 200) {
      const detail = typeof responseData.message === "string" ? responseData.message.slice(0, 250) : "";
      const message = `Supplier rejected the request (HTTP ${supplierResponse.status}). ${detail}`.trim();
      await admin.from("orders").update({ status: "Supplier Error", supplier_error: message }).eq("id", order.id);
      console.error("Supplier request was not accepted.", supplierResponse.status);
      return jsonResponse({ error: "Payment recorded; supplier did not confirm the order." }, 502);
    }

    const { error: saveError } = await admin.from("orders").update({
      supplier_order_id: supplierId,
      status: "Processing",
      supplier_error: null
    }).eq("id", order.id);
    if (saveError) {
      console.error("Supplier accepted request but database update failed.", saveError.message);
      // Respond non-2xx to trigger Stripe retry. The stable supplier key reduces
      // the chance of duplicate supplier orders when the provider supports it.
      return jsonResponse({ error: "Supplier accepted but order link could not be saved." }, 500);
    }

    return jsonResponse({ received: true, status: "Processing", publicReference: order.public_reference });
  } catch (error) {
    console.error("Stripe webhook processing failed.", safeError(error));
    return jsonResponse({ error: "Webhook processing failed." }, 500);
  }
});