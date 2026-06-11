# Mahalli Pro V4 — Database Schema & Deployment Plan

## Context

Mahalli Pro V4 is a multi-tenant SaaS that automates Saudi Arabia's LCGPA Local Content
certification. **Greenfield build** (empty repo). User wants (1) DB schema, (2) deployment steps,
(3) implementation approach. Confirmed: shared-schema + Postgres RLS tenancy; hosting **Phase 0 =
DigitalOcean (dev), Phase 1 = GCP Dammam `me-central2` (PDPL prod)**; next step = scaffold repo.

**This plan was revised after reviewing the real LCGPA source files** in `Documents/` and
`Documents/New folder/`. They materially change the schema vs. the architecture doc — see
*Reality-check deltas* below.

### ⚠️ Compliance flag
DigitalOcean has **no in-Kingdom region** → Phase 0 is **synthetic/dev data only**; real LCGPA
financial/payroll data is PDPL-legal only in Phase 1 (GCP Dammam). Vertex AI + Document AI run in
`me-central2` in **both** phases (Django calls out to GCP).

### Reality-check deltas (from the official files)
1. **Contract/Tender dimension is real.** Official templates exist at **Entity Level *and* Contract
   Level**, each with `Tender Name`, `Contract Start/End Date`, and in **Target vs Periodic/Final**
   variants. Reporting is two-dimensional: `(level: ENTITY|CONTRACT) × (type: TARGET|PERIODIC|FINAL)`.
2. **Section 5 = CAPEX** is a full section the architecture doc skipped. Real section order:
   S3 Labor → S4 Goods&Services → **S4.1 Extra Disclosure** → **S5 CAPEX** → S6 Capacity Building →
   S7 Depreciation → Appendix A → Appendix B.
3. **Appendix B** = sectors with an explicit baseline `Local Content Score (%)` (e.g.
   `4_SERVICES - KSA Security = 0.82`, `10_SERVICES - Finance = 0.75`). ~38 GOODS/SERVICES sectors.
4. **Mandatory list is keyed by Etimad commodity code** across ~17 Arabic sector sheets (Segment No,
   Etimad code, product Ar/En, description Ar/En). Matching purchased items = Etimad-code lookup, not
   fuzzy text.
5. **Minimum-threshold file** gives **per-year minimum LC %** (2026/2027/2028) + an `effective_date`
   per Etimad code. The "February 2026 threshold" is a row set, not a single number.
6. Real **labor multipliers** are explicit in the template (Saudi compensation ×1.0, foreign ×0.534).
7. Export targets the **actual templates** (`Local Content Score Template v2`, `Target LC Score
   Template (Entity/Contract)`, `Periodic/Final Report (Contract)`) — not the doc's "OM-LRG-02".

### Source files → system role
- `Local Content Score Template - v.2.xlsx` → master output template + cell-map (Template Vault).
- `Target LC Score Template (Entity/Contract) v1` → TARGET reports + the bidding/What-If simulator.
- `Periodic or Final Report Template (at Contract Level) v2` → PERIODIC/FINAL contract reports.
- `Mandatory List of Government Entities (Jan 2026).xlsx` → `etimad_commodity` seed (~thousands rows).
- `The minimum percentage ... February 2026.xlsx` → `mandatory_min_threshold` seed (per-year %).
- `Local Content Score Template`→`Appendix B` → `isic_sector` seed (baseline LC scores).
- `Updating the Methodology of Measuring the LC Score.pdf` → source of truth for the **math engine**.
- `Agreed-upon procedures for verifying local content (contract level) v4.docx` → the **±5% AUP /
  auditor checklist** logic.
