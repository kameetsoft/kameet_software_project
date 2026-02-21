# pdf2excel/m_indian_1.py
# -*- coding: utf-8 -*-
"""
Indian Bank extractor module (01 Jan 2025 - 31 Mar 2025 format)

Usage:
    from pdf2excel.m_indian_1 import indian_1
    tables = indian_1([r"C:\path\to\INDIAN_BANK.pdf"], ["password1", "password2"])
    # tables = [ [ [bank_name, account_no, "", "", "", ""],
    #              ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
    #              [rows...]
    #            ],
    #            ... (one table per account across input PDFs)
    #          ]
"""

import re
from typing import List, Any, Optional, Tuple
import pdfplumber
from dateutil import parser as dtparse
from dateutil.parser import ParserError

BANK_NAME = "INDIAN BANK"

# --- date & amount regex ------------------------------------------------------
# Supports: "05 Jan 2025" and dd/mm/yyyy or dd-mm-yyyy
DATE_WORD_RX = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[A-Za-z]*\s+"
    r"(19|20)\d{2}\b",
    re.I,
)
DATE_NUM_RX = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/(19|20)\d{2}\b",
    re.I,
)

# AMT_TOKEN_RX = re.compile(r"(?:-|INR\s*[\d,]+\.\d{1,2})", re.I)
# AMT_RX       = re.compile(r"INR\s*([\d,]+\.\d{1,2})", re.I)

AMT_TOKEN_RX = re.compile(r"(?:-|INR\s*[\d,]+\.\d{1,2}\s*(?:CR|DR)?)", re.I)
AMT_RX       = re.compile(r"INR\s*([\d,]+\.\d{1,2})", re.I)

# --- page text noise / headers ------------------------------------------------
FOOTER_RX = re.compile(
    r"(?:ACCOUNT\s+STATEMENT|ACCOUNT\s+DETAILS|ACCOUNT\s+SUMMARY|ACCOUNT\s+ACTIVITY|"
    r"For\s+period:|Ending\s+Balance\s+INR|^Total\s+INR|Indian\s+Bank\s*\|)",
    re.I,
)

TABLE_HEAD_RX = re.compile(
    r"^\s*Date\s+Transaction\s+Details\s+Debits\s+Credits\s+Balance\s*$",
    re.I,
)

# For text fallback: capture body + 3 trailing cells (debit, credit, balance)
# TAIL_THREE_CELLS_RX = re.compile(
#     r"(?s)^(?P<body>.*?)(?P<deb>-|INR\s*[\d,]+\.\d{1,2})\s+"
#     r"(?P<cred>-|INR\s*[\d,]+\.\d{1,2})\s+"
#     r"(?P<bal>INR\s*[\d,]+\.\d{1,2})\s*$",
#     re.I,
# )
MONTH_WORDS = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"

# day-first e.g. "05 Jan 2025"
DATE_WORD_DMY_RX = re.compile(
    rf"\b(0?[1-9]|[12][0-9]|3[01])\s+{MONTH_WORDS}[A-Za-z]*\s+(19|20)\d{{2}}\b",
    re.I,
)
# month-first e.g. "Jan 05 2025"
DATE_WORD_MDY_RX = re.compile(
    rf"\b{MONTH_WORDS}[A-Za-z]*\s+(0?[1-9]|[12][0-9]|3[01])\s+(19|20)\d{{2}}\b",
    re.I,
)

DATE_NUM_RX = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/(19|20)\d{2}\b",
    re.I,
)
TAIL_THREE_CELLS_RX = re.compile(
    r"(?s)^(?P<body>.*?)(?P<deb>-|INR\s*[\d,]+\.\d{1,2}\s*(?:CR|DR)?)\s+"
    r"(?P<cred>-|INR\s*[\d,]+\.\d{1,2}\s*(?:CR|DR)?)\s+"
    r"(?P<bal>INR\s*[\d,]+\.\d{1,2}\s*(?:CR|DR)?)\s*$",
    re.I,
)
# --- helpers ------------------------------------------------------------------
def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
    for pwd in (passwords or []) + [None]:
        try:
            return pdfplumber.open(pdf_path, password=pwd)
        except Exception:
            continue
    return None

# def _norm_date(s: str) -> str:
#     if not s:
#         return ""
#     try:
#         dt = dtparse.parse(s.strip(), dayfirst=True)
#         if dt.year < 1990 or dt.year > 2100:
#             return ""
#         return dt.strftime("%d-%m-%Y")
#     except (ParserError, ValueError, TypeError):
#         return ""

