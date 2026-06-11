"""Pure-logic tests for Procurement services (no DB).

DB-backed paths (whitelist upsert, mandatory checks, Top-40 aggregation) require a
PostgreSQL test database and are covered by integration tests run via `manage.py test`.
"""
import datetime as dt
from decimal import Decimal

from django.test import SimpleTestCase

from apps.common.validators import is_local_vat, zatca_vat_validator
from apps.procurement.models import Vendor
from apps.procurement.services import _validity_key, classify_vendor


class ZatcaClassificationTests(SimpleTestCase):
    def test_local_vat_starts_and_is_15_digits(self):
        self.assertTrue(is_local_vat("300000000000003"))
        self.assertEqual(classify_vendor("300000000000003"), Vendor.Classification.LOCAL)

    def test_foreign_when_not_starting_with_3(self):
        self.assertFalse(is_local_vat("400000000000003"))
        self.assertEqual(classify_vendor("400000000000003"), Vendor.Classification.FOREIGN)

    def test_foreign_when_wrong_length_or_empty(self):
        self.assertEqual(classify_vendor("3003"), Vendor.Classification.FOREIGN)
        self.assertEqual(classify_vendor(None), Vendor.Classification.FOREIGN)

    def test_validator_requires_3_at_both_ends(self):
        with self.assertRaises(Exception):
            zatca_vat_validator("300000000000001")  # ends in 1


class WhitelistConflictResolutionTests(SimpleTestCase):
    def test_newer_expiry_wins(self):
        older = _validity_key(dt.date(2025, 1, 1), 2025)
        newer = _validity_key(dt.date(2026, 1, 1), 2026)
        self.assertGreater(newer, older)

    def test_financial_year_breaks_tie_when_no_expiry(self):
        a = _validity_key(None, 2025)
        b = _validity_key(None, 2026)
        self.assertGreater(b, a)

    def test_regression_detected(self):
        incoming = _validity_key(dt.date(2024, 1, 1), 2024)
        current = _validity_key(dt.date(2026, 1, 1), 2026)
        self.assertLess(incoming, current)  # -> would raise WhitelistRegression
