"""
LCGPA scoring math engine.

Single source of truth for the formulas the architecture doc and the official
"Updating the Methodology ..." PDF describe. Operates on already-decrypted Decimal
values (the 🔒 fields cannot be aggregated in SQL), so callers fetch rows and pass
plain Decimals here. Multipliers/tolerances come from settings.LCGPA, never hard-coded.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

_L = settings.LCGPA


def labor_local_content(saudi_comp: Decimal, foreign_comp: Decimal) -> Decimal:
    """Section 3: Saudi compensation ×1.0 + foreign ×0.534 (defaults; see settings)."""
    saudi_mult = Decimal(str(_L["SAUDI_LABOR_MULTIPLIER"]))
    foreign_mult = Decimal(str(_L["FOREIGN_LABOR_MULTIPLIER"]))
    return (saudi_comp * saudi_mult) + (foreign_comp * foreign_mult)


def within_tolerance(a: Decimal, b: Decimal, tolerance: float | None = None) -> tuple[bool, Decimal]:
    """±5% Strict Block. Returns (passed, variance_fraction). variance vs the larger base."""
    tol = Decimal(str(tolerance if tolerance is not None else _L["RECONCILIATION_TOLERANCE"]))
    base = max(abs(a), abs(b))
    if base == 0:
        return True, Decimal("0")
    variance = abs(a - b) / base
    return variance <= tol, variance


@dataclass
class VendorSpend:
    vendor_id: str
    net_eligible_spend: Decimal
    lc_score: Decimal


def top_vendors_70(vendors: list[VendorSpend]) -> dict:
    """
    Top-40 / 70% optimizer: sort by net eligible spend desc, take the smallest set
    of vendors that covers >= 70% of total spend (the LCGPA reporting rule), and
    report the spend-weighted LC score of that set.
    """
    coverage = Decimal(str(_L["TOP_VENDOR_COVERAGE"]))
    ranked = sorted(vendors, key=lambda v: v.net_eligible_spend, reverse=True)
    total = sum((v.net_eligible_spend for v in ranked), Decimal("0"))
    if total == 0:
        return {"selected": [], "coverage": Decimal("0"), "weighted_lc_score": Decimal("0")}

    selected: list[VendorSpend] = []
    running = Decimal("0")
    for v in ranked:
        selected.append(v)
        running += v.net_eligible_spend
        if running / total >= coverage:
            break

    weighted = sum((v.net_eligible_spend * v.lc_score for v in selected), Decimal("0")) / running
    return {
        "selected": [v.vendor_id for v in selected],
        "coverage": running / total,
        "weighted_lc_score": weighted,
    }


def bidding_power_gain(shifted_spend: Decimal) -> Decimal:
    """Module 8: the 10% government price-preference advantage on shifted local spend."""
    return shifted_spend * Decimal(str(_L["PRICE_PREFERENCE"]))
