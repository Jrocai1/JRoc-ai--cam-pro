# J-Roc AI Mobile Repair — Feature Matrix

**Supported scope is fixed for this product:** Apple and Samsung devices only, limited to phones, tablets and laptops. Other manufacturers and device types are not accepted by the desktop intake or public request API.

| Brand | Phone | Tablet | Laptop |
|---|---|---|---|
| Apple | iPhone | iPad | MacBook |
| Samsung | Galaxy phones | Galaxy Tab | Galaxy Book |

Carrier unlock is available only for eligible phones and cellular tablets, with a strict 15-digit numeric IMEI. Laptops use repair/diagnostics intake; they do not use IMEI-based carrier unlock checkout.

## Desktop repair-management core

| Area | Current state | Notes |
|---|---|---|
| Local data store | Implemented | SQLite under the current Windows user's LocalAppData |
| Customer records | Implemented | Contact, address, notes and communication preferences |
| Device registry | Implemented, scoped | Apple/Samsung only; Phone/Tablet/Laptop only |
| Repair tickets | Implemented | Job number, complaint, notes, priority, status and customer/device linkage |
| Diagnostics | Implemented, basic | Diagnostic findings and next-action notes; read-only ADB/Fastboot/USB discovery |
| Technician directory | Implemented, limited | Records and job assignment; no login or enforced roles |
| Estimates | Implemented, basic | Data layer supports line items; current desktop GUI creates one line per estimate |
| Customer authorization | Manual/basic | Approval state recorded; e-signature/waiver workflow planned |
| Parts and inventory | Implemented | SKU, stock counts, thresholds, costs, movements and job consumption |
| Repair work logs | Implemented | Work performed and duration |
| Quality control | Implemented, basic | Per-test pass/fail and notes; no model-specific automated tests |
| Invoices and payments | Implemented, basic | Invoice from approved estimate, partial/full payments; no payment gateway |
| Warranty/service cases | Basic implemented | Link to original job, optional follow-up job, terms, expiry and status |
| Notifications | Draft-only | Local queue only; no SMS/email sent |
| Owner dashboard | Implemented, basic | Open jobs, approvals, QC, low stock, payments today and outstanding balance |
| Reports | Implemented, basic | Summary and CSV job export |
| Audit history | Implemented, local | Important data-layer changes; not multi-user identity auditing |
| Backup/integrity | Implemented | SQLite backup and integrity check |
| Desktop firmware inspection | Implemented, read-only | Archive inventory/SHA-256; no authenticity verification |
| React frontend | Implemented, development baseline | Responsive request UI for Apple/Samsung Phone/Tablet/Laptop |
| Supabase repair requests | Implemented in source | Private Edge Function insert path; deployment and secrets must be configured |
| Stripe Elements checkout | Implemented in source | Unlock PaymentIntent is server-created; live account/configuration not supplied |
| Private request lookup | Implemented in source | Requires reference plus a separate high-entropy customer token |
| Supplier unlock webhook/polling | Implemented in source | Requires a real supplier's HTTPS API contract and secrets |
| 15-minute cron schedule | SQL provided | Invoke polling Edge Function via pg_cron/pg_net/Vault; must be configured in project |
| Samsung Download Mode flashing | Not implemented | No firmware partition writes |
| Apple device restore automation | Not implemented | Use official supported recovery procedures; no proprietary service API integration claimed |
| Multi-user login/RBAC | Planned | Current desktop is a local owner-workstation build |
| Multi-shop sync/cloud admin | Planned | No multi-location synchronization or staff admin portal |
| Electronic waiver/signatures | Planned | Not implemented in current release |
| Real SMS/email | Planned | Notification drafts only |
| Supplier purchase order system | Planned | Not implemented |
| AI repair agent integrations | Planned | No live AI technician/front desk/inventory agents connected |
| Encrypted vault/secure erasure | Planned | Requires separate security design and verification |

## Repair lifecycle

Customer → Device → Intake → Job → Diagnostics → Diagnosis → Estimate → Customer Approval → Parts/Inventory → Technician Assignment → Repair → QC → Notification → Invoice/Payment → Device Return → Reporting.

## Security and release guardrails

- Enforce brand and device-type scope in both frontend and server-side validation.
- RLS remains enabled on exposed request tables; public clients do not get direct table grants.
- Never expose Supabase service-role/secret keys, Stripe secrets, webhook secrets, wholesaler keys or cron secrets to the browser.
- A reference by itself is insufficient to read a request; use a separate high-entropy private token.
- Use official firmware and validate exact-model compatibility independently. A SHA-256 digest is not authenticity verification.
- No Activation Lock, FRP/account-lock, PIN/password or other security bypasses.
- CI success is not the same as supplier sandbox testing, live Stripe testing or hardware-in-the-loop validation.
