"""Pure-logic tests for the LCGPA scoring engine (no DB)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.scoring.engine import (
    VendorSpend,
    bidding_power_gain,
    labor_local_content,
    top_vendors_70,
    within_tolerance,
)


class ScoringEngineTests(SimpleTestCase):
    def test_labor_multipliers(self):
        # 100k Saudi ×1.0 + 100k foreign ×0.534 = 153,400
        self.assertEqual(
            labor_local_content(Decimal("100000"), Decimal("100000")),
            Decimal("153400.000"),
        )

    def test_within_tolerance_pass_and_fail(self):
        ok, var = within_tolerance(Decimal("100"), Decimal("104"))
        self.assertTrue(ok)
        self.assertLess(var, Decimal("0.05"))
        fail, _ = within_tolerance(Decimal("100"), Decimal("120"))
        self.assertFalse(fail)

    def test_tolerance_zero_base(self):
        ok, var = within_tolerance(Decimal("0"), Decimal("0"))
        self.assertTrue(ok)
        self.assertEqual(var, Decimal("0"))

    def test_top_vendors_70_smallest_covering_set(self):
        vendors = [
            VendorSpend("a", Decimal("500"), Decimal("0.8")),
            VendorSpend("b", Decimal("300"), Decimal("0.5")),
            VendorSpend("c", Decimal("200"), Decimal("0.3")),
        ]
        result = top_vendors_70(vendors)
        # a+b = 800/1000 = 80% >= 70% coverage; c is excluded.
        self.assertEqual(result["selected"], ["a", "b"])
        self.assertGreaterEqual(result["coverage"], Decimal("0.70"))

    def test_bidding_power(self):
        self.assertEqual(bidding_power_gain(Decimal("5000000")), Decimal("500000.0"))
