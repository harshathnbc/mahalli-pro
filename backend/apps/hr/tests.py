"""Pure-logic tests for the HR classification engine (no DB)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.hr.models import PayrollRow
from apps.hr.services import classify_payroll


class ClassificationEngineTests(SimpleTestCase):
    def test_regular_goes_to_section3(self):
        split = classify_payroll(
            status=PayrollRow.Status.ACTIVE,
            classification=PayrollRow.Classification.REGULAR,
            gross=Decimal("10000"),
        )
        self.assertEqual(split.section3, Decimal("10000"))
        self.assertEqual(split.section6, Decimal("0"))

    def test_trainee_shifts_to_section6(self):
        split = classify_payroll(
            status=PayrollRow.Status.ACTIVE,
            classification=PayrollRow.Classification.TRAINEE,
            gross=Decimal("8000"),
        )
        self.assertEqual(split.section3, Decimal("0"))
        self.assertEqual(split.section6, Decimal("8000"))

    def test_vacation_is_zero_both_sections(self):
        split = classify_payroll(
            status=PayrollRow.Status.VACATION,
            classification=PayrollRow.Classification.REGULAR,
            gross=Decimal("9999"),
        )
        self.assertEqual(split.section3, Decimal("0"))
        self.assertEqual(split.section6, Decimal("0"))

    def test_vacation_trainee_still_zero(self):
        split = classify_payroll(
            status=PayrollRow.Status.VACATION,
            classification=PayrollRow.Classification.TRAINEE,
            gross=Decimal("5000"),
        )
        self.assertEqual(split.section3, Decimal("0"))
        self.assertEqual(split.section6, Decimal("0"))
