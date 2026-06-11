"""
LCGPA certificate parsing via Google Cloud Document AI (Module 3 OCR).

The Document AI call lives in `parse_certificate_pdf`; the field extraction and the
expiry decision are pure functions so they are unit-testable without GCP. Parsed
output feeds the self-enriching Global Whitelist (services.push_certificate_to_whitelist).
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation


def _to_score(text: str) -> Decimal | None:
    """'45%' or '0.45' -> Decimal('0.45')."""
    if not text:
        return None
    cleaned = text.strip().replace("%", "")
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    return value / Decimal("100") if value > 1 else value


def _to_date(text: str) -> dt.date | None:
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    m = re.search(r"(20\d{2})", text)
    return dt.date(int(m.group(1)), 12, 31) if m else None


# Document AI entity type -> our field. Adjust to match the trained processor schema.
_FIELD_MAP = {
    "vendor_name": ("vendor", "name", "supplier"),
    "cr_vat": ("cr", "vat", "registration", "unified"),
    "lc_score": ("local_content", "lc_score", "score", "percentage"),
    "expiry_date": ("expiry", "expiration", "valid_until", "end_date"),
}


def extract_fields_from_entities(entities: list[dict]) -> dict:
    """
    Pure mapper: Document AI key-value entities -> structured certificate fields.
    Each entity is {"type": str, "mention_text": str}. First match per field wins.
    """
    out: dict = {"vendor_name": "", "cr_vat": "", "lc_score": None, "expiry_date": None}
    for ent in entities:
        etype = (ent.get("type") or "").lower()
        text = ent.get("mention_text") or ""
        for field, keys in _FIELD_MAP.items():
            if out_is_empty(out[field]) and any(k in etype for k in keys):
                if field == "lc_score":
                    out[field] = _to_score(text)
                elif field == "expiry_date":
                    out[field] = _to_date(text)
                else:
                    out[field] = text.strip()
    return out


def out_is_empty(value) -> bool:
    return value in (None, "", [])


def is_certificate_expired(expiry_date: dt.date | None, today: dt.date | None = None) -> bool:
    """A certificate with an expiry in the past is expired (reverts vendor to baseline)."""
    if expiry_date is None:
        return False
    return expiry_date < (today or dt.date.today())


def parse_certificate_pdf(pdf_bytes: bytes) -> dict:
    """
    Run Document AI on a certificate PDF and return {fields..., raw_json}.
    Requires GCP configuration; raises GCPNotConfigured otherwise.
    """
    from google.cloud import documentai

    from apps.common.gcp import documentai_client, processor_name

    client = documentai_client()
    raw_doc = documentai.RawDocument(content=pdf_bytes, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=processor_name(), raw_document=raw_doc)
    result = client.process_document(request=request)
    document = result.document

    entities = [
        {"type": e.type_, "mention_text": e.mention_text}
        for e in document.entities
    ]
    fields = extract_fields_from_entities(entities)
    fields["raw_json"] = {"text": document.text[:5000], "entities": entities}
    return fields
