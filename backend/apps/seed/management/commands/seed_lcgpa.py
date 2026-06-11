"""
Seed the database from the official LCGPA source workbooks.

  python manage.py seed_lcgpa --source-dir "../docs/lcgpa"

Parses (best-effort, resilient to merged cells & bilingual headers):
  • Appendix B (in the LC Score Template)      -> IsicSector
  • Mandatory List of Government Entities      -> EtimadCommodity
  • The minimum percentage ... February 2026   -> MandatoryMinThreshold
  • A small built-in seed of verified entities -> GlobalWhitelistEntry (SABIC/Aramco/STC)

Idempotent: re-running updates existing rows.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.seed.models import (
    EtimadCommodity,
    GlobalWhitelistEntry,
    IsicSector,
    MandatoryMinThreshold,
)

# Default file names (the real deliverables shipped by LCGPA).
F_SCORE_TEMPLATE = "Local Content Score Template - v.2.xlsx"
F_MANDATORY = "Mandatory List of Government Entities (January 2026).xlsx"
F_MIN_PCT = (
    "The minimum percentage of local content in the local content certificate "
    "on mandatory list products - February 2026.xlsx"
)

_AR_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5,
    "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10,
    "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}


def _dec(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_ar_date(value) -> dt.date | None:
    """'1 أغسطس 2027م' -> date(2027, 8, 1). Returns None if unparseable."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.date() if isinstance(value, dt.datetime) else value
    if not value:
        return None
    text = str(value)
    day = re.search(r"\b(\d{1,2})\b", text)
    year = re.search(r"\b(20\d{2})\b", text)
    month = next((num for name, num in _AR_MONTHS.items() if name in text), None)
    if day and month and year:
        try:
            return dt.date(int(year.group(1)), month, int(day.group(1)))
        except ValueError:
            return None
    return None


def _header_map(ws, header_row: int = 1) -> dict[int, str]:
    return {
        c: str(ws.cell(header_row, c).value).strip()
        for c in range(1, ws.max_column + 1)
        if ws.cell(header_row, c).value is not None
    }


