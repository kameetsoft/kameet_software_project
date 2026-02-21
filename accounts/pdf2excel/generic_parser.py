# pdf2excel/generic_parser.py
# -*- coding: utf-8 -*-
"""
Generic header-driven parser for *any* bank statement PDF.

Output format (per account):
[
  [ [BANK_NAME, ACCOUNT_ID, "", "", "", ""],
    ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
    [row...],
    [row...],
  ],
  ...
]

- Tries line-based table extraction, falls back to text-based.
- Detects headers by synonyms (DATE/NARRATION/DEBIT/CREDIT/BALANCE/etc).
- Accepts mixed banks, masked accounts (XXXX1234), and unknown accounts.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import pdfplumber
from dateutil import parser as dtparser
from dateutil.parser import ParserError

# --- Config -------------------------------------------------------------------

BANK_FALLBACK_NAME = "BANK"

# Accepts 04-04-24 / 04/04/2024 / 4-4-2024 etc.
# DATE_RX = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
# NEW
DATE_RX = re.compile(r"\b\d{1,2}[-/\s](?:\d{1,2}|[A-Za-z]{3})[-/\s]\d{2,4}\b")


# Header synonyms → canonical keys
HEADER_SYNONYMS: Dict[str, List[str]] = {
    "DATE":      [r"\bDATE\b", r"\bTRANS?\s*DATE\b", r"\bVALU?E?\s*DATE\b"],
    "NARRATION": [r"\bNARRATION\b", r"\bDESCRIPTION\b", r"\bPARTICULARS?\b", r"\bDETAILS?\b"],
    "REFNO":     [r"\bCHQ(?:\.| |-|/)?(?:NO|NUMBER)\b", r"\bREF(?:\.| |-|/)?NO\b", r"\bCHEQUE\b"],
    "DEBIT":     [r"\bDEBIT\b", r"\bWITHDRAWAL\b", r"\bDR\b"],
    "CREDIT":    [r"\bCREDIT\b", r"\bDEPOSIT\b", r"\bCR\b"],
    "BALANCE":   [r"\bBALANCE\b", r"\bCLOS(?:ING)?\s*BAL(ANCE)?\b", r"\bCL\s*BAL\b"],
}

# Account number (incl. masked) patterns found in page text
ACCOUNT_HINTS: List[str] = [
    r"\bACCOUNT\s*NUMBER\s*[:\-]?\s*(\d{8,20})",
    r"\bA/C\s*NO\.?\s*[:\-]?\s*(\d{8,20})",
    r"\bSAVINGS\s*ACCOUNT.*?(\d{8,20})",
    r"\bCURRENT\s*ACCOUNT.*?(\d{8,20})",
    r"\bX{3,}\s*\d{3,8}",  # XXXXXXXX1234 style
]

# --- Helpers ------------------------------------------------------------------

def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
    """Try passwords then None; return an open pdfplumber.PDF or None."""
    for pwd in (passwords or []) + [None]:
        try:
            return pdfplumber.open(pdf_path, password=pwd)
        except Exception:
            continue
    return None

def _clean_amount(x) -> float:
    """Convert value like '1,234.56 CR' or '12,345 DR' or '-' to float; sign handled separately."""
    s = re.sub(r"[^\d\.\-]", "", str(x or "")).strip()
    if s in ("", "-", "--", "."):
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def _norm_date(s: str) -> str:
    try:
        dt = dtparser.parse(s.strip(), dayfirst=True)
        return dt.strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError, AttributeError):
        return ""

def _looks_like_header(row: List[str]) -> bool:
    """True if row hits ≥ 3 header synonyms across all canonical keys."""
    if not row:
        return False
    s = " ".join((c or "").upper() for c in row)
    hits = 0
    for pats in HEADER_SYNONYMS.values():
        for rx in pats:
            if re.search(rx, s, flags=re.I):
                hits += 1
                break
    return hits >= 3

def _header_index_map(header_row: Optional[List[str]]) -> Dict[str, int]:
    """Map canonical header → column index using HEADER_SYNONYMS."""
    idx: Dict[str, int] = {}
    if not header_row:
        return idx
    for i, h in enumerate(header_row):
        token = (h or "").upper().strip()
        for key, patterns in HEADER_SYNONYMS.items():
            for rx in patterns:
                if re.search(rx, token, flags=re.I):
                    if key not in idx:  # keep first match per key
                        idx[key] = i
                    break
    return idx

def _collect_tables(page: pdfplumber.page.Page) -> List[List[List[str]]]:
    """Extract tables: first with line strategies, fallback to text strategies."""
    # Lines
    tables = page.extract_tables({
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_tolerance": 3,
    }) or []
    # Text fallback
    if not tables:
        tables = page.extract_tables({
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 3,
        }) or []
    # Clean cells
    out: List[List[List[str]]] = []
    for tbl in tables:
        out.append([[(c or "").strip() for c in (row or [])] for row in (tbl or [])])
    return out

def _pick_header_and_rows(tbl: List[List[str]]) -> Tuple[Optional[List[str]], List[List[str]]]:
    """Find header row and return (header_row, body_rows)."""
    if not tbl:
        return None, []
    header_idx = None
    # look top ~6 rows
    for r, row in enumerate(tbl[:6]):
        if _looks_like_header(row):
            header_idx = r
            break
    # fallback: a row followed by a row with a date in it
    if header_idx is None:
        for r in range(min(3, len(tbl) - 1)):
            if DATE_RX.search(" ".join(tbl[r + 1])):
                header_idx = r
                break
    if header_idx is None:
        return None, tbl
    return tbl[header_idx], tbl[header_idx + 1:]

def _detect_account(text: str) -> Optional[str]:
    """Find account or masked account in page text."""
    up = text or ""
    for rx in ACCOUNT_HINTS:
        m = re.search(rx, up, flags=re.I)
        if m:
            g = m.group(1) if m.lastindex else m.group(0)
            return g.replace(" ", "")
    return None

# --- Core ---------------------------------------------------------------------

def parse_generic(pdf_paths: List[str], passwords: List[str]):
    """
    Generic parser for arbitrary bank statements.

    Returns list of tables (per account) with your standard schema.
    """
    data_table: List[List[List[Any]]] = []   # final: [[account_row, headers] + rows] *

    for pdf_path in pdf_paths:
        pdf = _open_pdf(pdf_path, passwords)
        if not pdf:
            # Can't open with any password → skip this file
            continue

        # Hold rows grouped by detected account id
        accounts: Dict[str, List[List[Any]]] = {}
        account_seq = 0
        current_acct: Optional[str] = None

        try:
            # Try to read first text chunk to guess BANK name (nice to have)
            first_text = ""
            try:
                if pdf.pages:
                    first_text = (pdf.pages[0].extract_text() or "").strip()
            except Exception:
                pass
            bank_name = BANK_FALLBACK_NAME
            # quick bank name heuristic
            for bn in ["AXIS", "HDFC", "ICICI", "SBI", "BANK OF BARODA", "BANK OF MAHARASHTRA", "PUNJAB NATIONAL BANK", "PNB","SARVODAYA", "SPCB", "SUTEX"]:
                if re.search(rf"\b{re.escape(bn)}\b", first_text, flags=re.I):
                    bank_name = bn
                    break

            for page in pdf.pages:
                page_text = page.extract_text() or ""

                # Update/seed current account if we find one on this page
                acct = _detect_account(page_text)
                if acct:
                    current_acct = acct
                if not current_acct:
                    # Create a synthetic account bucket (Unknown-N)
                    account_seq += 1
                    current_acct = f"Unknown-{account_seq}"
                if current_acct not in accounts:
                    accounts[current_acct] = []

                # Extract tables on this page
                for tbl in _collect_tables(page):
                    if not tbl or len(tbl) < 2:
                        continue

                    header_row, body_rows = _pick_header_and_rows(tbl)
                    colmap = _header_index_map(header_row)

                    for r in body_rows:
                        if not r:
                            continue

                        # Find date cell
                        date_cell: Optional[str] = None
                        if "DATE" in colmap and colmap["DATE"] < len(r):
                            date_cell = r[colmap["DATE"]]
                        else:
                            # scan whole row
                            for cell in r:
                                if DATE_RX.search(str(cell)):
                                    date_cell = cell
                                    break
                        if not date_cell:
                            continue

                        nd = _norm_date(date_cell)
                        if not nd:
                            continue

                        # Narration + RefNo
                        if "NARRATION" in colmap and colmap["NARRATION"] < len(r):
                            full_narr = (r[colmap["NARRATION"]] or "").replace("\n", " ").strip()
                        else:
                            # heuristic: pick the longest text cell as narration
                            texts = [str(c) for c in r if isinstance(c, str)]
                            full_narr = max(texts, key=len) if texts else ""
                        refno = ""
                        if "REFNO" in colmap and colmap["REFNO"] < len(r):
                            refno = (r[colmap["REFNO"]] or "").replace("\n", " ").strip()

                        narr1 = full_narr[:90]
                        narr2 = (full_narr[90:] + ("  " + refno if refno else "")).strip()

                        # Amounts
                        debit = _clean_amount(r[colmap["DEBIT"]]) if "DEBIT" in colmap and colmap["DEBIT"] < len(r) else 0.0
                        credit = _clean_amount(r[colmap["CREDIT"]]) if "CREDIT" in colmap and colmap["CREDIT"] < len(r) else 0.0

                        # Balance (handle DR/CR sign if embedded in cell text)
                        if "BALANCE" in colmap and colmap["BALANCE"] < len(r):
                            raw_bal = str(r[colmap["BALANCE"]] or "")
                        else:
                            raw_bal = str(r[-1] if r else "")
                        bal = _clean_amount(raw_bal)
                        if re.search(r"\bDR\b", raw_bal, flags=re.I) and bal > 0:
                            bal = -bal  # DR as negative if not already

                        accounts[current_acct].append([nd, narr1, narr2, debit, credit, bal])

            # Pack per account into final tables
            for acct, rows in accounts.items():
                if not rows:
                    continue
                account_row = [bank_name, acct, "", "", "", ""]
                headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

                # Merge if same account already exists in data_table
                merged = False
                for existing in data_table:
                    if existing and existing[0][1] == acct:
                        existing.extend(rows)
                        merged = True
                        break
                if not merged:
                    data_table.append([account_row, headers] + rows)

        finally:
            try:
                pdf.close()
            except Exception:
                pass

    return data_table
