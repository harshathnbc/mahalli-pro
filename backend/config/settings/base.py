"""
Base settings for Mahalli Pro V4.

Hosting-portable (12-factor): everything env-driven so the Phase 0 (DigitalOcean)
deployment lifts cleanly to Phase 1 (GCP Dammam me-central2). See .env.example.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend

env = environ.Env()
# Load backend/.env if present (dev convenience; prod uses real env vars).
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# --- Applications ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]
LOCAL_APPS = [
    "apps.common",
    "apps.tenancy",
    "apps.accounts",
    "apps.audit",
    "apps.seed",
    "apps.hr",
    "apps.procurement",
    "apps.capex",
    "apps.finance",
    "apps.assets",
    "apps.reports",
    "apps.copilot",
    "apps.integrations",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Sets `app.current_tenant_id` GUC per request so Postgres RLS isolates tenants.
    "apps.common.middleware.RowLevelSecurityMiddleware",
    # Writes a row to the immutable Master Audit Log for every mutating request.
    "apps.audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database (PostgreSQL + pgvector). App role is non-superuser => RLS enforced. ---
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://mahalli_app:app_pw@localhost:5432/mahalli"),
}
# Optional privileged connection (RLS bypass) for the Master Admin control center.
# When configured, master-plane querysets run on this alias to read across tenants.
ADMIN_DATABASE_URL = env("DATABASE_URL_ADMIN", default=None)
if ADMIN_DATABASE_URL:
    DATABASES["admin"] = env.db("DATABASE_URL_ADMIN")
    MASTER_DB_ALIAS = "admin"
else:
    MASTER_DB_ALIAS = "default"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n: Arabic (RTL) + English (LTR) ---
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("ar", "Arabic")]
TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- DRF + JWT ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

# --- Celery ---
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_TRACK_STARTED = True

# --- Field-level AES-256-GCM encryption key (financial / payroll columns) ---
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# --- LCGPA domain constants (overridable; source = methodology PDF / templates) ---
LCGPA = {
    "SAUDI_LABOR_MULTIPLIER": 1.0,
    "FOREIGN_LABOR_MULTIPLIER": 0.534,
    "RECONCILIATION_TOLERANCE": 0.05,  # ±5% strict block
    "TOP_VENDOR_COVERAGE": 0.70,       # 70% reporting rule
    "PRICE_PREFERENCE": 0.10,          # 10% government bid preference
}

# --- Google Cloud (Vertex AI + Document AI, me-central2 in both phases) ---
GCP = {
    "PROJECT_ID": env("GCP_PROJECT_ID", default=""),
    "LOCATION": env("GCP_LOCATION", default="me-central2"),
    "DOCAI_PROCESSOR_ID": env("DOCAI_PROCESSOR_ID", default=""),
    "EMBEDDING_MODEL": env("VERTEX_EMBEDDING_MODEL", default="text-embedding-004"),
    "GENERATIVE_MODEL": env("VERTEX_GENERATIVE_MODEL", default="gemini-1.5-flash"),
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
