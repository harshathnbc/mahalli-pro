"""Pure-logic tests for Master Admin provisioning + RBAC section access (no DB)."""
from django.test import SimpleTestCase

from apps.accounts.models import ROLE_SECTION_ACCESS, Role
from apps.accounts.provisioning import generate_temp_password


class PasswordGenTests(SimpleTestCase):
    def test_length_and_charset(self):
        pw = generate_temp_password(16)
        self.assertEqual(len(pw), 16)
        self.assertTrue(pw.isalnum())

    def test_uniqueness(self):
        self.assertNotEqual(generate_temp_password(), generate_temp_password())


class SectionAccessTests(SimpleTestCase):
    def test_hr_sections(self):
        self.assertEqual(ROLE_SECTION_ACCESS[Role.HR_ADMIN], {"3", "6"})

    def test_procurement_section(self):
        self.assertEqual(ROLE_SECTION_ACCESS[Role.PROCUREMENT_ADMIN], {"4"})

    def test_finance_sections(self):
        self.assertEqual(ROLE_SECTION_ACCESS[Role.FINANCE_ADMIN], {"A", "7"})
