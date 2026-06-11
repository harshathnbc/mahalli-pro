"""Pure-logic tests for Finance services (no DB).

DB-backed paths (aggregation, reconciliation persistence, locking) require a
PostgreSQL test database and are covered by integration tests via `manage.py test`.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.finance.models import TbAccountMapping
from apps.finance.services import EXEMPTION_CATEGORIES, ceiling_from_mappings


class CeilingTests(SimpleTestCase):
    def test_exemptions_are_subtracted(self):
        Cat = TbAccountMapping.Category
        items = [
            (Cat.REVENUE, Decimal("1000000")),
            (Cat.DIRECT_COST, Decimal("400000")),
            (Cat.EXEMPT_ZAKAT, Decimal("50000")),
            (Cat.EXEMPT_CUSTOMS, Decimal("30000")),
            (Cat.EXEMPT_VISA, Decimal("20000")),
        ]
        # base = 1,400,000 ; exemptions = 100,000 ; ceiling = 1,300,000
        self.assertEqual(ceiling_from_mappings(items), Decimal("1300000"))

    def test_no_exemptions(self):
        items = [(TbAccountMapping.Category.REVENUE, Decimal("500000"))]
        self.assertEqual(ceiling_from_mappings(items), Decimal("500000"))

    def test_exemption_category_set(self):
        Cat = TbAccountMapping.Category
        self.assertEqual(
            EXEMPTION_CATEGORIES,
            {Cat.EXEMPT_ZAKAT, Cat.EXEMPT_CUSTOMS, Cat.EXEMPT_VISA},
        )
