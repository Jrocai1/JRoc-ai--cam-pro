import { createAdminClient, handleOptions, jsonResponse, sha256Hex } from "../_shared/common.ts";

Deno.serve(async (request: Request) => {
  const options = handleOptions(request);
  if (options) return options;

  try {
    const body = await request.json();
    const reference = typeof body.reference === "string" ? body.reference.trim().toUpperCase() : "";
    const token = typeof body.lookupToken === "string" ? body.lookupToken.trim() : "";
    if (!/^JR[MR]-[A-F0-9]{12}$/.test(reference) || token.length < 40 || token.length > 100) {
      return jsonResponse({ error: "Enter a valid reference and private tracking token." }, 400);
    }

    const tokenHash = await sha256Hex(token);
    const admin = createAdminClient();

    const unlock = await admin.from("orders")
      .select("public_reference,status,brand,device_type,model,created_at,unlock_code")
      .eq("public_reference", reference)
      .eq("lookup_token_hash", tokenHash)
      .maybeSingle();

    if (!unlock.error && unlock.data) {
      return jsonResponse({
        publicReference: unlock.data.public_reference,
        serviceType: "Carrier unlock",
        brand: unlock.data.brand,
        deviceType: unlock.data.device_type,
        model: unlock.data.model,
        status: unlock.data.status,
        createdAt: unlock.data.created_at,
        unlockCode: unlock.data.status === "Completed" ? unlock.data.unlock_code : null
      });
    }

    const repair = await admin.from("repair_requests")
      .select("public_reference,status,brand,device_type,model,created_at")
      .eq("public_reference", reference)
      .eq("lookup_token_hash", tokenHash)
      .maybeSingle();

    if (!repair.error && repair.data) {
      return jsonResponse({
        publicReference: repair.data.public_reference,
        serviceType: "Repair & diagnostics",
        brand: repair.data.brand,
        deviceType: repair.data.device_type,
        model: repair.data.model,
        status: repair.data.status,
        createdAt: repair.data.created_at,
        unlockCode: null
      });
    }

    // Same response for missing reference and wrong token to avoid record discovery.
    return jsonResponse({ error: "No request was found with that reference and token." }, 404);
  } catch (error) {
    console.error("lookup-service-request failed.", error instanceof Error ? error.message : "unknown error");
    return jsonResponse({ error: "Invalid lookup request." }, 400);
  }
});