- `New folder/*.pdf` (sample certs/regs) → corpus for **Document AI** training/validation + **RAG**.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + Tailwind, `next-intl` for RTL(ar)/LTR(en) dynamic switching |
| Backend | Django + DRF, Celery (async PDF/Excel parsing) |
| Parsing/Math | `openpyxl`/`pandas`, `Decimal` for money precision |
| DB | PostgreSQL 16 + `pgvector`, `pg_trgm` (fuzzy vendor name), `pgcrypto` |
| Cache/Queue | Redis (broker + cache + session) |
| Object storage | Phase 0: DO Spaces (S3) · Phase 1: GCS `me-central2` + CMEK |
| AI | Vertex AI Gemini + Document AI, `me-central2`, reached **only** via Django |
| Encryption | AES-256-GCM field-level (🔒), key in Secret Manager / KMS envelope |

---

## Database Schema

Two tiers: **GLOBAL** (no `tenant_id`, RLS-exempt) and **TENANT** (`tenant_id uuid NOT NULL`,
RLS-enforced). PKs `uuid`. 🔒 = AES-256 field-encrypted (aggregation done app-side; see notes).

### A. Global / Seed
- **isic_sector** — `code` (e.g. `4_SERVICES - KSA Security`), `name_en`, `name_ar`, `kind`
  (GOODS|SERVICES), `baseline_lc_score` (decimal), `description`, `compliance_year` *(Appendix B)*
- **etimad_commodity** — `etimad_code` (unique), `segment_no`, `sector_sheet`, `name_ar`, `name_en`,
  `desc_ar`, `desc_en`, `is_mandatory` *(Mandatory List, ~thousands of rows, trigram-indexed)*
- **mandatory_min_threshold** — `etimad_code` FK, `year` (2026/27/28), `min_pct`, `effective_date`
- **global_whitelist_entry** — `vat_number` (uniq), `cr_number`, `vendor_name_norm` (trgm), `lc_score`,
  `certificate_expiry_date`, `financial_year`, `version`, `source_cert_sha256`, `verified_at`,
  `_source_tenant_id` *(internal-only)*. Conflict-resolution: reject regressions, auto-apply
  highest-validity, notify. Seeded with SABIC/Aramco/STC.
- **template_vault** — `template_key` (LC_SCORE_V2|TARGET_ENTITY|TARGET_CONTRACT|PERIODIC_CONTRACT),
  `compliance_year`, `file_ref`, `uploaded_by` *(Master Admin)*
- **template_cell_mapping** — `template_id`, `system_variable`, `sheet_name`, `cell_coordinate`

### B. Tenancy & Identity (Module 1)
- **tenant** — `name`, `primary_cr_number`, `subscription_tier`, `status` (ACTIVE|HOLD),
  `billing_status` (FULLY_PAID|PARTIAL|DELAYED), `max_employees`, `max_vendors`
- **tenant_branch** — `tenant_id`, `cr_number`, `is_main`, `label` *(Multi-CR consolidation)*
- **compliance_year** — `tenant_id`, `year`, `is_paid`, `state` (OPEN|LOCKED), `locked_at`
- **company_profile** — `tenant_id`, `cr_number`(10-digit), `zatca_vat`(15-digit `3…3`),
  `national_address_wasel`(`^[A-Z]{4}\d{4}$`), `isic_sector_id`, `consolidates_multi_cr`
- **contract** — `tenant_id`, `compliance_year_id`, `tender_name`, `gov_entity`, `start_date`,
  `end_date`, `cr_scope` *(NEW: enables Contract-Level reporting)*
- **app_user** — Django user + `tenant_id?`(null=Master Admin), `role` (MASTER_ADMIN|SUPER_ADMIN|
  COMPANY_ADMIN|HR_ADMIN|PROCUREMENT_ADMIN|FINANCE_ADMIN)
- **subscription** — `tenant_id`, `tier`, `paid_years[]`, `payment_status`, `hold_flag`
- **audit_log** — `actor_user_id`, `tenant_id?`, `action`(CRUD), `entity_type`, `entity_id`,
  `before`/`after` jsonb, `ip`, `ts` — **append-only** (trigger blocks UPDATE/DELETE)
