"""
Assets & Depreciation domain services (Section 7).

In-Kingdom validation: an asset NOT operating in KSA is excluded from the score.
±5% cross-check: the Excel asset-register depreciation must match the Depreciation
Expense mapped from the Trial Balance (Module 4) within ±5%.
"""
from __future__ import annotations

from decimal import Decimal

from apps.assets.models import Asset, AssetRegisterUpload
from apps.scoring.engine import within_tolerance


def asset_included(operating_in_ksa: bool) -> bool:
    """Pure In-Kingdom rule: only assets operating in KSA count toward the score."""
    return bool(operating_in_ksa)


def register_depreciation_total(register: AssetRegisterUpload) -> Decimal:
    """Sum the score-eligible depreciation in an asset register (decrypting 🔒)."""
    total = Decimal("0")
    for asset in register.assets.filter(included_in_score=True).only("annual_depreciation"):
        total += asset.annual_depreciation or Decimal("0")
    return total


def apply_in_kingdom_rule(asset: Asset) -> Asset:
    """Set included_in_score from the mandatory 'Operating in KSA?' column."""
    asset.included_in_score = asset_included(asset.operating_in_ksa)
    asset.save(update_fields=["included_in_score"])
    return asset


def reconcile_with_tb(register: AssetRegisterUpload, tb_depreciation: Decimal) -> dict:
    """±5% check of register depreciation vs the Trial Balance depreciation expense."""
    register_total = register_depreciation_total(register)
    passed, variance = within_tolerance(register_total, tb_depreciation)
    return {
        "register_depreciation": register_total,
        "tb_depreciation": tb_depreciation,
        "variance_pct": variance,
        "passed": passed,
    }
