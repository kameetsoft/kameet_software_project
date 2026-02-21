# -*- coding: utf-8 -*-
"""
IDBI 'Choice Point' extractor
Layout typically shows:
  Sr | Date | Description | Amount | Type (Cr/Dr)
Sample line:
  1. 05-AUG-25 NEFT-HDFCH00403397123-CHOICE POINT KIDS WEAR 5,000.00 Cr

API (BOB-like):
    from accounts.pdf2excel.m_idbi_choicepoint import idbi_choicepoint
    tables = idbi_choicepoint([r"...\choice point idbi.pdf"], [None, "pwd"])
    -> [
         [
           ["IDBI", "1115102000001809", "", "", "", ""],
           ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
           ["05-08-2025","NEFT-HDFCH00403397123-CHOICE POINT KIDS WEAR","",0.0,5000.0,0.0],
           ...
         ]
       ]
"""
import re
from typing import List, Any, Optional
import pdfplumber
from dateutil import parser as dtparse
from dateutil.parser import ParserError

BANK_NAME = "IDBI"

# ---------- regex ----------
# Account number line usually: "Account Number : 1115102000001809"
ACCT_RX = re.compile(r"Account\s*Number\s*[:\-]?\s*(\d{6,20})", re.I)

# Header row variations
HEAD_RX = re.compile(
    r"^\s*Sr\.?\s+Date\s+Description\s+Amount\s+Type\s*$",
    re.I,
)

# Transaction line:
# "1. 05-AUG-25 SOME TEXT ... 75,000.00 Dr"
TXN_RX = re.compile(
    r"""^\s*
        (?P<sr>\d+)\.\s+
        (?P<date>\d{2}-[A-Za-z]{3}-\d{2})\s+
        (?P<desc>.*?)\s+
        (?P<amt>[\d,]+\.\d{2})\s+
        (?P<typ>Cr|Dr)\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
    for pwd in (passwords or []) + [None]:
        try:
            return pdfplumber.open(pdf_path, password=pwd)
        except Exception:
            continue
    return None

def _as_float(s: str) -> float:
    if not s:
        return 0.0
    s2 = re.sub(r"[^\d\.\-]", "", str(s))
    if not s2 or s2 in ("-", ".", "--"):
        return 0.0
    try:
        return float(s2)
    except Exception:
        return 0.0

def _norm_date(s: str) -> str:
    """Normalize '05-AUG-25' -> '05-08-2025' (day-first)."""
    if not s:
        return ""
    try:
        dt = dtparse.parse(s.strip(), dayfirst=True)
        if dt.year < 1990:  # handle yy→19yy
            dt = dt.replace(year=dt.year + 100)
        return dt.strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError):
        return ""

def _maybe_account_no(text: str) -> Optional[str]:
    m = ACCT_RX.search(text or "")
    return m.group(1) if m else None

def _iter_lines_from_pages(pdf: pdfplumber.PDF) -> List[str]:
    out: List[str] = []
    for p in pdf.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        t = re.sub(r"[\u200B\u00A0]", " ", t)
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        out.extend(lines)
    return out

def _find_table_start_idx(lines: List[str]) -> int:
    for i, ln in enumerate(lines):
        if HEAD_RX.search(ln):
            return i
    return -1

def _parse_transactions(lines: List[str]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for ln in lines:
        m = TXN_RX.match(ln)
        if not m:
            continue
        nd = _norm_date(m.group("date"))
        desc = re.sub(r"\s+", " ", m.group("desc")).strip()
        amt = _as_float(m.group("amt"))
        typ = (m.group("typ") or "").strip().lower()

        wd = amt if typ == "dr" else 0.0
        dp = amt if typ == "cr" else 0.0
        rows.append([nd, desc, "", wd, dp, 0.0])  # no running balance in this layout
    return rows

def idbi_choicepoint(pdf_paths: List[str], passwords: List[str]) -> List[List[List[Any]]]:
    data_tables: List[List[List[Any]]] = []

    for path in pdf_paths:
        pdf = _open_pdf(path, passwords)
        if not pdf:
            continue
        try:
            # find account number (first couple of pages)
            account_no = ""
            try:
                for p in pdf.pages[:2]:
                    tt = p.extract_text() or ""
                    acct = _maybe_account_no(tt)
                    if acct:
                        account_no = acct
                        break
            except Exception:
                pass
            if not account_no:
                account_no = "Unknown"

            all_lines = _iter_lines_from_pages(pdf)
            start = _find_table_start_idx(all_lines)
            txn_lines = all_lines[start + 1 :] if start >= 0 else all_lines

            rows = _parse_transactions(txn_lines)
            if rows:
                header = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
                account_row = [BANK_NAME, account_no, "", "", "", ""]
                data_tables.append([account_row, header] + rows)
        finally:
            try:
                pdf.close()
            except Exception:
                pass

    return data_tables
