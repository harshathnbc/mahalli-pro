"""Pure-logic tests for Assets services (no DB)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.assets.services import asset_included
from apps.scoring.engine import within_tolerance


class InKingdomTests(SimpleTestCase):
    def test_ksa_asset_included(self):
        self.assertTrue(asset_included(True))

    def test_non_ksa_excluded(self):
        self.assertFalse(asset_included(False))


class DepreciationReconcileTests(SimpleTestCase):
    def test_within_5pct_passes(self):
        passed, _ = within_tolerance(Decimal("100000"), Decimal("103000"))
        self.assertTrue(passed)

    def test_over_5pct_fails(self):
        passed, _ = within_tolerance(Decimal("100000"), Decimal("120000"))
        self.assertFalse(passed)
