# J-Roc AI Mobile Repair — Operator Guide

This guide covers the current local desktop workflow and the separate React service-request frontend. It reflects the current scope and does not claim that planned features are finished.

## 1. Supported device scope

The product accepts **Apple and Samsung only**:

- Apple: iPhone (phone), iPad (tablet), MacBook (laptop).
- Samsung: Galaxy phones, Galaxy Tab (tablet), Galaxy Book (laptop).

No other manufacturer or device type is supported by the current intake flow. Carrier unlock checkout is limited to eligible phones and cellular tablets with a 15-digit numeric IMEI. Laptops can be submitted for repair/diagnostics but do not use IMEI-based carrier unlock checkout.

## 2. First launch

The Windows desktop app runs from the installer or `python main.py`. Main tabs include Overview, Customers, Devices, Repair Jobs, Parts & Inventory, Technicians, Estimates & Invoices, QC & Reports, Device Tools and Settings & Audit. Local SQLite data is stored at `%LOCALAPPDATA%\JROC\MobileRepair\mobile_repair.sqlite3`. Named staff logins are not implemented in the desktop baseline.

The React frontend lives in `web/`; see [web/README.md](../web/README.md) and [Supabase setup](../supabase/README.md).

## 3. Configure the shop

Open **Settings & Audit** and enter the business name, address, phone, email, currency and default tax rate. Confirm the tax treatment against your business requirements before issuing an estimate.

## 4. Create the repair job

Every repair connects a customer, an allowed device and a job:

**Customer → Device → Intake → Job → Diagnostics → Estimate → Approval → Parts → Repair → QC → Invoice/Payment → Device Return → Reporting**

Create the customer record first. Register the device with manufacturer (Apple or Samsung), type (Phone, Tablet or Laptop), model, serial number/IMEI when appropriate, intake condition, accessories and reported issue. The app generates a repair job number, priority and workflow status. Record only personal data needed for service.

## 5. Diagnose before repairing

Select a job and use **Add Diagnosis** to record category, findings/evidence and next action. A symptom is not necessarily the confirmed root cause. For a charging complaint, inspect and document cable, power source, connector, battery behavior, software state, temperature and physical damage as appropriate.

**Device Tools** can gather read-only ADB/Fastboot and Windows USB data. Device state and manufacturer drivers affect what can be detected. ADB may not enumerate a phone in Download Mode or recovery; detection does not establish support for a model-specific operation.

## 6. Estimates and customer approval

Use **Create Estimate for Job** under **Estimates & Invoices**. Enter a service line, quantity, unit price and tax. The data layer supports multiple line items, while the current desktop form creates one line per estimate. Record Approved or Declined. Do not start discretionary paid work before customer approval.

## 7. Parts and inventory

Create inventory parts with unique SKUs, opening quantities, minimum thresholds, costs, retail prices and supplier references. Use **Adjust Stock** for a documented correction or receipt. With a job selected, use **Use Part** to consume inventory against it. Negative inventory and consumption above available stock are rejected.

## 8. Repair logs and QC

Use **Log Repair Work** to record actual work and time. Use **Add QC Check** for device-appropriate tests such as power-on, charging, battery, display/touch, cameras, audio, buttons, connectivity, data connection, biometrics and physical assembly. Record pass/fail with supporting notes.

## 9. Invoices, payments and notifications

Create invoices only from an approved estimate. The desktop app tracks partial/full payments and outstanding balances but does not connect to a payment gateway. Customer notifications are locally stored drafts; they are not sent by SMS/email.

## 10. React service desk

The frontend supports:
- Repair intake for Apple/Samsung phones, tablets and laptops.
- Unlock requests for eligible phones and cellular tablets, requiring 15 numeric IMEI digits and a carrier/network.
- Stripe Elements checkout initiated by a server-created PaymentIntent.
- Private request tracking using both a reference and a separate one-time token.

The React frontend cannot be used for live requests until the Supabase URL/public key, Edge Function secrets, Stripe settings and (for unlocks) an actual supplier integration are configured. Save the private tracking token shown once after submission/payment; do not share it publicly.

## 11. Backups and audit

Use **Settings & Audit → Back Up Database** before major updates or database maintenance. Store a second copy away from the workstation. **Check Database Health** runs SQLite's integrity check. Audit entries document actions performed through the app; without named sessions, they are not a full multi-user access audit.

## 12. Firmware and security boundaries

Firmware inspection lists archive contents and calculates SHA-256 for Samsung `.tar`, `.tar.md5` and `.zip` files. It does not authenticate the supplier signature, prove official origin or verify exact-model/region/bootloader compatibility. Firmware writes are disabled. Use official manufacturer recovery procedures and only perform authorized service work. This app does not bypass Activation Lock, FRP/account verification, PIN/password controls or other device security.

## 13. Not yet connected

Named staff accounts and Owner/Manager/Technician/Front Desk/Viewer RBAC, e-signatures/waivers, full warranty returns, supplier purchase orders, actual SMS/email delivery, payment processing for repair invoices, multi-shop sync, encrypted document vault, AI agents and manufacturer-specific hardware test adapters are not connected in the current build. The private unlock backend also requires real supplier URLs/keys and sandbox evidence before live orders should be accepted.
