"""Pure-logic tests for Copilot RBAC routing + chunking (no GCP, no DB)."""
from django.test import SimpleTestCase

from apps.accounts.models import Role
from apps.copilot.models import DocCategory
from apps.copilot.services import allowed_categories, chunk_text


class RbacRoutingTests(SimpleTestCase):
    def test_hr_cannot_see_finance(self):
        cats = allowed_categories(Role.HR_ADMIN)
        self.assertIn(DocCategory.HR, cats)
        self.assertNotIn(DocCategory.FINANCE, cats)
        self.assertNotIn(DocCategory.PROCUREMENT, cats)

    def test_finance_cannot_see_hr(self):
        cats = allowed_categories(Role.FINANCE_ADMIN)
        self.assertIn(DocCategory.FINANCE, cats)
        self.assertNotIn(DocCategory.HR, cats)

    def test_everyone_sees_global_rulebooks(self):
        for role in (Role.HR_ADMIN, Role.PROCUREMENT_ADMIN, Role.FINANCE_ADMIN):
            cats = allowed_categories(role)
            self.assertIn(DocCategory.LCGPA, cats)
            self.assertIn(DocCategory.ZATCA, cats)

    def test_super_admin_sees_all(self):
        self.assertEqual(allowed_categories(Role.SUPER_ADMIN), set(DocCategory.values))


class ChunkingTests(SimpleTestCase):
    def test_chunks_with_overlap(self):
        text = "x" * 2500
        chunks = chunk_text(text, size=1000, overlap=150)
        self.assertEqual(len(chunks), 3)  # step 850 -> 0,850,1700
        self.assertTrue(all(len(c) <= 1000 for c in chunks))

    def test_empty_text(self):
        self.assertEqual(chunk_text("   "), [])

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            chunk_text("abc", size=0)
