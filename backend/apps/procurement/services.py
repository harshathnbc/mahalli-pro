"""
Procurement domain services (Section 4).

Pure-ish domain logic kept out of views/tasks so it is unit-testable and reused by
both the Celery parser and the API:

  • classify_vendor          — ZATCA Intelligence Engine (Local vs Foreign)
  • resolve_vendor_lc_score  — cert > Global Whitelist > baseline sector score
  • push_certificate_to_whitelist — self-enriching moat w/ regression protection
  • run_mandatory_checks     — Mandatory-List + per-year threshold alerts (Etimad)
  • run_top40                — Top-40 / 70% optimizer (delegates math to scoring.engine)
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.common.validators import is_local_vat
from apps.scoring.engine import VendorSpend, top_vendors_70
from apps.seed.models import GlobalWhitelistEntry, IsicSector, MandatoryMinThreshold
from apps.procurement.models import (
    ComplianceWarning,
    Invoice,
    TopVendorSelection,
    Vendor,
)


# --- ZATCA Intelligence Engine ------------------------------------------------
def classify_vendor(vat_number: str | None) -> str:
    """15-digit VAT starting with 3 == Local; otherwise Foreign."""
    return Vendor.Classification.LOCAL if is_local_vat(vat_number) else Vendor.Classification.FOREIGN


# --- LC score resolution ------------------------------------------------------
def resolve_vendor_lc_score(vendor: Vendor) -> tuple[Decimal | None, str]:
    """
    Priority: a valid (non-expired) parsed certificate > Global Whitelist auto-fill >
    baseline sector score. Returns (score, source). Expired certs fall through.
    """
    today = timezone.now().date()
    cert = (
        vendor.certificates.filter(is_expired=False)
        .exclude(parsed_lc_score__isnull=True)
        .order_by("-expiry_date")
        .first()
    )
    if cert and (cert.expiry_date is None or cert.expiry_date >= today):
        return cert.parsed_lc_score, Vendor.ScoreSource.CERT

    if vendor.vat_number:
        entry = GlobalWhitelistEntry.objects.filter(vat_number=vendor.vat_number).first()
        if entry:
            return entry.lc_score, Vendor.ScoreSource.GLOBAL_WHITELIST

    # Baseline: fall back to the company/sector baseline if one is associated.
    baseline = IsicSector.objects.order_by("baseline_lc_score").first()
    if baseline:
        return baseline.baseline_lc_score, Vendor.ScoreSource.BASELINE
    return None, Vendor.ScoreSource.BASELINE


# --- Self-enriching Global Whitelist (with conflict resolution) ---------------
class WhitelistRegression(Exception):
    """Raised when an upload is older than the currently verified entry."""

    def __init__(self, existing: GlobalWhitelistEntry):
        self.existing = existing
        super().__init__("A newer verified certificate already exists for this vendor.")


def _validity_key(expiry: dt.date | None, fin_year: int | None) -> tuple:
    """Higher == more up to date. Expiry date dominates, then financial year."""
    return (expiry or dt.date.min, fin_year or 0)


@transaction.atomic
def push_certificate_to_whitelist(
    *,
    vat_number: str,
    cr_number: str,
    vendor_name: str,
    lc_score: Decimal,
    expiry_date: dt.date | None,
    financial_year: int | None,
    source_sha256: str = "",
    source_tenant_id=None,
) -> GlobalWhitelistEntry:
    """
    Push a freshly verified certificate to the cross-tenant Global Whitelist.

    Conflict resolution: if an entry exists and is NEWER (later expiry / financial
    year) than this upload, reject to prevent data regression (WhitelistRegression).
    Otherwise upsert, bumping the version and applying the most up-to-date score.
    """
    incoming = _validity_key(expiry_date, financial_year)
    existing = (
        GlobalWhitelistEntry.objects.select_for_update()
        .filter(vat_number=vat_number)
        .first()
    )
    if existing:
        current = _validity_key(existing.certificate_expiry_date, existing.financial_year)
        if incoming < current:
            raise WhitelistRegression(existing)
        existing.cr_number = cr_number or existing.cr_number
        existing.vendor_name_norm = (vendor_name or existing.vendor_name_norm).upper()
        existing.lc_score = lc_score
        existing.certificate_expiry_date = expiry_date
        existing.financial_year = financial_year
        existing.source_cert_sha256 = source_sha256
        existing.version += 1
        if source_tenant_id:
            existing._source_tenant_id = source_tenant_id
        existing.save()
        return existing

    return GlobalWhitelistEntry.objects.create(
        vat_number=vat_number,
        cr_number=cr_number,
        vendor_name_norm=(vendor_name or "").upper(),
        lc_score=lc_score,
        certificate_expiry_date=expiry_date,
        financial_year=financial_year,
        source_cert_sha256=source_sha256,
        version=1,
        _source_tenant_id=source_tenant_id,
    )


# --- Mandatory-List & threshold alert engine ----------------------------------
def run_mandatory_checks(tenant, compliance_year) -> list[ComplianceWarning]:
    """
    Cross-reference invoice lines against the Mandatory List (by Etimad code).
    Raise a Compliance Warning when a mandatory item is bought from a Foreign vendor,
    or when the vendor's LC score is below that product's minimum for the year.
    """
    warnings: list[ComplianceWarning] = []
    thresholds = {
        t.etimad_code: t.min_pct
        for t in MandatoryMinThreshold.objects.filter(year=compliance_year.year)
    }
    lines = (
        Invoice.objects.filter(tenant=tenant, upload__compliance_year=compliance_year)
        .values_list(
            "lines__etimad_commodity__etimad_code",
            "lines__etimad_commodity__is_mandatory",
            "vendor_id",
            "vendor__classification",
            "vendor__verified_lc_score",
        )
        .distinct()
    )
    for etimad_code, is_mandatory, vendor_id, classification, lc_score in lines:
        if not etimad_code or not is_mandatory:
            continue
        if classification == Vendor.Classification.FOREIGN:
            warnings.append(
                ComplianceWarning(
                    tenant=tenant,
                    compliance_year=compliance_year,
                    type=ComplianceWarning.WarningType.MANDATORY_FOREIGN,
                    etimad_code=etimad_code,
                    vendor_id=vendor_id,
                    message=f"Mandatory-list item {etimad_code} purchased from a Foreign vendor.",
                )
            )
            continue
        min_pct = thresholds.get(etimad_code)
        if min_pct is not None and (lc_score is None or lc_score < min_pct):
            warnings.append(
                ComplianceWarning(
                    tenant=tenant,
                    compliance_year=compliance_year,
                    type=ComplianceWarning.WarningType.THRESHOLD,
                    etimad_code=etimad_code,
                    vendor_id=vendor_id,
                    message=(
                        f"LC score {lc_score} below {compliance_year.year} minimum "
                        f"{min_pct} for mandatory item {etimad_code}."
                    ),
                )
            )
    if warnings:
        ComplianceWarning.objects.bulk_create(warnings)
    return warnings


# --- Top-40 / 70% optimizer ---------------------------------------------------
def run_top40(tenant, compliance_year) -> TopVendorSelection:
    """
    Aggregate net eligible spend per vendor for the year (decrypting 🔒 amounts in
    Python), then delegate the 70%-coverage selection + weighted score to the engine.
    """
    spend: dict[str, Decimal] = {}
    scores: dict[str, Decimal] = {}
    invoices = (
        Invoice.objects.filter(tenant=tenant, upload__compliance_year=compliance_year)
        .select_related("vendor")
    )
    for inv in invoices:
        # net_eligible_spend is precomputed at parse time; fall back to gross - vat.
        net = inv.net_eligible_spend
        if net is None:
            net = (inv.gross_amount or Decimal("0")) - (inv.vat_amount or Decimal("0"))
        vid = str(inv.vendor_id)
        spend[vid] = spend.get(vid, Decimal("0")) + net
        scores[vid] = inv.vendor.verified_lc_score or Decimal("0")

    vendors = [VendorSpend(vid, spend[vid], scores[vid]) for vid in spend]
    result = top_vendors_70(vendors)
    return TopVendorSelection.objects.create(
        tenant=tenant,
        compliance_year=compliance_year,
        selected_vendor_ids=result["selected"],
        computed_lc_score=result["weighted_lc_score"],
    )
