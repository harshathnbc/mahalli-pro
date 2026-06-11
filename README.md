# Mahalli Pro V4 — LCGPA Local Content SaaS

Multi-tenant platform that automates Saudi Arabia's LCGPA Local Content
certification. Backend: **Django + DRF + Celery**. Frontend: **Next.js + Tailwind**
with dynamic Arabic (RTL) / English (LTR). Database: **PostgreSQL + pgvector**,
shared-schema multi-tenancy enforced by **Row-Level Security**, with **AES-256-GCM**
field-level encryption on all financial/payroll columns.

> **PDPL note.** Phase 0 runs on DigitalOcean for development with **synthetic data
> only** (no in-Kingdom region). Real LCGPA financial/payroll data is PDPL-legal only
> in **Phase 1 (GCP Dammam `me-central2`)**. Vertex AI + Document AI run in
> `me-central2` in both phases.

## Layout

```
backend/   Django project (config/ + apps/*)
frontend/  Next.js App Router, next-intl RTL/LTR
infra/     docker-compose, Dockerfiles, db init SQL
docs/      planning notes + docs/lcgpa/ (official LCGPA source workbooks)
```

### Backend apps
`common` (RLS, encrypted fields, validators) · `tenancy` · `accounts` (RBAC, ghost
login) · `audit` (append-only log) · `seed` (ISIC / Etimad / thresholds / global
whitelist / templates) · `scoring` (math engine) · `hr` · `procurement` · `capex` ·
`finance` · `assets` · `reports` · `copilot` (pgvector RAG) · `integrations`.

## Quick start (Docker, Phase 0)

```bash
cp .env.example backend/.env          # then set FIELD_ENCRYPTION_KEY (see below)
docker compose -f infra/docker-compose.yml up --build
```

Postgres comes up with `pgvector`, `pg_trgm`, `pgcrypto` (see `infra/db/init`).
Then, in the `web` container:

```bash
python manage.py migrate
python manage.py enable_rls            # install tenant-isolation RLS policies
python manage.py install_audit_guard   # make the audit log append-only
python manage.py seed_lcgpa --source-dir ../docs/lcgpa
python manage.py createsuperuser        # first Master Admin
```

Frontend: `cd frontend && npm install && npm run dev` → http://localhost:3000
(redirects to `/ar`; toggle to `/en`). API: http://localhost:8000/api, health
at `/healthz`.

## Local backend without Docker

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate      # Windows; use bin/activate on *nix
pip install -r requirements.txt
# Generate an encryption key:
python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# Put it in backend/.env as FIELD_ENCRYPTION_KEY, point DATABASE_URL at a local PG, then:
python manage.py migrate && python manage.py enable_rls && python manage.py install_audit_guard
python manage.py seed_lcgpa
python manage.py runserver
```

## Seed data (from the official LCGPA workbooks)

`seed_lcgpa` parses `docs/lcgpa/`:

| Source file | Table |
|---|---|
| `Local Content Score Template - v.2.xlsx` → Appendix B | `IsicSector` (baseline LC scores) |
| `Mandatory List of Government Entities (January 2026).xlsx` | `EtimadCommodity` |
| `The minimum percentage ... February 2026.xlsx` | `MandatoryMinThreshold` (per-year %) |
| built-in (SABIC / Aramco / STC) | `GlobalWhitelistEntry` |

## Security model

- **RLS** isolates tenants at the database. App connects as a non-superuser; the
  `RowLevelSecurityMiddleware` sets `app.current_tenant_id` per request. The Master
  Admin uses a privileged RLS-bypass role (control center + ghost login).
- **RBAC** (DRF) is the department "cryptographic wall": HR↔§3/6, Procurement↔§4,
  Finance↔Appendix A/§7; cross-department visibility is denied.
- **Encryption**: `apps/common/fields.py` (AES-256-GCM). 🔒 columns are not
  SQL-aggregable, so all SUM / Top-40 / ±5% math runs in `apps/scoring` after decrypt.

## Phase 1 — GCP Dammam (`me-central2`) production

Cloud SQL / AlloyDB (pgvector, private IP) · GCS bucket + CMEK via Cloud KMS · Cloud
Run (web + frontend) · Cloud Tasks / Pub-Sub · Memorystore Redis · Secret Manager.
`config/settings/prod.py` switches storage to GCS. Migrate DO→Cloud SQL and re-key
🔒 fields under KMS. See `docs/` plan for the full runbook.
