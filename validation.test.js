import test from "node:test";
import assert from "node:assert/strict";
import {
  SUPPORTED_BRANDS,
  SUPPORTED_DEVICE_TYPES,
  validateServiceForm
} from "./validation.js";

const validRepair = {
  brand: "Apple", deviceType: "Phone", serviceType: "repair",
  model: "iPhone 15", email: "customer@example.com", issue: "Screen cracked", imei: ""
};

test("only Apple and Samsung brands are supported", () => {
  assert.deepEqual(SUPPORTED_BRANDS, ["Apple", "Samsung"]);
  const errors = validateServiceForm({ ...validRepair, brand: "Google" });
  assert.match(errors.brand, /Apple or Samsung/);
});

test("supported device types are phone, tablet and laptop only", () => {
  assert.deepEqual(SUPPORTED_DEVICE_TYPES, ["Phone", "Tablet", "Laptop"]);
  assert.ok(validateServiceForm({ ...validRepair, deviceType: "Console" }).deviceType);
});

test("carrier unlock requires exactly 15 numeric IMEI digits and a network", () => {
  const base = { ...validRepair, serviceType: "unlock", network: "T-Mobile", imei: "123456789012345" };
  assert.deepEqual(validateServiceForm(base), {});
  assert.ok(validateServiceForm({ ...base, imei: "12345" }).imei);
  assert.ok(validateServiceForm({ ...base, imei: "12345678901234A" }).imei);
  assert.ok(validateServiceForm({ ...base, network: "" }).network);
});

test("laptops cannot select carrier unlock", () => {
  const errors = validateServiceForm({
    ...validRepair, deviceType: "Laptop", serviceType: "unlock", network: "Carrier",
    imei: "123456789012345"
  });
  assert.ok(errors.serviceType);
});

test("repair intake allows laptop and optional but validated IMEI for phones/tablets", () => {
  assert.deepEqual(validateServiceForm({
    ...validRepair, brand: "Samsung", deviceType: "Laptop", model: "Galaxy Book4",
    issue: "Battery problem", imei: ""
  }), {});
  assert.ok(validateServiceForm({ ...validRepair, imei: "123" }).imei);
});