"""
Production settings. Phase 1 target: GCP Dammam (me-central2), PDPL-compliant.
Object storage = GCS bucket in-region with CMEK; secrets from Secret Manager.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Security headers / HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Object storage -> GCS (django-storages). Bucket pinned to me-central2 + CMEK.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": env("STORAGE_BUCKET"),
            "location": env("GCP_LOCATION", default="me-central2"),
        },
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
