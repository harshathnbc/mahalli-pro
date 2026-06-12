"""
Production settings.

Phase 0 (developing stage): backend on DigitalOcean App Platform, frontend on
Vercel, media on DO Spaces (S3-compatible). NOT PDPL-compliant (no in-Kingdom
region) — synthetic data only.
Phase 1: GCP Dammam (me-central2) — set STORAGE_BACKEND=gcs.

Everything is env-driven so the same image runs in both phases.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Behind the App Platform / load-balancer TLS terminator.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Dev-stage: run Celery tasks inline (no separate worker / Redis) unless configured.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

# --- Media/object storage (selectable) ---------------------------------------
STORAGE_BACKEND = env("STORAGE_BACKEND", default="s3")  # s3 | gcs | local

if STORAGE_BACKEND == "s3":
    # DO Spaces (S3-compatible). App Platform disk is ephemeral, so uploads MUST
    # go to external object storage.
    AWS_ACCESS_KEY_ID = env("STORAGE_ACCESS_KEY", default="")
    AWS_SECRET_ACCESS_KEY = env("STORAGE_SECRET_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("STORAGE_BUCKET", default="")
    AWS_S3_ENDPOINT_URL = env("STORAGE_ENDPOINT_URL", default="")
    AWS_S3_REGION_NAME = env("STORAGE_REGION", default="")
    AWS_DEFAULT_ACL = "private"
    AWS_QUERYSTRING_AUTH = True
    default_storage_cfg = {"BACKEND": "storages.backends.s3.S3Storage"}
elif STORAGE_BACKEND == "gcs":
    default_storage_cfg = {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": env("STORAGE_BUCKET"),
            "location": env("GCP_LOCATION", default="me-central2"),
        },
    }
else:  # local (ephemeral — dev/testing only)
    default_storage_cfg = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": default_storage_cfg,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
