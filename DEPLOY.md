# Deploying Mahalli Pro — Phase 0 (developing stage)

**Frontend → Vercel · Backend + DB → DigitalOcean · Domain → mahallipro.com**

> ⚠️ **PDPL note.** DigitalOcean has no in-Kingdom region, so this stage is for
> **development with synthetic data only**. Real LCGPA data must wait for the
> in-Kingdom (GCP Dammam) move. Vertex AI / Document AI features stay disabled until
> you add GCP credentials.

Target topology:

| Host | Component | Domain |
|---|---|---|
| Vercel | Next.js frontend | `mahallipro.com`, `www.mahallipro.com` |
| DO App Platform | Django API (Docker) | `api.mahallipro.com` |
| DO Managed Postgres | Database (pgvector) | — |
| DO Spaces | Uploaded PDFs/Excel/zip | — |

---

## 1. Generate the secrets you'll need

```bash
# Django secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"
# Field encryption key (AES-256) — KEEP THIS SAFE; losing it makes 🔒 data unreadable
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

## 2. DigitalOcean — Managed Postgres

1. **Databases → Create → PostgreSQL 16**. Pick a *Managed Database cluster* (not the
   free trial dev DB — the cluster is required for the `vector` extension). Region:
   Frankfurt (`fra1`).
2. After it's up, note the connection string. The entrypoint runs
   `setup_extensions` automatically (creates `vector`, `pg_trgm`, `pgcrypto`).

## 3. DigitalOcean — Spaces (object storage for uploads)

1. **Spaces → Create** a bucket, e.g. `mahalli-dev`, region `fra1`.
2. **API → Spaces Keys → Generate** an access key/secret. Save both.

## 4. DigitalOcean — App Platform (the API)

Option A (dashboard): **Apps → Create → GitHub → `harshathnbc/mahalli-pro`**, branch
`main`. It detects `infra/Dockerfile.backend`. Attach the Managed Postgres from step 2.

Option B (spec): edit `.do/app.yaml` and import it (**Create → Import App Spec**).

Then set these **environment variables** (mark the secrets as *encrypted*):

| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | (from step 1) — secret |
| `FIELD_ENCRYPTION_KEY` | (from step 1) — secret |
| `DATABASE_URL` | `${db.DATABASE_URL}` (bind the attached DB) |
| `DJANGO_ALLOWED_HOSTS` | `*` (tighten later) |
| `SECURE_SSL_REDIRECT` | `False` |
| `CSRF_TRUSTED_ORIGINS` | `https://api.mahallipro.com,https://mahallipro.com,https://www.mahallipro.com` |
| `CORS_ALLOWED_ORIGINS` | `https://mahallipro.com,https://www.mahallipro.com` |
| `CELERY_TASK_ALWAYS_EAGER` | `True` |
| `RUN_SEED` | `1` (loads LCGPA seed on first deploy; set `0` after) |
| `STORAGE_BACKEND` | `s3` |
| `STORAGE_BUCKET` | `mahalli-dev` |
| `STORAGE_ENDPOINT_URL` | `https://fra1.digitaloceanspaces.com` |
| `STORAGE_REGION` | `fra1` |
| `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | (from step 3) — secret |

Deploy. The container entrypoint runs `setup_extensions → migrate → seed_lcgpa`, then
gunicorn. Health check: `GET /healthz`.

**Create the first Master Admin** (App Platform → your app → **Console**):

```bash
python manage.py createsuperuser   # then, in shell, set role:
python manage.py shell -c "from apps.accounts.models import User,Role; u=User.objects.get(username='<email>'); u.role=Role.MASTER_ADMIN; u.save()"
```

## 5. DNS — point the domain

In your DNS provider for `mahallipro.com`:

- `api` → **CNAME**/A to the App Platform domain (App settings → Domains → add
  `api.mahallipro.com`, DO shows the target).
- root `@` and `www` → Vercel (step 6 shows the exact records).

## 6. Vercel — the frontend

1. **Add New → Project → import `harshathnbc/mahalli-pro`**.
2. **Root Directory: `frontend`** (important — the repo is a monorepo).
3. Framework preset: **Next.js** (auto).
4. Environment variable: `NEXT_PUBLIC_API_BASE_URL = https://api.mahallipro.com/api`.
5. Deploy, then **Settings → Domains → add `mahallipro.com` + `www.mahallipro.com`**
   and follow Vercel's DNS instructions.

## 7. Smoke test

```bash
curl https://api.mahallipro.com/healthz                      # {"status":"ok"}
# Provision a tenant as Master Admin, then log in at https://mahallipro.com
```

Open `https://mahallipro.com` → you should land on `/ar` (toggle to `/en`), log in,
and reach the role-aware dashboard.

---

## What's intentionally deferred for this stage

- **Strict DB RLS** (set `ENABLE_RLS=1` only once you run the API as a non-owner
  Postgres role — see `infra/db/init/01-extensions.sql`). For now tenant isolation
  is enforced at the application layer (`TenantScopedViewSet`).
- **Redis + Celery worker** — tasks run inline (`CELERY_TASK_ALWAYS_EAGER`). Add a
  worker + Managed Redis when uploads get large.
- **Document AI / Copilot** — set `GCP_PROJECT_ID`, `DOCAI_PROCESSOR_ID`, and mount a
  service-account JSON to enable; they no-op/error cleanly until then.

## Production (Phase 1, in-Kingdom)

Move to **GCP Dammam `me-central2`**: Cloud SQL/AlloyDB (private IP) + `STORAGE_BACKEND=gcs`
bucket with CMEK, run the API as a non-owner role with `ENABLE_RLS=1`, and migrate
encrypted fields under Cloud KMS. See `docs/PLAN.md`.
