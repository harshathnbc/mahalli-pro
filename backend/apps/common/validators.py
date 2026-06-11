"""
LCGPA / ZATCA / Wasel field validators (Module 1 — Company Profile rules).
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# CR Number: strict 10-digit integer.
cr_number_validator = RegexValidator(
    regex=r"^\d{10}$",
    message="CR Number must be exactly 10 digits.",
)

# National Address (Wasel): 4 English letters followed by 4 digits, e.g. RAGI2929.
wasel_validator = RegexValidator(
    regex=r"^[A-Z]{4}\d{4}$",
    message="National Address (Wasel) must be 4 uppercase letters + 4 digits (e.g. RAGI2929).",
)

_VAT_RE = re.compile(r"^\d{15}$")


def zatca_vat_validator(value: str) -> None:
    """ZATCA VAT: 15 digits, must begin AND end with the digit 3."""
    if not value or not _VAT_RE.match(value):
        raise ValidationError("ZATCA VAT Number must be exactly 15 digits.")
    if not (value.startswith("3") and value.endswith("3")):
        raise ValidationError("ZATCA VAT Number must begin and end with the digit 3.")


def is_local_vat(value: str | None) -> bool:
    """ZATCA Intelligence Engine: a 15-digit VAT starting with 3 == Local Vendor."""
    return bool(value) and bool(_VAT_RE.match(value)) and value.startswith("3")
