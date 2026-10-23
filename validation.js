export const SUPPORTED_BRANDS = Object.freeze(["Apple", "Samsung"]);
export const SUPPORTED_DEVICE_TYPES = Object.freeze(["Phone", "Tablet", "Laptop"]);
export const SERVICE_TYPES = Object.freeze([
  { value: "unlock", label: "Carrier unlock", description: "Eligible phones and cellular tablets" },
  { value: "repair", label: "Repair & diagnostics", description: "Phones, tablets and laptops" }
]);

export function validateServiceForm(form) {
  const errors = {};
  if (!SUPPORTED_BRANDS.includes(form.brand)) errors.brand = "Choose Apple or Samsung.";
  if (!SUPPORTED_DEVICE_TYPES.includes(form.deviceType)) errors.deviceType = "Choose phone, tablet or laptop.";
  if (!String(form.model ?? "").trim()) errors.model = "Enter the exact model.";
  if (!/^\S+@\S+\.\S+$/.test(String(form.email ?? "").trim())) errors.email = "Enter a valid email address.";

  if (form.serviceType === "unlock") {
    if (form.deviceType === "Laptop") errors.serviceType = "Carrier unlocking is available only for eligible phones and cellular tablets.";
    if (!/^\d{15}$/.test(String(form.imei ?? ""))) errors.imei = "IMEI must contain exactly 15 digits.";
    if (!String(form.network ?? "").trim()) errors.network = "Enter the current carrier/network.";
  } else if (form.serviceType === "repair") {
    if (!String(form.issue ?? "").trim()) errors.issue = "Describe the repair issue.";
    if (form.imei && !/^\d{15}$/.test(String(form.imei))) errors.imei = "If supplied, the IMEI must contain exactly 15 digits.";
  } else {
    errors.serviceType = "Choose a supported service.";
  }
  return errors;
}