def _norm_date(s: str) -> str:
    """Normalize to dd-mm-yyyy from any supported style."""
    if not s:
        return ""
    try:
        dt = dtparse.parse(s.strip(), dayfirst=True)  # handles both "05 Jan 2025" and "Jan 05 2025"
        if 1990 <= dt.year <= 2100:
            return dt.strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError):
        pass
    return ""
def _as_float(x: Any) -> float:
    if x is None:
        return 0.0
    s = str(x)
    s_clean = re.sub(r"[^\d\.\-]", "", s)
    if s_clean in ("", "-", "--", "."):
        return 0.0
    try:
        return float(s_clean)
    except Exception:
        return 0.0

def _find_account_number(text: str) -> Optional[str]:
    # Seen as: Account Number 7583079678
    m = re.search(r"Account\s*Number\s*[:\-]?\s*(\d{6,20})", text, flags=re.I)
    if m:
        return m.group(1)
    return None

# --- table collection ---------------------------------------------------------
def _looks_indian_header_row(row: List[str]) -> bool:
    s = " ".join((row or [])).strip()
    return bool(TABLE_HEAD_RX.search(s))

def _collect_tables(page: pdfplumber.page.Page):
    """
    Keep tables that look like Indian Bank grids with the header
    'Date Transaction Details Debits Credits Balance' in the top few rows.
    Include a text-strategy fallback to catch loose grids.
    """
    STRATEGIES = [
        dict(vertical_strategy="lines", horizontal_strategy="lines",
             intersection_tolerance=3, snap_tolerance=3, join_tolerance=3),
        dict(vertical_strategy="lines", horizontal_strategy="lines",
             intersection_tolerance=5, snap_tolerance=4, join_tolerance=4),
        dict(vertical_strategy="text", horizontal_strategy="text",
             snap_tolerance=3),
    ]

    out, seen_sig = [], set()
    for ts in STRATEGIES:
        try:
            tables = page.extract_tables(ts) or []
        except Exception:
            continue
        for tbl in tables:
            cleaned = [[(c or "").strip() for c in (row or [])] for row in (tbl or [])]
            if not cleaned:
                continue
            n_rows = len(cleaned)
            n_cols = max((len(r) for r in cleaned if r), default=0)
            if n_cols < 4 or n_cols > 30 or n_rows > 5000:
                continue
            has_header = any(_looks_indian_header_row(r) for r in cleaned[:8])
            if not has_header:
                # Allow body-like chunks if first cell has a date and last cells look numeric
                head = cleaned[:5]
                date_hits, num_hits = 0, 0
                for r in head:
                    left = " ".join(str(c or "") for c in r[:2])
                    if DATE_WORD_RX.search(left) or DATE_NUM_RX.search(left):
                        date_hits += 1
                    right = " ".join(str(c or "") for c in r[-3:])
                    if re.search(r"\d", right):
                        num_hits += 1
                if not (date_hits >= 1 and num_hits >= 2):
                    continue
            sig = (n_rows, n_cols, tuple(len(r) for r in cleaned[:2]))
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            out.append(cleaned)
    return out

def _find_header_idx(tbl: List[List[str]]) -> int:
    for i, r in enumerate(tbl[:8]):
        if _looks_indian_header_row(r):
            return i
    return -1

def _split_clean_lines(page_text: str) -> List[str]:
    if not page_text:
        return []
    page_text = re.sub(r"[\u200B\u00A0]", " ", page_text)

    raw = [ln.strip() for ln in page_text.splitlines() if ln.strip()]

    out, in_table = [], False
    for ln in raw:
        if TABLE_HEAD_RX.search(ln):
            in_table = True
            continue
        if not in_table:
            continue
        # stop at obvious page footers/summaries
        if re.search(r"Ending\s+Balance", ln, re.I): break
        if re.search(r"^Total\s+INR", ln): break
        if re.search(r"Indian\s+Bank\s*\|\s*\|\s*\d+/\d+", ln): break
        if FOOTER_RX.search(ln): 
            # ignore generic header/footer noise inside the table scan
            continue
        out.append(ln)
    return out

# def _is_date_line(s: str) -> Optional[str]:
#     m = DATE_WORD_RX.search(s)
#     if m:
#         return m.group(0)
#     m = DATE_NUM_RX.search(s)
#     if m:
#         return m.group(0)
#     return None

def _is_date_line(s: str) -> Optional[str]:
    if not s:
        return None
    for rx in (DATE_WORD_DMY_RX, DATE_WORD_MDY_RX, DATE_NUM_RX):
        m = rx.search(s)
        if m:
            return m.group(0)
    return None