class Command(BaseCommand):
    help = "Seed IsicSector, EtimadCommodity, MandatoryMinThreshold, GlobalWhitelist from LCGPA xlsx."

    def add_arguments(self, parser):
        default_dir = (Path(settings.BASE_DIR).parent / "docs" / "lcgpa")
        parser.add_argument("--source-dir", default=str(default_dir))

    def handle(self, *args, **opts):
        src = Path(opts["source_dir"])
        if not src.exists():
            raise CommandError(f"Source dir not found: {src}")

        self.seed_appendix_b(src / F_SCORE_TEMPLATE)
        self.seed_mandatory_list(src / F_MANDATORY)
        self.seed_min_thresholds(src / F_MIN_PCT)
        self.seed_global_whitelist()
        self.stdout.write(self.style.SUCCESS("LCGPA seed complete."))

    # --- Appendix B -> IsicSector --------------------------------------------
    def seed_appendix_b(self, path: Path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"skip Appendix B (missing {path.name})"))
            return
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb["Appendix B"]
        # The template indents content: Sector=col 2, Score=col 3, Description=col 4.
        col_sector, col_score, col_desc = 2, 3, 4
        count = 0
        for r in range(1, ws.max_row + 1):
            code = ws.cell(r, col_sector).value
            score = _dec(ws.cell(r, col_score).value)
            if not code or score is None or "Sector" == str(code).strip():
                continue
            code = str(code).strip()
            kind = (
                IsicSector.Kind.GOODS if "GOODS" in code.upper()
                else IsicSector.Kind.SERVICES if "SERVICES" in code.upper() else ""
            )
            IsicSector.objects.update_or_create(
                code=code,
                defaults={
                    "name_en": code,
                    "kind": kind,
                    "baseline_lc_score": score,
                    "description": str(ws.cell(r, col_desc).value or ""),
                },
            )
            count += 1
        self.stdout.write(f"  IsicSector: {count} sectors")

    # --- Mandatory List -> EtimadCommodity -----------------------------------
    def seed_mandatory_list(self, path: Path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"skip Mandatory List (missing {path.name})"))
            return
        wb = openpyxl.load_workbook(path, data_only=True)
        total = 0
        for ws in wb.worksheets:
            headers = _header_map(ws)
            joined = " ".join(headers.values())
            if "اعتماد" not in joined and "Etimad" not in joined:
                continue  # overview / exclusion-rule sheets

            cols = self._mandatory_columns(headers)
            if "etimad" not in cols:
                continue
            seg, seg_ar, seg_en = None, "", ""  # forward-fill across merged cells
            for r in range(2, ws.max_row + 1):
                if cols.get("segment"):
                    v = ws.cell(r, cols["segment"]).value
                    if v not in (None, ""):
                        seg = str(v).strip()
                        seg_ar = str(ws.cell(r, cols.get("sector_ar", 0)).value or "") if cols.get("sector_ar") else seg_ar
                        seg_en = str(ws.cell(r, cols.get("sector_en", 0)).value or "") if cols.get("sector_en") else seg_en
                etimad = ws.cell(r, cols["etimad"]).value
                if etimad in (None, ""):
                    continue
                EtimadCommodity.objects.update_or_create(
                    etimad_code=str(etimad).strip(),
                    sector_sheet=ws.title,
                    defaults={
                        "segment_no": seg or "",
                        "name_ar": str(ws.cell(r, cols.get("name_ar", 0)).value or "") if cols.get("name_ar") else "",
                        "name_en": str(ws.cell(r, cols.get("name_en", 0)).value or "") if cols.get("name_en") else "",
                        "desc_ar": str(ws.cell(r, cols.get("desc_ar", 0)).value or "") if cols.get("desc_ar") else "",
                        "desc_en": str(ws.cell(r, cols.get("desc_en", 0)).value or "") if cols.get("desc_en") else "",
                        "is_mandatory": True,
                    },
                )
                total += 1
        self.stdout.write(f"  EtimadCommodity: {total} products")

    @staticmethod
    def _mandatory_columns(headers: dict[int, str]) -> dict[str, int]:
        cols: dict[str, int] = {}
        for c, h in headers.items():
            t = h.replace("\n", " ")
            if "Segment" in t or "رقم القطاع" in t:
                cols["segment"] = c
            elif "القطاع" in t and ("عربي" in t):
                cols["sector_ar"] = c
            elif "القطاع" in t and ("نجليزي" in t):
                cols["sector_en"] = c
            elif "اعتماد" in t or "Etimad" in t:
                cols["etimad"] = c
            elif "اسم المنتج" in t and "عربي" in t:
                cols["name_ar"] = c
            elif "اسم المنتج" in t and "نجليزي" in t:
                cols["name_en"] = c
            elif "وصف المنتج" in t and "عربي" in t:
                cols["desc_ar"] = c
            elif "وصف المنتج" in t and "نجليزي" in t:
                cols["desc_en"] = c
        return cols

    # --- Minimum percentage -> MandatoryMinThreshold -------------------------
    def seed_min_thresholds(self, path: Path):
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"skip Min %% (missing {path.name})"))
            return
        wb = openpyxl.load_workbook(path, data_only=True)
        total = 0
        for ws in wb.worksheets:
            etimad_col = None
            date_col = None
            year_cols: dict[int, int] = {}  # column -> year
            for r in range(1, min(ws.max_row, 5000) + 1):
                row = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
                # Detect a header row and (re)build the column map.
                if any(isinstance(v, str) and "الرمز في منصة اعتماد" in v for v in row):
                    etimad_col = date_col = None
                    year_cols = {}
                    for c, v in enumerate(row, start=1):
                        if not isinstance(v, str):
                            continue
                        if "اعتماد" in v:
                            etimad_col = c
                        elif "تاريخ" in v:
                            date_col = c
                        else:
                            m = re.search(r"لعام\s*(20\d{2})", v)
                            if m:
                                year_cols[c] = int(m.group(1))
                    continue
                if etimad_col is None or not year_cols:
                    continue
                etimad = ws.cell(r, etimad_col).value
                if etimad in (None, ""):
                    continue
                eff = _parse_ar_date(ws.cell(r, date_col).value) if date_col else None
                for c, year in year_cols.items():
                    pct = _dec(ws.cell(r, c).value)
                    if pct is None:
                        continue
                    MandatoryMinThreshold.objects.update_or_create(
                        etimad_code=str(etimad).strip(),
                        year=year,
                        defaults={"min_pct": pct, "effective_date": eff},
                    )
                    total += 1
        self.stdout.write(f"  MandatoryMinThreshold: {total} rows")

    # --- Global Whitelist seed (verified KSA entities) -----------------------
    def seed_global_whitelist(self):
        seeds = [
            # name, vat, cr, lc_score
            ("SABIC", "300000000000003", "1010010813", Decimal("0.75")),
            ("Saudi Aramco", "300000000000103", "2052101150", Decimal("0.70")),
            ("STC (Saudi Telecom Company)", "300000000000203", "1010150269", Decimal("0.68")),
        ]
        for name, vat, cr, score in seeds:
            GlobalWhitelistEntry.objects.update_or_create(
                vat_number=vat,
                defaults={
                    "vendor_name_norm": name.upper(),
                    "cr_number": cr,
                    "lc_score": score,
                    "financial_year": 2026,
                    "version": 1,
                },
            )
        self.stdout.write(f"  GlobalWhitelistEntry: {len(seeds)} seed vendors")
