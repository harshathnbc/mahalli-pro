"""
Reports & Export services (Module 8) — the Victory Screen.

Assembles the per-section LCGPA score, populates the official template via the
Master Admin's cell-map, and builds the Audit Pack (.zip) with an SHA-256 hash
logged to the Master Audit Log (Module 10, Phase 1). Exports are blocked until the
Annual Hard-Close passes the ±5% reconciliation (finance.export_allowed).
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.assets.models import Asset
from apps.audit.models import AuditAction, AuditLog
from apps.capex.models import CapexItem
from apps.finance.services import export_allowed
from apps.hr.models import PayrollRow
from apps.procurement.models import Invoice
from apps.reports.models import ExportArtifact, LcReport, SimulatorScenario
from apps.scoring.engine import bidding_power_gain
from apps.seed.models import TemplateVault


class ExportBlocked(Exception):
    """Raised when an export is attempted before reconciliation passes (Red Light)."""


# --- Pure helpers (unit-testable without a DB) -------------------------------
def combine_sections(sections: dict[str, Decimal]) -> dict:
    """
    Given per-section local-content contributions, return totals + an overall
    score fraction. Kept pure so it can be tested without touching the database.
    """
    total = sum((Decimal(str(v)) for v in sections.values()), Decimal("0"))
    return {"sections": {k: Decimal(str(v)) for k, v in sections.items()}, "total": total}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- Score assembly -----------------------------------------------------------
def _sum(rows, attr) -> Decimal:
    total = Decimal("0")
    for r in rows:
        total += getattr(r, attr) or Decimal("0")
    return total


def assemble_score(tenant, compliance_year) -> dict:
    """Pull the section contributions for a tenant/year from each module."""
    payroll = PayrollRow.objects.filter(tenant=tenant, upload__compliance_year=compliance_year)
    section3 = _sum(payroll.only("section3_amount"), "section3_amount")
    section6 = _sum(payroll.only("section6_amount"), "section6_amount")

    # Section 4: net eligible procurement spend (decrypted).
    section4 = Decimal("0")
    for inv in Invoice.objects.filter(
        tenant=tenant, upload__compliance_year=compliance_year
    ).only("gross_amount", "vat_amount", "net_eligible_spend"):
        net = inv.net_eligible_spend
        if net is None:
            net = (inv.gross_amount or Decimal("0")) - (inv.vat_amount or Decimal("0"))
        section4 += net

    section5 = _sum(
        CapexItem.objects.filter(tenant=tenant, compliance_year=compliance_year).only("amount"),
        "amount",
    )
    section7 = _sum(
        Asset.objects.filter(
            tenant=tenant,
            register__compliance_year=compliance_year,
            included_in_score=True,
        ).only("annual_depreciation"),
        "annual_depreciation",
    )

    return combine_sections(
        {
            "section3_labor": section3,
            "section4_goods_services": section4,
            "section5_capex": section5,
            "section6_capacity_building": section6,
            "section7_depreciation": section7,
        }
    )


# --- Template population -------------------------------------------------------
def generate_score_xlsx(report: LcReport) -> ExportArtifact:
    """
    Populate the official template by writing system variables into the exact cells
    declared by the Master Admin's TemplateCellMapping, then store the workbook.
    """
    if not export_allowed(report.compliance_year):
        raise ExportBlocked("Annual Hard-Close has not passed ±5% reconciliation.")

    import openpyxl

    template = TemplateVault.objects.filter(
        template_key=TemplateVault.TemplateKey.LC_SCORE_V2,
        compliance_year=report.compliance_year.year,
    ).first()
    score = report.computed_score or assemble_score(report.tenant, report.compliance_year)

    if template and default_storage.exists(template.file_ref):
        with default_storage.open(template.file_ref, "rb") as fh:
            wb = openpyxl.load_workbook(fh)
        for mapping in template.cell_mappings.all():
            value = score.get("sections", {}).get(mapping.system_variable)
            if value is not None and mapping.sheet_name in wb.sheetnames:
                wb[mapping.sheet_name][mapping.cell_coordinate] = float(value)
    else:
        # No template uploaded yet — emit a minimal summary workbook.
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Score"
        ws.append(["Section", "Local Content (SAR)"])
        for key, val in score.get("sections", {}).items():
            ws.append([key, float(val)])
        ws.append(["TOTAL", float(score.get("total", 0))])

    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    key = f"exports/{report.tenant_id}/{report.id}/score.xlsx"
    default_storage.save(key, ContentFile(data))

    return ExportArtifact.objects.create(
        tenant=report.tenant,
        report=report,
        kind=ExportArtifact.Kind.SCORE_XLSX,
        file_ref=key,
        sha256_hash=sha256_hex(data),
    )


# --- Audit Pack (.zip) + cryptographic hash -----------------------------------
def build_audit_pack(report: LcReport, extra_files: dict[str, bytes] | None = None) -> ExportArtifact:
    """
    Bundle the sanitized ledger / mapped TB / payroll summary / PDFs into a .zip,
    hash it with SHA-256, store it, and log the hash to the immutable audit trail so
    external Big-4 auditors can verify the data was not tampered with.
    """
    if not export_allowed(report.compliance_year):
        raise ExportBlocked("Annual Hard-Close has not passed ±5% reconciliation.")

    score = report.computed_score or assemble_score(report.tenant, report.compliance_year)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        lines = [f"{k},{v}" for k, v in score.get("sections", {}).items()]
        lines.append(f"TOTAL,{score.get('total', 0)}")
        zf.writestr("score_summary.csv", "\n".join(lines))
        for name, blob in (extra_files or {}).items():
            zf.writestr(name, blob)
    data = buf.getvalue()
    digest = sha256_hex(data)

    key = f"exports/{report.tenant_id}/{report.id}/audit_pack.zip"
    default_storage.save(key, ContentFile(data))

    artifact = ExportArtifact.objects.create(
        tenant=report.tenant,
        report=report,
        kind=ExportArtifact.Kind.AUDIT_PACK_ZIP,
        file_ref=key,
        sha256_hash=digest,
    )
    AuditLog.objects.create(
        tenant=report.tenant,
        action=AuditAction.CREATE,
        entity_type="ExportArtifact.AUDIT_PACK",
        entity_id=str(artifact.id),
        after={"sha256": digest, "file_ref": key},
    )
    return artifact


# --- Strategic advisory: 10% price-preference Bidding Power --------------------
def run_bidding_simulator(tenant, *, shifted_spend: Decimal, scope: str) -> SimulatorScenario:
    gain = bidding_power_gain(shifted_spend)
    return SimulatorScenario.objects.create(
        tenant=tenant,
        scope=scope,
        inputs={"shifted_spend": str(shifted_spend)},
        result={
            "price_advantage_sar": str(gain),
            "narrative": (
                f"Shifting {shifted_spend} SAR to local vendors yields a 10% price "
                f"preference (~{gain} SAR) on the next government tender."
            ),
        },
    )
