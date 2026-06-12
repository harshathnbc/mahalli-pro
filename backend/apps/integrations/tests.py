"""Pure-logic tests for the Integration Layer crypto helpers (no DB)."""
import datetime as dt

from django.test import SimpleTestCase

from apps.integrations.services import (
    generate_api_key,
    hash_api_key,
    sign_payload,
    verify_signature,
)


class WebhookSignatureTests(SimpleTestCase):
    def test_sign_and_verify_roundtrip(self):
        payload = b'{"event":"export.ready"}'
        sig = sign_payload("s3cr3t", payload)
        self.assertTrue(verify_signature("s3cr3t", payload, sig))

    def test_wrong_secret_fails(self):
        payload = b"data"
        sig = sign_payload("right", payload)
        self.assertFalse(verify_signature("wrong", payload, sig))

    def test_tampered_payload_fails(self):
        sig = sign_payload("k", b"original")
        self.assertFalse(verify_signature("k", b"tampered", sig))


class ApiKeyTests(SimpleTestCase):
    def test_generate_prefix_and_hash(self):
        raw, hashed = generate_api_key()
        self.assertTrue(raw.startswith("mp_"))
        self.assertEqual(hashed, hash_api_key(raw))
        self.assertNotEqual(raw, hashed)

    def test_keys_are_unique(self):
        self.assertNotEqual(generate_api_key()[0], generate_api_key()[0])


class LinkExpiryTests(SimpleTestCase):
    def test_validity_window(self):
        from apps.integrations.services import link_is_valid

        class _Link:
            expires_at = dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc)

        before = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 1, 3, tzinfo=dt.timezone.utc)
        self.assertTrue(link_is_valid(_Link(), now=before))
        self.assertFalse(link_is_valid(_Link(), now=after))
