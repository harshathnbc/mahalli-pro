"""Pure-logic tests for CAPEX services (no DB)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.capex.models import CapexItem
from apps.capex.services import capex_eligible_amount


class CapexEligibilityTests(SimpleTestCase):
    def test_only_local_counts(self):
        items = [
            (CapexItem.Origin.LOCAL, Decimal("100000")),
            (CapexItem.Origin.FOREIGN, Decimal("250000")),
            (CapexItem.Origin.LOCAL, Decimal("50000")),
        ]
        self.assertEqual(capex_eligible_amount(items), Decimal("150000"))

    def test_empty_is_zero(self):
        self.assertEqual(capex_eligible_amount([]), Decimal("0"))

    def test_all_foreign_is_zero(self):
        items = [(CapexItem.Origin.FOREIGN, Decimal("999"))]
        self.assertEqual(capex_eligible_amount(items), Decimal("0"))