- **ghost_login_session** — `master_admin_id`, `target_tenant_id`, `started_at`, `ended_at`

### C. HR & Labor — Section 3 & 6 (Module 2)
- **hr_monthly_upload** — `tenant_id`, `compliance_year_id`, `month` 1–12, `status` *(12 slots)*
- **gosi_certificate** — `hr_monthly_upload_id`, `branch_id`, `file_ref`, `saudi_headcount`,
  `expat_headcount`, `parsed_at` *(summed across branches)*
- **payroll_row** — `hr_monthly_upload_id`, `national_id`🔒, `name`🔒, `gender`, `nationality`,
  `status`(ACTIVE|VACATION), `classification`(REGULAR|TRAINEE), `basic`🔒, `housing`🔒, `transport`🔒,
  `bonus_vacation_pay`🔒, `eosb_accrual`🔒, `section3_amount`🔒, `section6_amount`🔒
  *(Trainee → salary auto-shifted S3→S6; Saudi×1.0 / foreign×0.534 multipliers from config)*
- *Validation:* `count(payroll_row) == saudi+expat headcount`

### D. Procurement — Section 4 (Module 3)
- **proc_monthly_upload** — `tenant_id`, `compliance_year_id`, `contract_id?`, `month`, `raw_file_ref`
- **column_mapping** — `tenant_id`, `source_field_name`, `system_field` *(memorized per tenant)*
- **vendor** — `tenant_id`, `name`, `cr_number`(Unified National Number), `vat_number`,
  `classification`(LOCAL|FOREIGN via ZATCA `3…3`), `verified_lc_score`,
  `lc_score_source`(CERT|GLOBAL_WHITELIST|BASELINE), `global_whitelist_id?`
- **invoice** — `proc_monthly_upload_id`, `vendor_id`, `invoice_number`, `vat_number`,
  `gross_amount`🔒, `vat_amount`🔒, `net_eligible_spend`🔒
- **invoice_line** — `invoice_id`, `description`, `etimad_code?`, `goods_or_services`(GOODS|SERVICES),
  `local_or_foreign`, `factory_manufactured`(bool), `isic_sector_id?`, `audited_score?`
  *(real S4 columns; drives mandatory-list + threshold checks)*
- **vendor_lcgpa_certificate** — `vendor_id`, `file_ref`, `parsed_vendor_name`, `parsed_cr_vat`,
  `parsed_lc_score`, `expiry_date`, `is_expired`, `doc_ai_json` *(OCR-only; feeds global_whitelist)*
- **top_vendor_selection** — `tenant_id`, `compliance_year_id`, `selected_vendor_ids[]`,
  `computed_lc_score`, `manual_override` *(Top-40 / 70% optimizer)*
- **compliance_warning** — `tenant_id`, `compliance_year_id`, `type`(MANDATORY_FOREIGN|THRESHOLD),
  `etimad_code?`, `vendor_id?`, `message`, `raised_at`

### E. CAPEX — Section 5 (NEW)
- **capex_item** — `tenant_id`, `compliance_year_id`, `contract_id?`, `asset_type`, `description`,
  `supplier_name`, `supplier_cr`, `goods_or_services`, `local_or_foreign`, `factory_manufactured`,
  `isic_sector_id?`, `amount`🔒, `audited_score?`

### F. Finance — Appendix A (Module 4)
- **monthly_soft_close** — `tenant_id`, `compliance_year_id`, `month`, `total_salaries`🔒,
  `total_purchases`🔒, `hr_variance`, `proc_variance`
- **annual_hard_close** — `tenant_id`, `compliance_year_id`, `revenues`🔒, `direct_costs`🔒, `gna`🔒,
  `selling_distribution`🔒, `finance_costs`🔒, `state`, `reconciliation_passed`
