"""
Enterprise Integration Layer services (Module 10).

  • Certified Auditor Portal (Phase 2): time-limited, read-only viewing links so an
    external CPA verifies the SHA-256 audit-pack hashes and signs off in-app, instead
    of emailing a .zip.
  • ERP API Gateway (Phase 2 roadmap): HMAC-signed webhooks + hashed API keys for
    future Odoo/SAP/Dynamics/Microtec integrations.

Crypto helpers (HMAC signature, key hashing, expiry check) are pure & unit-testable.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.utils import timezone

from apps.integrations.models import ApiKey, AuditorPortalLink, WebhookEndpoint
from apps.reports.models import ExportArtifact


# --- Pure crypto helpers ------------------------------------------------------
def sign_payload(secret: str, payload: bytes) -> str:
    """HMAC-SHA256 webhook signature (hex), verifiable by the receiver."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_payload(secret, payload), signature)


def hash_api_key(raw_key: str) -> str:
    """Store only the hash; the raw key is shown to the user once."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, hashed_key). Raw is 'mp_' + 40 hex chars."""
    raw = "mp_" + secrets.token_hex(20)
    return raw, hash_api_key(raw)


def link_is_valid(link: AuditorPortalLink, now=None) -> bool:
    """A portal link is usable only before its expiry."""
    now = now or timezone.now()
    return link.expires_at > now


# --- Auditor portal -----------------------------------------------------------
def create_auditor_link(*, tenant, compliance_year, created_by, ttl_hours: int = 72) -> AuditorPortalLink:
    return AuditorPortalLink.objects.create(
        tenant=tenant,
        compliance_year=compliance_year,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
        read_only=True,
        created_by=created_by,
    )


def artifact_hashes(compliance_year) -> list[dict]:
    """The SHA-256 hashes an external auditor verifies against the delivered files."""
    artifacts = ExportArtifact.objects.filter(report__compliance_year=compliance_year)
    return [{"kind": a.kind, "sha256": a.sha256_hash, "generated_at": a.generated_at} for a in artifacts]


def verify_artifact_hash(compliance_year, provided_sha256: str) -> bool:
    """Confirm a hash the auditor computed matches a stored artifact hash."""
    return ExportArtifact.objects.filter(
        report__compliance_year=compliance_year, sha256_hash=provided_sha256
    ).exists()


# --- API keys -----------------------------------------------------------------
def issue_api_key(*, tenant, label: str, scopes: list[str]) -> tuple[ApiKey, str]:
    raw, hashed = generate_api_key()
    key = ApiKey.objects.create(tenant=tenant, hashed_key=hashed, label=label, scopes=scopes)
    return key, raw


def resolve_api_key(raw_key: str) -> ApiKey | None:
    return ApiKey.objects.filter(hashed_key=hash_api_key(raw_key), is_active=True).first()
