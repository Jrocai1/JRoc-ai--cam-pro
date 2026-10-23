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
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    const issue = typeof body.issue === "string" ? body.issue.trim() : "";
    const imei = body.imei == null || body.imei === "" ? null : String(body.imei).trim();

    if (!validBrand(brand)) return jsonResponse({ error: "Only Apple and Samsung devices are supported." }, 400);
    if (!["Phone", "Tablet", "Laptop"].includes(deviceType)) {
      return jsonResponse({ error: "Choose a phone, tablet or laptop." }, 400);
    }
    if (model.length < 1 || model.length > 120) return jsonResponse({ error: "Enter the exact model (up to 120 characters)." }, 400);
    if (!validEmail(email)) return jsonResponse({ error: "Enter a valid email address." }, 400);
    if (issue.length < 3 || issue.length > 2000) return jsonResponse({ error: "Describe the issue in 3–2,000 characters." }, 400);
    if (imei !== null && !/^[0-9]{15}$/.test(imei)) return jsonResponse({ error: "If supplied, IMEI must contain exactly 15 digits." }, 400);

    const admin = createAdminClient();
    const rawToken = newLookupToken();
    const tokenHash = await sha256Hex(rawToken);
    const publicReference = newPublicReference("JRR");
    const { error } = await admin.from("repair_requests").insert({
      brand, device_type: deviceType, model, email, imei, issue,
      status: "Awaiting Review",
      public_reference: publicReference,
      lookup_token_hash: tokenHash
    });

    if (error) {
      console.error("Unable to create private repair request.", error.message);
      return jsonResponse({ error: "The repair request could not be saved. Please retry." }, 500);
    }

    return jsonResponse({
      requestId: publicReference,
      publicReference,
      lookupToken: rawToken,
      status: "Awaiting Review"
    }, 201);
  } catch (error) {
    console.error("create-repair-request failed.", error instanceof Error ? error.message : "unknown error");
    return jsonResponse({ error: "Invalid request or temporary service failure." }, 400);
  }
});