- **trial_balance_upload** — `tenant_id`, `compliance_year_id`, `raw_file_ref`
- **tb_account_mapping** — `trial_balance_id`, `account_code`, `account_name`,
  `mapped_category`(incl. exemptions ZAKAT|CUSTOMS|VISA_FEES), `amount`🔒
- **reconciliation_check** — `tenant_id`, `compliance_year_id`, `scope`(MONTHLY|ANNUAL),
  `variance_pct`, `passed` *(±5% Strict Block)*
- **evidence_vault** — `tenant_id`, `compliance_year_id`, `doc_type`(FIN_STATEMENTS_PDF|TB_EXCEL|
  GOSI_PDF), `file_ref`

### G. Assets / Depreciation — Section 7 (Module 5)
- **asset_register_upload** — `tenant_id`, `compliance_year_id`, `file_ref`
- **asset** — `asset_register_id`, `asset_class`, `supplier_cr`, `origin`, `local_or_foreign`,
  `annual_depreciation`🔒, `operating_in_ksa`(bool), `included_in_score`
  *(±5% vs TB depreciation)*

### H. Reports, Exports & Advisory (Module 8 + Module 10 hashing)
- **lc_report** — `tenant_id`, `compliance_year_id`, `contract_id?`, `level`(ENTITY|CONTRACT),
  `type`(TARGET|PERIODIC|FINAL|SCORE), `state`, `computed_score` jsonb *(per-section breakdown)*
- **export_artifact** — `lc_report_id`, `kind`(SCORE_XLSX|TARGET_XLSX|PERIODIC_XLSX|AUDIT_PACK_ZIP),
  `file_ref`, `sha256_hash`, `generated_at` *(hash logged to audit_log)*
- **simulator_scenario** — `tenant_id`, `scope`(SUPERADMIN|PROCUREMENT|HR), `inputs`/`result` jsonb
  *(siloed What-If / 10% price-preference Bidding Power)*

### I. AI Copilot / RAG (Module 9)
- **knowledge_document** — `title`, `category`(LCGPA|ZATCA|HR|FINANCE|PROCUREMENT), `is_global`,
  `tenant_id?`
- **document_chunk** — `knowledge_document_id`, `content`, `embedding vector(768)` (pgvector
  HNSW/IVFFlat), `category`(RBAC filter), `tenant_id?`
- **copilot_conversation** / **copilot_message** — `user_id`, `tenant_id`, `role`, `content`,
  `retrieved_chunk_ids[]`

### J. Integration roadmap (Module 10 — stubs)
- **auditor_portal_link** — `tenant_id`, `compliance_year_id`, `token`, `expires_at`, `read_only`
- **webhook_endpoint** / **api_key** — `tenant_id`, `url`/`hashed_key`, `secret`, `events[]`, `scopes`

### Cross-cutting DB mechanics
- **RLS:** every TENANT table policy `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`.
  Django middleware sets the GUC per request from JWT. Master Admin uses a privileged RLS-bypass role
  (control center + ghost login). RLS is the wall *under* DRF RBAC.
- **Encryption:** 🔒 = AES-256-GCM; ciphertext isn't SQL-aggregable, so SUM/Top-40/±5% run in Python
  after decrypt (fine for batch monthly data). Key in Secret Manager (Phase 1: KMS-wrapped DEK).
- **Files** never stored as DB blobs — `file_ref` → object storage; rows hold parsed results only.
- **Math engine** (`apps/scoring`) encodes the Methodology PDF formulas + the AUP ±5% checks;
  multipliers/thresholds come from seed tables, not hard-coded.

---

## Deployment Steps

### Phase 0 — DigitalOcean (dev/MVP, synthetic data only)
1. DO Managed PostgreSQL 16; enable `pgvector`, `pg_trgm`, `pgcrypto`.
2. DO Spaces bucket (S3) for PDFs/Excel/zip; server-side encryption on.
3. GCP `me-central2`: enable Vertex AI + Document AI, create a Document AI processor, SA JSON for Django.
4. Redis (DO Managed or container).
5. Containers (DO App Platform or Droplet + `docker-compose`): `web`(gunicorn), `worker`(Celery),
   `beat`, `frontend`(Next.js), `nginx`.