def _parse_block(block_lines: List[str]) -> Optional[List[Any]]:
    """
    block_lines: ["05 Jan 2025 ...", "...continued...", "... tail amounts ..."]
    We always take the LAST three amount-like tokens as: <deb or -> <cred or -> <INR balance>,
    then remove those tokens from the string so narration includes lines after them.
    """
    if not block_lines:
        return None

    joined = " ".join(bl.strip() for bl in block_lines if bl.strip())

    # 1) date
    date_str = _is_date_line(joined)
    nd = _norm_date(date_str or "")
    if not nd:
        return None

    # 2) drop the first date occurrence
    s = re.sub(re.escape(date_str), "", joined, count=1).strip()

    # 3) find all amount-like tokens with spans; take LAST 3
    matches = list(re.finditer(r"(?:-|INR\s*[\d,]+\.\d{1,2})", s, re.I))
    if len(matches) < 3:
        return None
    deb_m, cred_m, bal_m = matches[-3], matches[-2], matches[-1]
    deb_tok, cred_tok, bal_tok = deb_m.group(0), cred_m.group(0), bal_m.group(0)

    # 4) numbers
    def _num(tok: str) -> float:
        m = re.search(r"INR\s*([\d,]+\.\d{1,2})", tok, re.I)
        return _as_float(m.group(1)) if m else 0.0

    withdraw = _num(deb_tok)
    deposit  = _num(cred_tok)
    bal_val  = _num(bal_tok)

    # 5) remove the last three tokens from the string (right-to-left) so narration keeps all lines
    s_list = list(s)
    for m in (bal_m, cred_m, deb_m):
        for i in range(m.start(), m.end()):
            s_list[i] = " "
    body = re.sub(r"\s+", " ", "".join(s_list)).strip()

    # n1, n2 = body[:90], body[90:]
    n1, n2 = re.sub(r"\s+", " ", body).strip(), ""

    return [nd, n1, n2, withdraw, deposit, bal_val]

def _parse_rows_from_text(page_text: str) -> List[List[Any]]:
    lines = _split_clean_lines(page_text)
    out, curr = [], []
    for ln in lines:
        # skip table header lines
        if TABLE_HEAD_RX.search(ln):
            continue
        if _is_date_line(ln):
            # flush previous
            if curr:
                row = _parse_block(curr)
                if row:
                    out.append(row)
                curr = []
            curr.append(ln)
        else:
            if curr:
                curr.append(ln)
            else:
                # orphan text before first date; ignore
                pass
    if curr:
        row = _parse_block(curr)
        if row:
            out.append(row)
    return out

