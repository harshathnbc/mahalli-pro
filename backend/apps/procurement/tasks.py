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

from apps.procurement import services
from apps.procurement.models import (
    ColumnMapping,
    Invoice,
    ProcMonthlyUpload,
    Vendor,
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
