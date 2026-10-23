import Stripe from "npm:stripe@22.0.0";
import {
  createAdminClient, handleOptions, jsonResponse, newLookupToken,
  newPublicReference, sha256Hex, validBrand, validEmail
} from "../_shared/common.ts";

Deno.serve(async (request: Request) => {
  const options = handleOptions(request);
  if (options) return options;

  try {
    const rawBody = await request.text();
    if (rawBody.length > 20_000) return jsonResponse({ error: "Request is too large." }, 413);

    const body = JSON.parse(rawBody);
    const brand = body.brand;
    const deviceType = body.deviceType;
    const model = typeof body.model === "string" ? body.model.trim() : "";
    const network = typeof body.network === "string" ? body.network.trim() : "";
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    const imei = typeof body.imei === "string" ? body.imei.trim() : "";

    if (!validBrand(brand)) return jsonResponse({ error: "Only Apple and Samsung devices are supported." }, 400);
    if (!["Phone", "Tablet"].includes(deviceType)) {
      return jsonResponse({ error: "Carrier unlocking is only available for eligible phones and cellular tablets; laptops use repair intake." }, 400);
    }
    if (model.length < 1 || model.length > 120) return jsonResponse({ error: "Enter the exact model (up to 120 characters)." }, 400);
    if (!/^[0-9]{15}$/.test(imei)) return jsonResponse({ error: "IMEI must contain exactly 15 digits." }, 400);
    if (network.length < 1 || network.length > 120) return jsonResponse({ error: "Enter a valid carrier/network." }, 400);
    if (!validEmail(email)) return jsonResponse({ error: "Enter a valid email address." }, 400);

    const stripeSecret = Deno.env.get("STRIPE_SECRET_KEY");
    const amount = Number(Deno.env.get("UNLOCK_PRICE_CENTS") ?? "");
    const currency = (Deno.env.get("UNLOCK_CURRENCY") ?? "usd").toLowerCase();
    if (!stripeSecret || !stripeSecret.startsWith("sk_")) {
      return jsonResponse({ error: "Stripe server credentials are not configured." }, 503);
    }
    if (!Number.isSafeInteger(amount) || amount < 100 || amount > 200_000) {
      return jsonResponse({ error: "Unlock pricing is not configured correctly. Contact the shop administrator." }, 503);
    }
    if (!/^[a-z]{3}$/.test(currency)) return jsonResponse({ error: "Unlock currency configuration is invalid." }, 503);

    const admin = createAdminClient();
    const rawToken = newLookupToken();
    const tokenHash = await sha256Hex(rawToken);
    const publicReference = newPublicReference("JRM");

    const { data: order, error: insertError } = await admin.from("orders").insert({
      imei,
      brand,
      model,
      device_type: deviceType,
      network,
      email,
      status: "Awaiting Payment",
      public_reference: publicReference,
      lookup_token_hash: tokenHash
    }).select("id,public_reference").single();

    if (insertError || !order) {
      console.error("Unable to create private unlock order.", insertError?.message);
      return jsonResponse({ error: "The service request could not be created. Please retry." }, 500);
    }

    const stripe = new Stripe(stripeSecret);
    try {
      const intent = await stripe.paymentIntents.create({
        amount,
        currency,
        receipt_email: email,
        automatic_payment_methods: { enabled: true },
        description: `J-Roc AI Mobile Repair unlock service — ${brand} ${model}`,
        metadata: {
          order_id: order.id,
          public_reference: publicReference,
          imei,
          brand,
          device_type: deviceType,
          model,
          network
        }
      }, { idempotencyKey: `jroc-mobile-unlock-${order.id}` });

      const { error: updateError } = await admin.from("orders")
        .update({ stripe_intent_id: intent.id })
        .eq("id", order.id);
      if (updateError) throw new Error("Could not link payment to the order.");

      return jsonResponse({
        orderId: order.id,
        publicReference,
        lookupToken: rawToken,
        clientSecret: intent.client_secret,
        amount,
        currency
      }, 201);
    } catch (paymentError) {
      await admin.from("orders").update({
        status: "Payment Setup Failed",
        supplier_error: "Payment setup failed; no supplier request was submitted."
      }).eq("id", order.id);
      console.error("Stripe PaymentIntent setup failed.", paymentError instanceof Error ? paymentError.message : "unknown error");
      return jsonResponse({ error: "Secure checkout could not be started. No supplier order was submitted." }, 502);
    }
  } catch (error) {
    console.error("create-unlock-order failed.", error instanceof Error ? error.message : "unknown error");
    return jsonResponse({ error: "Invalid request or temporary service failure." }, 400);
  }
});