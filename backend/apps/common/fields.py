"""
Field-level AES-256-GCM encryption for financial / payroll columns (the 🔒 fields).

Ciphertext is stored as base64 text: base64(nonce[12] || ciphertext || tag[16]).
Because ciphertext is not SQL-aggregable, all SUM / Top-40 / ±5% math is performed
in Python after decrypt (acceptable for batch monthly data) — see apps.scoring.

Phase 1 (GCP): replace the raw env key with a KMS-wrapped DEK from Secret Manager.
"""
from __future__ import annotations

import base64
import os
from decimal import Decimal

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

_NONCE_BYTES = 12


def _load_key() -> bytes:
    raw = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if not raw:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\""
        )
    key = base64.urlsafe_b64decode(raw)
    if len(key) != 32:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must decode to 32 bytes (AES-256).")
    return key


def encrypt_str(plaintext: str) -> str:
    nonce = os.urandom(_NONCE_BYTES)
    blob = AESGCM(_load_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + blob).decode("ascii")


def decrypt_str(token: str) -> str:
    data = base64.b64decode(token)
    nonce, blob = data[:_NONCE_BYTES], data[_NONCE_BYTES:]
    return AESGCM(_load_key()).decrypt(nonce, blob, None).decode("utf-8")


class _EncryptedMixin:
    """Stores values as encrypted base64 text in a TextField column."""

    def get_internal_type(self):  # column type in the DB
        return "TextField"

    def get_prep_value(self, value):
        if value is None:
            return None
        return encrypt_str(self._to_str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return self._from_str(decrypt_str(value))

    def to_python(self, value):
        # Already-decrypted python value passes straight through.
        if value is None or isinstance(value, (Decimal, int, float)) and not isinstance(self, EncryptedCharField):
            return value
        return value

    # Subclasses convert between python value <-> str.
    def _to_str(self, value) -> str:  # pragma: no cover - trivial
        return str(value)

    def _from_str(self, value: str):  # pragma: no cover - trivial
        return value


class EncryptedCharField(_EncryptedMixin, models.Field):
    """Encrypted short text (e.g. National ID, employee name)."""


class EncryptedTextField(_EncryptedMixin, models.Field):
    """Encrypted long text."""


class EncryptedDecimalField(_EncryptedMixin, models.Field):
    """Encrypted monetary value. Use Decimal in app code; never aggregate in SQL."""

    def _to_str(self, value) -> str:
        return str(Decimal(value))

    def _from_str(self, value: str):
        return Decimal(value)
