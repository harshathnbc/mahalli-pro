"""Pure-logic tests for Document AI certificate post-processing (no GCP, no DB)."""
import datetime as dt
from decimal import Decimal

from django.test import SimpleTestCase

from apps.procurement.docai import (
    _to_date,
    _to_score,
    extract_fields_from_entities,
    is_certificate_expired,
)


class ScoreParsingTests(SimpleTestCase):
    def test_percent_string(self):
        self.assertEqual(_to_score("45%"), Decimal("0.45"))

    def test_fraction_string(self):
        self.assertEqual(_to_score("0.45"), Decimal("0.45"))

    def test_garbage_is_none(self):
        self.assertIsNone(_to_score("n/a"))


class DateParsingTests(SimpleTestCase):
    def test_iso(self):
        self.assertEqual(_to_date("2026-12-31"), dt.date(2026, 12, 31))

    def test_dmy(self):
        self.assertEqual(_to_date("31/12/2026"), dt.date(2026, 12, 31))

    def test_year_only_fallback(self):
        self.assertEqual(_to_date("FY 2027"), dt.date(2027, 12, 31))


class EntityMappingTests(SimpleTestCase):
    def test_maps_known_entity_types(self):
        entities = [
            {"type": "supplier_name", "mention_text": "ACME Industrial Co"},
            {"type": "vat_number", "mention_text": "300000000000003"},
            {"type": "local_content_score", "mention_text": "62%"},
            {"type": "expiry_date", "mention_text": "2026-12-31"},
        ]
        out = extract_fields_from_entities(entities)
        self.assertEqual(out["vendor_name"], "ACME Industrial Co")
        self.assertEqual(out["cr_vat"], "300000000000003")
        self.assertEqual(out["lc_score"], Decimal("0.62"))
        self.assertEqual(out["expiry_date"], dt.date(2026, 12, 31))

    def test_first_match_wins(self):
        entities = [
            {"type": "score", "mention_text": "50%"},
            {"type": "lc_score", "mention_text": "90%"},
        ]
        self.assertEqual(extract_fields_from_entities(entities)["lc_score"], Decimal("0.50"))


class ExpiryTests(SimpleTestCase):
    def test_past_is_expired(self):
        self.assertTrue(is_certificate_expired(dt.date(2020, 1, 1), dt.date(2026, 6, 12)))

    def test_future_not_expired(self):
        self.assertFalse(is_certificate_expired(dt.date(2027, 1, 1), dt.date(2026, 6, 12)))

    def test_none_not_expired(self):
        self.assertFalse(is_certificate_expired(None))