6. Secrets via env: DB URL, Redis URL, **AES master key**, GCP SA key, Spaces creds.
7. `migrate` → **seed**: Appendix B → `isic_sector`; Mandatory List → `etimad_commodity`;
   min-% file → `mandatory_min_threshold`; seed suppliers → `global_whitelist`; blank templates +
   cell maps → `template_vault`; create first Master Admin.
8. CI/CD: GitHub Actions → build → push registry → deploy. Health `/healthz`.

### Phase 1 — GCP Dammam `me-central2` (PDPL production)
1. Cloud SQL for PostgreSQL (or AlloyDB for pgvector) in `me-central2`, private IP/VPC; enable extensions.
2. GCS bucket `me-central2` + CMEK (Cloud KMS); migrate Spaces objects.
3. Cloud KMS (AES envelope key) + Secret Manager (all secrets).
4. Cloud Run (Django + Next.js); Cloud Tasks/Pub-Sub (async); Memorystore Redis.
5. Migrate DO→Cloud SQL (`pg_dump`/restore or DMS); re-key 🔒 fields under KMS.
6. Point Django at private Vertex/Document AI endpoints; cutover DNS.
7. Cloud Monitoring/Logging, automated backups + PITR, VPC-SC perimeter.

---

## Repo Scaffold (approved next step)

```
mahalli-pro/
  backend/
    config/                 # 12-factor settings (django-environ), wsgi/asgi, celery
    apps/
      common/               # EncryptedField, RLS middleware, CR/VAT/Wasel validators
      tenancy/  accounts/  audit/  seed/  scoring/   # scoring = math engine
      hr/  procurement/  capex/  finance/  assets/  reports/  copilot/  integrations/
    manage.py  pyproject.toml
  frontend/                 # Next.js + Tailwind + next-intl (RTL/LTR)
  infra/  docker-compose.yml  Dockerfile.backend  Dockerfile.frontend  terraform/
  docs/                     # copy of LCGPA source files for reference
```

**Build order:** scaffold → `tenancy`+`accounts`+RLS+`audit` → `seed` (parse the 4 official xlsx into
fixtures) → `scoring` math engine (from Methodology PDF, validated against the sample templates) →
Procurement vertical slice (upload→map→Etimad/threshold→Doc AI→global_whitelist→Top-40) → HR, CAPEX,
Finance, Assets, Reports/Exports, Copilot.

---

## Verification

- `docker-compose up`; `migrate`+`seed` load Appendix B sectors, Etimad commodities, thresholds; `/healthz` green.
- **RLS isolation:** 2 tenants; A cannot read B (API + raw SQL).
- **Validators:** CR 10-digit, VAT 15-digit `3…3`, Wasel `^[A-Z]{4}\d{4}$` reject bad input.
- **Seed correctness:** spot-check e.g. `4_SERVICES - KSA Security = 0.82`; a known Etimad code resolves
  to its 2026/2027 min %.
- **Doc AI:** upload a sample cert PDF (from `New folder/`) → structured JSON → vendor + global_whitelist
  updated; older cert rejected with "newer version exists".
- **Scoring:** feed a filled sample template's inputs → engine reproduces its section scores; trainee
  salary moves S3→S6; foreign labor ×0.534.
- **Mandatory check:** invoice line with a mandatory Etimad code from a FOREIGN vendor → Compliance Warning.
- **Reconciliation:** >5% variance → export blocked (Red Light); within ±5% → unlocks.
- **Export integrity:** generate Audit Pack → SHA-256 recorded in audit_log and re-verifiable; output
  matches the official template cell-map.
- **Master Admin:** wizard creates tenant + Super Admin; Soft Hold logs users out; Ghost Login logged.
