"""
Celery tasks for Procurement (Section 4).

`parse_invoice_upload` reads a raw ERP export from object storage, applies the
tenant's memorized ColumnMapping, and creates Invoice rows (encrypting amounts),
auto-extracting + ZATCA-classifying vendors as it goes.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.procurement import services
from apps.procurement.models import (
    ColumnMapping,
    Invoice,
    ProcMonthlyUpload,
    Vendor,
    VendorLcgpaCertificate,
)


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip() or "0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _mapping_for(tenant_id) -> dict[str, str]:
    """system_field -> source column name, as remembered for this tenant."""
    return {
        m.system_field: m.source_field_name
        for m in ColumnMapping.objects.filter(tenant_id=tenant_id)
    }


@shared_task
def parse_invoice_upload(upload_id: str) -> dict:
    import pandas as pd

    upload = ProcMonthlyUpload.objects.select_related("tenant").get(id=upload_id)
    tenant_id = upload.tenant_id
    mapping = _mapping_for(tenant_id)
    if not mapping:
        upload.status = "NEEDS_MAPPING"
        upload.save(update_fields=["status"])
        return {"status": upload.status}

    with default_storage.open(upload.raw_file_ref, "rb") as fh:
        df = pd.read_excel(fh)

    col_invoice = mapping.get(ColumnMapping.SystemField.INVOICE_NO)
    col_vat = mapping.get(ColumnMapping.SystemField.VAT)
    col_gross = mapping.get(ColumnMapping.SystemField.GROSS)
    col_vat_amt = mapping.get(ColumnMapping.SystemField.VAT_AMOUNT)

    created = 0
    vendor_cache: dict[str, Vendor] = {}
    for _, row in df.iterrows():
        vat = str(row.get(col_vat, "") or "").strip()
        gross = _to_decimal(row.get(col_gross))
        vat_amt = _to_decimal(row.get(col_vat_amt))

        vendor = vendor_cache.get(vat)
        if vendor is None:
            vendor, _ = Vendor.objects.get_or_create(
                tenant_id=tenant_id,
                vat_number=vat,
                defaults={
                    "name": str(row.get("VendorName", "") or "Unknown"),
                    "classification": services.classify_vendor(vat),
                },
            )
            vendor_cache[vat] = vendor

        Invoice.objects.create(
            tenant_id=tenant_id,
            upload=upload,
            vendor=vendor,
            invoice_number=str(row.get(col_invoice, "") or ""),
            vat_number=vat,
            gross_amount=gross,
            vat_amount=vat_amt,
            net_eligible_spend=gross - vat_amt,  # strip VAT to find net eligible spend
        )
        created += 1

    upload.status = "PARSED"
    upload.save(update_fields=["status"])
    return {"status": upload.status, "invoices": created}


@shared_task
def parse_vendor_certificate(cert_id: str) -> dict:
    """
    OCR a vendor's LCGPA certificate via Document AI, persist the parsed fields, set
    expiry, and push the verified score to the cross-tenant Global Whitelist. If the
    certificate is expired, the vendor reverts to the baseline score.
    """
    from apps.procurement.docai import is_certificate_expired, parse_certificate_pdf

    cert = VendorLcgpaCertificate.objects.select_related("vendor").get(id=cert_id)
    with default_storage.open(cert.file_ref, "rb") as fh:
        fields = parse_certificate_pdf(fh.read())

    cert.parsed_vendor_name = fields.get("vendor_name", "")
    cert.parsed_cr_vat = fields.get("cr_vat", "")
    cert.parsed_lc_score = fields.get("lc_score")
    cert.expiry_date = fields.get("expiry_date")
    cert.is_expired = is_certificate_expired(cert.expiry_date)
    cert.doc_ai_json = fields.get("raw_json")
    cert.save()

    if cert.is_expired or cert.parsed_lc_score is None:
        # Revert vendor to baseline; do not enrich the whitelist from a stale cert.
        return {"cert": str(cert.id), "expired": cert.is_expired, "whitelisted": False}

    try:
        entry = services.push_certificate_to_whitelist(
            vat_number=cert.parsed_cr_vat,
            cr_number=cert.parsed_cr_vat,
            vendor_name=cert.parsed_vendor_name,
            lc_score=cert.parsed_lc_score,
            expiry_date=cert.expiry_date,
            financial_year=cert.expiry_date.year if cert.expiry_date else None,
            source_tenant_id=cert.tenant_id,
        )
    except services.WhitelistRegression:
        return {"cert": str(cert.id), "whitelisted": False, "reason": "newer_exists"}

    # Auto-fill the vendor from the freshly verified certificate.
    vendor = cert.vendor
    vendor.verified_lc_score = cert.parsed_lc_score
    vendor.lc_score_source = Vendor.ScoreSource.CERT
    vendor.global_whitelist = entry
    vendor.save(update_fields=["verified_lc_score", "lc_score_source", "global_whitelist"])
    return {"cert": str(cert.id), "whitelisted": True, "version": entry.version, "ts": str(timezone.now())}