# --- main ---------------------------------------------------------------------
def indian_1(pdf_paths: List[str], passwords: List[str]):
    """
    Parse Indian Bank statements like:
    Date | Transaction Details | Debits | Credits | Balance

    Returns your standard list-of-tables format.
    """
    data_table: List[List[List[Any]]] = []

    for pdf_path in pdf_paths:
        pdf = _open_pdf(pdf_path, passwords)
        if not pdf:
            continue
        try:
            # account number (first couple pages)
            account_no = ""
            try:
                for p in pdf.pages[:3]:
                    t = p.extract_text() or ""
                    acct = _find_account_number(t)
                    if acct:
                        account_no = acct
                        break
            except Exception:
                pass
            if not account_no:
                account_no = "Unknown-1"

            rows_out: List[List[Any]] = []
            seen = set()
            MAX_ROWS = 5000
            added = 0

            # remember header mapping if a table split continues across chunks
            last_cols: Optional[Tuple[int, int, int, int, int]] = None  # date, details, debit, credit, balance

            for page in pdf.pages:
                page_added_before = added
                tables = _collect_tables(page)

                # ---------- table path ----------
                if tables:
                    for tbl in tables:
                        if not tbl:
                            continue
                        h_idx = _find_header_idx(tbl)
                        if h_idx >= 0:
                            header = [c.upper() for c in (tbl[h_idx] if h_idx < len(tbl) else [])]

                            def _col(name_parts, default=None):
                                for i, h in enumerate(header):
                                    if all(part in h for part in name_parts):
                                        return i
                                return default

                            c_date = _col(["DATE"], 0)
                            # The header text is "Transaction Details"
                            c_det  = _col(["TRANSACTION", "DETAIL"], 1)
                            c_deb  = _col(["DEBIT"], 2)
                            c_cre  = _col(["CREDIT"], 3)
                            c_bal  = _col(["BALANCE"], 4)
                            last_cols = (c_date, c_det, c_deb, c_cre, c_bal)
                            body = tbl[h_idx + 1 :]
                        else:
                            if not last_cols:
                                continue
                            c_date, c_det, c_deb, c_cre, c_bal = last_cols
                            body = tbl

                        for r in body:
                            # REPLACE the simple "for r in body:" loop with this block (inside the table path)
                            i = 0
                            while i < len(body):
                                r = body[i]
                                if not r or all(not (x or "").strip() for x in r):
                                    i += 1
                                    continue

                                def cell(row, ci):
                                    return (row[ci] if (ci is not None and 0 <= ci < len(row)) else "") or ""

                                joined = " ".join(str(x or "") for x in r)
                                # skip header repeats
                                if TABLE_HEAD_RX.search(joined):
                                    i += 1
                                    continue

                                # Find date for the START row of a block
                                date_raw = cell(r, c_date)
                                nd = _norm_date(date_raw) or _norm_date(_is_date_line(joined) or "")
                                if not nd:
                                    # Not a new txn block; just move on
                                    i += 1
                                    continue

                                # --- start a multi-row transaction block ---
                                det_lines = []

                                # pull details from current row (not the amount columns)
                                first_det = cell(r, c_det)
                                extras = []
                                for ci, val in enumerate(r):
                                    if ci in (c_date, c_deb, c_cre, c_bal, c_det):
                                        continue
                                    if val and not AMT_RX.search(str(val)):
                                        extras.append(str(val))
                                if first_det or extras:
                                    det_lines.append(" ".join([x for x in [first_det] + extras if x]).strip())

                                # initialize amounts from this row (may be empty; likely picked in later row)
                                deb_v = _as_float(cell(r, c_deb))
                                cre_v = _as_float(cell(r, c_cre))
                                bal_v = _as_float(cell(r, c_bal))

                                # look ahead to stitch continuation rows until we hit an "amount row" or next date
                                j = i + 1
                                while j < len(body):
                                    r2 = body[j]
                                    if not r2:
                                        j += 1
                                        continue

                                    j_join = " ".join(str(x or "") for x in r2)

                                    # stop if we see the table header or the next transaction date
                                    if TABLE_HEAD_RX.search(j_join) or _norm_date(_is_date_line(j_join) or ""):
                                        break

                                    # is this an "amount row"? (one of debit/credit/balance has digits/INR)
                                    deb_tok = cell(r2, c_deb)
                                    cre_tok = cell(r2, c_cre)
                                    bal_tok = cell(r2, c_bal)
                                    has_amounts = any(re.search(r"\d", str(t)) for t in (deb_tok, cre_tok, bal_tok))

                                    # collect any extra details text on this row
                                    row_det = cell(r2, c_det)
                                    row_extras = []
                                    for ci, val in enumerate(r2):
                                        if ci in (c_date, c_deb, c_cre, c_bal, c_det):
                                            continue
                                        if val and not AMT_RX.search(str(val)):
                                            row_extras.append(str(val))
                                    if row_det or row_extras:
                                        det_lines.append(" ".join([x for x in [row_det] + row_extras if x]).strip())

                                    if has_amounts:
                                        # amounts/balance are finalized on this row
                                        deb_v = _as_float(deb_tok)
                                        cre_v = _as_float(cre_tok)
                                        bal_v = _as_float(bal_tok)
                                        j += 1  # consume this amounts row
                                        break

                                    j += 1

                                # finalize this transaction
                                full_det = re.sub(r"\s+", " ", " ".join(d for d in det_lines if d)).strip()
                                # n1, n2 = full_det[:90], full_det[90:]
                                n1, n2 = re.sub(r"\s+", " ", full_det).strip(), ""


                                sig = (nd, full_det, f"{deb_v:.2f}", f"{cre_v:.2f}", f"{bal_v:.2f}")
                                if sig not in seen:
                                    rows_out.append([nd, n1, n2, deb_v, cre_v, bal_v])
                                    seen.add(sig)
                                    added += 1
                                    if added >= MAX_ROWS:
                                        break

                                # advance to the first row after this stitched block
                                i = j

                        if added >= MAX_ROWS:
                            break

                # ---------- text fallback (if table contributed nothing on this page) ----------
                if added == page_added_before:
                    txt = page.extract_text() or ""
                    extra_rows = _parse_rows_from_text(txt)
                    for row in extra_rows:
                        nd, n1, n2, wd, dp, bal = row
                        sig = (nd, re.sub(r"\s+", " ", (n1 + " " + n2)).strip(), f"{wd:.2f}", f"{dp:.2f}", f"{bal:.2f}")
                        if sig in seen:
                            continue
                        rows_out.append([nd, n1, n2, wd, dp, bal])
                        seen.add(sig)
                        added += 1
                        if added >= MAX_ROWS:
                            break

            if rows_out:
                account_row = [BANK_NAME, account_no, "", "", "", ""]
                headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
                data_table.append([account_row, headers] + rows_out)
        finally:
            try:
                pdf.close()
            except Exception:
                pass

    return data_table
