"""Pure-logic tests for Reports & Export (no DB)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.reports.services import combine_sections, sha256_hex


class CombineSectionsTests(SimpleTestCase):
    def test_totals_sum_across_sections(self):
        out = combine_sections(
            {
                "section3_labor": Decimal("100000"),
                "section4_goods_services": Decimal("250000"),
                "section5_capex": Decimal("50000"),
                "section6_capacity_building": Decimal("20000"),
                "section7_depreciation": Decimal("30000"),
            }
        )
        self.assertEqual(out["total"], Decimal("450000"))
        self.assertEqual(out["sections"]["section4_goods_services"], Decimal("250000"))

    def test_empty_is_zero(self):
        self.assertEqual(combine_sections({})["total"], Decimal("0"))


class Sha256Tests(SimpleTestCase):
    def test_known_digest(self):
        # SHA-256 of b"" is a well-known constant — verifies deterministic hashing.
        self.assertEqual(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_hash_changes_with_content(self):
        self.assertNotEqual(sha256_hex(b"audit-pack-v1"), sha256_hex(b"audit-pack-v2"))
