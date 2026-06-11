"""
CAPEX domain services (Section 5).

Capital expenditure contributes to Local Content based on whether the asset/spend
is Local vs Foreign (mirroring the official "Section 5. CAPEX" template columns).
"""
from __future__ import annotations

from decimal import Decimal

from apps.capex.models import CapexItem


def capex_eligible_amount(items: list[tuple[str, Decimal]]) -> Decimal:
    """
    Pure helper: sum the LOCAL-origin CAPEX amounts (the locally eligible portion).
    `items` is a list of (local_or_foreign, amount) pairs. Side-effect-free for tests.
    """
    total = Decimal("0")
    for origin, amount in items:
        if origin == CapexItem.Origin.LOCAL:
            total += amount or Decimal("0")
    return total


def aggregate_capex(tenant, compliance_year) -> dict:
    """Total vs locally-eligible CAPEX for a tenant/year (decrypting 🔒 amounts)."""
    total = Decimal("0")
    pairs: list[tuple[str, Decimal]] = []
    for item in CapexItem.objects.filter(
        tenant=tenant, compliance_year=compliance_year
    ).only("local_or_foreign", "amount"):
        amount = item.amount or Decimal("0")
        total += amount
        pairs.append((item.local_or_foreign, amount))
    return {"total": total, "local_eligible": capex_eligible_amount(pairs)}
