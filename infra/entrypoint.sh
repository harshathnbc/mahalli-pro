#!/usr/bin/env bash
# Container entrypoint: ensure the schema + extensions + seed are in place, then serve.
# Idempotent — safe to run on every deploy/restart.
set -e

echo "→ Ensuring PostgreSQL extensions…"
python manage.py setup_extensions

echo "→ Applying migrations…"
python manage.py migrate --noinput

# RUN_SEED=1 (re)loads the official LCGPA seed data (ISIC / Etimad / thresholds).
if [ "${RUN_SEED:-0}" = "1" ]; then
  echo "→ Seeding LCGPA reference data…"
  python manage.py seed_lcgpa
fi

# ENABLE_RLS=1 turns on the strict tenant-isolation policies (production / role-separated DB).
if [ "${ENABLE_RLS:-0}" = "1" ]; then
  echo "→ Enabling Row-Level Security policies…"
  python manage.py enable_rls
  python manage.py install_audit_guard
fi

echo "→ Starting gunicorn…"
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-3}" --timeout 120
