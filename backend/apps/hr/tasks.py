"""
Celery task: parse the monthly payroll Excel, create PayrollRow records (encrypting
PII + money), and apply the Section 3/6 classification engine to each row.

GOSI PDF headcount extraction is handled separately when certificates are uploaded
(stubbed here to a no-op hook; production uses Document AI / pypdf in me-central2).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.core.files.storage import default_storage

from apps.hr import services
from apps.hr.models import HrMonthlyUpload, PayrollRow


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip() or "0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


# Expected columns in the standardized Mahalli Pro payroll template.
COLS = {
    "national_id": "ID",
    "name": "Name",
    "gender": "Gender",
    "nationality": "Nationality",
    "status": "Status",
    "classification": "Classification",
    "basic": "Basic",
    "housing": "Housing",
    "transport": "Transport",
    "bonus": "Bonus",
    "eosb": "EOSB",
}


@shared_task
def parse_payroll_upload(upload_id: str) -> dict:
    import pandas as pd

    upload = HrMonthlyUpload.objects.get(id=upload_id)
    with default_storage.open(upload.payroll_file_ref, "rb") as fh:
        df = pd.read_excel(fh)

    created = 0
    for _, r in df.iterrows():
        status = str(r.get(COLS["status"], "ACTIVE") or "ACTIVE").upper()
        classification = str(r.get(COLS["classification"], "REGULAR") or "REGULAR").upper()
        nationality = str(r.get(COLS["nationality"], "") or "")
        row = PayrollRow.objects.create(
            tenant_id=upload.tenant_id,
            upload=upload,
            national_id=str(r.get(COLS["national_id"], "") or ""),
            name=str(r.get(COLS["name"], "") or ""),
            gender=str(r.get(COLS["gender"], "") or ""),
            nationality=nationality,
            is_saudi=nationality.strip().lower() in {"saudi", "ksa", "sa"},
            status=status if status in dict(PayrollRow.Status.choices) else "ACTIVE",
            classification=(
                classification
                if classification in dict(PayrollRow.Classification.choices)
                else "REGULAR"
            ),
            basic=_dec(r.get(COLS["basic"])),
            housing=_dec(r.get(COLS["housing"])),
            transport=_dec(r.get(COLS["transport"])),
            bonus_vacation_pay=_dec(r.get(COLS["bonus"])),
            eosb_accrual=_dec(r.get(COLS["eosb"])),
        )
        services.apply_classification(row)  # Section 3/6 split
        created += 1

    check = services.gosi_cross_check(upload)
    upload.status = "PARSED" if check.matches else "GOSI_MISMATCH"
    upload.save(update_fields=["status"])
    return {"status": upload.status, "rows": created, "cross_check": check.matches}
