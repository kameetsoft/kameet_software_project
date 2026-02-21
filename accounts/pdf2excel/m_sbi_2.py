# # -*- coding: utf-8 -*-
# """
# SBI extractor for layout:
# 'Date  Details Ref No./Cheque No  Debit  Credit  Balance'
# (Transactions often wrap lines; time can appear in the Date cell)

# API (BOB-like):
#     from pdf2excel.m_sbi_2 import sbi_2
#     tables = sbi_2([r"...\file.pdf"], ["pwd1", "pwd2"])
#     -> [
#          [
#            ["SBI", "37678294053", "", "", "", ""],
#            ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#            ["04-04-2024","TRANSFER FROM ...","UPI/CR/40958...", "", "20000.00", "20953.01"],
#            ...
#          ]
#        ]
# """

# import re
# from typing import List, Tuple, Dict, Optional
# import pdfplumber
# from dateutil import parser as dtparse
# # from dateutil.parser import ParserError
# from dateutil.parser import parse as dtparse


# BANK_NAME = "SBI"

# # ------------ regex helpers ------------
# DATE_RX = re.compile(
#     r"\b(0?[1-9]|[12][0-9]|3[01])\s*[-/ ]\s*([A-Za-z]{3,9}|0?[1-9]|1[0-2])\s*[-/ ]\s*(\d{2,4})\b"
# )
# MONEY_RX = re.compile(r"(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?")

# # ------------ utils ------------
# def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
#     for pwd in (passwords or []) + [None]:
#         try:
#             return pdfplumber.open(pdf_path, password=pwd)
#         except Exception:
#             continue
#     return None

# # def _norm_date(txt: str) -> str:
# #     txt = (txt or "").strip()
# #     if not txt:
# #         return ""
# #     try:
# #         d = dtparse(txt, dayfirst=True, fuzzy=True)
# #         return d.strftime("%d-%m-%Y")
# #     except ParserError:
# #         return ""

# def _norm_date(txt: str):
#     try:
#         d = dtparse(txt, dayfirst=True, fuzzy=True)
#         return d.strftime("%d-%m-%Y")
#     except Exception:
#         return txt.strip()

# def _clean_money(s: Optional[str]) -> str:
#     if not s:
#         return ""
#     s = s.strip()
#     # strip currency tokens and trailing CR/DR
#     s = re.sub(r'^(?:Rs\.?|INR)\s*', '', s, flags=re.I)
#     s = re.sub(r'\s*(?:CR|DR)\b\.?$', '', s, flags=re.I)
#     # normalize commas and stray dash used as bullets
#     s = s.replace(",", "")
#     s = re.sub(r"^(?:-)\s*(?=\d)", "", s)
#     return s if MONEY_RX.fullmatch(s) else ""

# def _find_account_no(page: pdfplumber.page.Page) -> str:
#     txt = page.extract_text() or ""
#     m = re.search(r"Account\s*Number\s*[:\-]?\s*([0-9Xx*]{6,20})", txt, re.I)
#     if m:
#         v = m.group(1)
#         if re.search(r"\d{6,}", v):
#             return re.sub(r"[^\d]", "", v)
#     head = "\n".join((txt.splitlines() or [])[:40])
#     m2 = re.search(r"\b(\d{10,20})\b", head)
#     return m2.group(1) if m2 else ""

# # ------------ header finder (tolerant across nearby Y positions) ------------
# def _header_boxes(page: pdfplumber.page.Page) -> Optional[Dict[str, Tuple[float, float]]]:
#     """
#     Find column x-spans by clustering header tokens that may sit on slightly different Y rows.
#     We require 'Date', 'Debit', 'Credit', 'Balance'. 'Details' is optional; synthesized if missing.
#     """
#     words = page.extract_words(x_tolerance=3.0, y_tolerance=2.0, keep_blank_chars=False)
#     if not words:
#         return None

#     def pick(label: str):
#         return [w for w in words if w["text"].strip().lower() == label]

#     date_ws   = pick("date")
#     debit_ws  = pick("debit")
#     credit_ws = pick("credit")
#     bal_ws    = pick("balance")
#     detail_ws = [w for w in words if re.match(r"(details?|ref|cheque|no\.)", w["text"].strip(), re.I)]

#     if not (date_ws and debit_ws and credit_ws and bal_ws):
#         return None

#     # Choose a header row by taking a 'Date' candidate and the nearest others in Y;
#     # accept if their Y spread is within ~3px.
#     best_spans = None
#     for d in date_ws:
#         base_y = round(d["top"], 1)

#         def nearest(cands):
#             return min(cands, key=lambda w: abs(round(w["top"], 1) - base_y))

#         db  = nearest(debit_ws)
#         cr  = nearest(credit_ws)
#         ba  = nearest(bal_ws)
#         det = nearest(detail_ws) if detail_ws else None

#         ys = [round(w["top"], 1) for w in (d, db, cr, ba)] + ([round(det["top"], 1)] if det else [])
#         spread = max(ys) - min(ys)
#         if spread > 3.0:
#             continue

#         centers: Dict[str, float] = {
#             "date":   (d["x0"]  + d["x1"])  / 2.0,
#             "debit":  (db["x0"] + db["x1"]) / 2.0,
#             "credit": (cr["x0"] + cr["x1"]) / 2.0,
#             "balance":(ba["x0"] + ba["x1"]) / 2.0,
#         }
#         centers["details"] = ((det["x0"] + det["x1"]) / 2.0) if det else (centers["balance"] + centers["debit"]) / 2.0

#         ordered = sorted(centers.items(), key=lambda kv: kv[1])
#         spans: Dict[str, Tuple[float, float]] = {}
#         for i, (name, xc) in enumerate(ordered):
#             left  = ordered[i-1][1] if i > 0 else 0.0
#             right = ordered[i+1][1] if i < len(ordered) - 1 else page.width
#             margin = 6.0
#             x0 = max(0.0, (left + xc) / 2.0 - margin)
#             x1 = min(page.width, (xc + right) / 2.0 + margin)
#             spans[name] = (x0, x1)

#         best_spans = spans
#         break  # first acceptable cluster is good enough

#     return best_spans

# # ------------ helpers for row extraction ------------
# def _band(words, top, bot):
#     return [w for w in words if (w["top"] >= top and w["top"] < bot)]

# def _join_in_span(band_words, x0, x1) -> str:
#     sel = [w for w in band_words if ((w["x0"] + w["x1"]) / 2.0) >= x0 and ((w["x0"] + w["x1"]) / 2.0) <= x1]
#     sel = sorted(sel, key=lambda z: (round(z["top"], 1), z["x0"]))
#     txt = " ".join(w["text"] for w in sel)
#     return re.sub(r"\s+", " ", txt).strip()

# def _find_date_anchors(words, x0_date, x1_date):
#     """
#     Inside Date span, group by y, join tokens, and detect a date in the joined string.
#     Returns list of dicts with 'top' and 'text' (the matched date).
#     """
#     rows: Dict[float, List[dict]] = {}
#     for w in words:
#         xm = (w["x0"] + w["x1"]) / 2.0
#         if x0_date <= xm <= x1_date:
#             y = round(w["top"], 1)
#             rows.setdefault(y, []).append(w)

#     anchors = []
#     for _, ws in sorted(rows.items()):
#         ws_sorted = sorted(ws, key=lambda z: z["x0"])
#         joined = " ".join(w["text"] for w in ws_sorted)
#         m = DATE_RX.search(joined)
#         if m:
#             anchors.append({
#                 "top": min(w["top"] for w in ws_sorted),
#                 "text": m.group(0),
#             })
#     return anchors

# def _extract_rows_from_page(page: pdfplumber.page.Page, boxes: Dict[str, Tuple[float, float]]) -> List[list]:
#     words = page.extract_words(x_tolerance=3.0, y_tolerance=2.0, keep_blank_chars=False)
#     if not words:
#         return []

#     x0_date, x1_date = boxes["date"]
#     anchors = _find_date_anchors(words, x0_date, x1_date)
#     if not anchors:
#         return []
#     anchors.sort(key=lambda z: round(z["top"], 1))

#     def first_money_in_span(band_words, span):
#         txt = _join_in_span(band_words, *span)
#         if not txt:
#             return ""
#         m = re.search(MONEY_RX, txt)
#         return _clean_money(m.group(0)) if m else ""

#     rows: List[list] = []
#     for i, a in enumerate(anchors):
#         y_top = a["top"] - 1.0
#         y_bot = (anchors[i + 1]["top"] - 0.5) if i + 1 < len(anchors) else (page.height - 2.0)
#         bw = _band(words, y_top, y_bot)

#         # amounts
#         deposit  = first_money_in_span(bw, boxes["credit"])   # Credit
#         withdraw = first_money_in_span(bw, boxes["debit"])    # Debit
#         balance  = first_money_in_span(bw, boxes["balance"])  # Balance

#         # narration
#         det_txt = _join_in_span(bw, *boxes["details"]) or ""
#         n1, n2 = "", ""
#         if det_txt:
#             m = re.search(r'(?:\bUPI\b|\bIMPS\b|\bNEFT\b|\bRTGS\b|\bACH\b|\bATM\b|\bPOS\b|/CR/|/DR/)', det_txt, flags=re.I)
#             if m:
#                 cut = m.start()
#                 n1 = det_txt[:cut].strip(" -")
#                 n2 = det_txt[cut:].strip()
#             elif len(det_txt) > 64:
#                 n1 = det_txt[:64].rstrip()
#                 n2 = det_txt[64:].lstrip()
#             else:
#                 n1 = det_txt

#         date_txt = _norm_date(a["text"])
#         rows.append([date_txt, n1, n2, withdraw or "", deposit or "", balance or ""])
#     return rows

# # ------------ public API ------------
# def sbi_2(pdf_paths: List[str], passwords: List[str]) -> List[List[list]]:
#     all_tables: List[List[list]] = []
#     for path in pdf_paths or []:
#         pdf = _open_pdf(path, passwords)
#         if not pdf:
#             continue
#         try:
#             first = pdf.pages[0]
#             accno = _find_account_no(first) or ""

#             # Find header boxes once (with fallback to later pages)
#             boxes = _header_boxes(first)
#             if not boxes:
#                 for pg in pdf.pages[1:]:
#                     boxes = _header_boxes(pg)
#                     if boxes:
#                         break

#             # If no boxes at all, still return a visible (empty) header table
#             if not boxes:
#                 all_tables.append([
#                     [BANK_NAME, accno, "", "", "", ""],
#                     ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#                 ])
#                 continue

#             # Extract rows page by page (prefer per-page header if it exists)
#             out_rows: List[list] = []
#             prev_boxes = boxes
#             for pg in pdf.pages:
#                 page_boxes = _header_boxes(pg) or prev_boxes
#                 rows = _extract_rows_from_page(pg, page_boxes)
#                 if rows:
#                     out_rows.extend(rows)
#                     prev_boxes = page_boxes  # carry forward
#             # Always append at least the header (prevents blank sheet)
#             table = [
#                 [BANK_NAME, accno, "", "", "", ""],
#                 ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#             ] + (out_rows or [])
#             all_tables.append(table)

#         finally:
#             pdf.close()
#     return all_tables


# -*- coding: utf-8 -*-
"""
SBI extractor for layout:
  'Date  Details  Ref No./Cheque No  Debit  Credit  Balance'

API (BOB-like):
    from pdf2excel.m_sbi_2 import sbi_2
    tables = sbi_2([r"...\file.pdf"], ["pwd1", "pwd2"])
    -> [
         [
           ["SBI", "37678294053", "", "", "", ""],
           ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
           ["04-04-2024","TRANSFER FROM ...","UPI/CR/40958...", 0.0, 20000.0, 20953.01],
           ...
         ]
       ]
"""

import re
from typing import List, Tuple, Dict, Optional
import pdfplumber
from dateutil.parser import parse as dtparse  # <- function import (no collision)

BANK_NAME = "SBI"

# ------------ regex helpers ------------
DATE_RX   = re.compile(r"\b(0?[1-9]|[12][0-9]|3[01])\s*[-/ ]\s*([A-Za-z]{3,9}|0?[1-9]|1[0-2])\s*[-/ ]\s*(\d{2,4})\b")
# MONEY_RX  = re.compile(r"(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?")
# Prefer amounts with decimal cents; fallback pattern allows integers if a bank prints them
MONEY_RX_DEC = re.compile(r"(?:\d{1,3}(?:[,\s]\d{3})*|\d+)\.\d{2}")
MONEY_RX     = re.compile(r"(?:\d{1,3}(?:[,\s]\d{3})*|\d+)(?:\.\d{2})?")

CRDR_TAIL = re.compile(r"\s*(?:CR|DR)\b\.?$", flags=re.I)

# ------------ utils ------------
def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
    for pwd in (passwords or []) + [None]:
        try:
            return pdfplumber.open(pdf_path, password=pwd)
        except Exception:
            continue
    return None

def _norm_date(txt: str) -> str:
    txt = (txt or "").strip()
    if not txt:
        return ""
    try:
        d = dtparse(txt, dayfirst=True, fuzzy=True)
        return d.strftime("%d-%m-%Y")
    except Exception:
        return ""

# def _clean_money_str(s: Optional[str]) -> str:
#     if not s:
#         return ""
#     s = s.strip()
#     # strip currency and CR/DR markers
#     s = re.sub(r'^(?:Rs\.?|INR)\s*', '', s, flags=re.I)
#     s = CRDR_TAIL.sub("", s)
#     # normalize commas; strip leading dash used as bullet/separator (not sign)
#     s = s.replace(",", "")
#     s = re.sub(r"^(?:-)\s*(?=\d)", "", s)
#     # keep only valid money
#     return s if MONEY_RX.fullmatch(s or "") else ""

def _clean_money_str(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip()
    # strip currency and CR/DR markers
    s = re.sub(r'^(?:Rs\.?|INR)\s*', '', s, flags=re.I)
    s = CRDR_TAIL.sub("", s)
    # remove grouping separators (comma/space) that occur between digits
    s = re.sub(r'(?<=\d)[,\s](?=\d)', '', s)
    # remove any remaining commas
    s = s.replace(",", "")
    # strip leading dash used as bullet/separator (not sign)
    s = re.sub(r"^(?:-)\s*(?=\d)", "", s)
    # keep only valid money (prefer decimal form)
    if MONEY_RX_DEC.fullmatch(s or ""):
        return s
    return s if MONEY_RX.fullmatch(s or "") else ""

def _to_float(s: Optional[str]) -> float:
    s = _clean_money_str(s)
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0

def _find_account_no(page: pdfplumber.page.Page) -> str:
    txt = page.extract_text() or ""
    m = re.search(r"Account\s*Number\s*[:\-]?\s*([0-9Xx*]{6,20})", txt, re.I)
    if m:
        v = m.group(1)
        v = re.sub(r"[^\d]", "", v)
        if len(v) >= 6:
            return v
    # fallback: any long number near top
    head = "\n".join((txt.splitlines() or [])[:40])
    m2 = re.search(r"\b(\d{10,20})\b", head)
    return m2.group(1) if m2 else ""

# ------------ header finder (tolerant across nearby Y positions) ------------
def _header_boxes(page: pdfplumber.page.Page) -> Optional[Dict[str, Tuple[float, float]]]:
    """
    Find column x-spans by clustering header tokens that may sit on slightly different Y rows.
    Requires 'Date', 'Debit', 'Credit', 'Balance'. Creates 'details' span in between if needed.
    """
    words = page.extract_words(x_tolerance=3.0, y_tolerance=2.0, keep_blank_chars=False)
    if not words:
        return None

    def pick_exact(label: str):
        return [w for w in words if w["text"].strip().lower() == label]

    date_ws   = pick_exact("date")
    debit_ws  = pick_exact("debit")
    credit_ws = pick_exact("credit")
    bal_ws    = pick_exact("balance")
    # details can be many forms ("details", "ref", "no", "cheque")
    detail_ws = [w for w in words if re.match(r"(details?|ref|cheque|no\.?)$", w["text"].strip(), re.I)]

    if not (date_ws and debit_ws and credit_ws and bal_ws):
        return None

    def nearest(base_y, cands):
        return min(cands, key=lambda w: abs(round(w["top"], 1) - base_y))

    best = None
    for d in date_ws:
        base_y = round(d["top"], 1)
        db  = nearest(base_y, debit_ws)
        cr  = nearest(base_y, credit_ws)
        ba  = nearest(base_y, bal_ws)
        det = nearest(base_y, detail_ws) if detail_ws else None
        ys  = [round(w["top"], 1) for w in (d, db, cr, ba)] + ([round(det["top"], 1)] if det else [])
        if (max(ys) - min(ys)) > 3.0:
            continue

        centers = {
            "date":   (d["x0"]  + d["x1"])  / 2.0,
            "debit":  (db["x0"] + db["x1"]) / 2.0,
            "credit": (cr["x0"] + cr["x1"]) / 2.0,
            "balance":(ba["x0"] + ba["x1"]) / 2.0,
        }
        centers["details"] = ((det["x0"] + det["x1"]) / 2.0) if det else (centers["balance"] + centers["debit"]) / 2.0

        ordered = sorted(centers.items(), key=lambda kv: kv[1])  # left→right
        spans: Dict[str, Tuple[float, float]] = {}
        for i, (name, xc) in enumerate(ordered):
            left  = ordered[i-1][1] if i > 0 else 0.0
            right = ordered[i+1][1] if i < len(ordered) - 1 else page.width
            margin = 6.0
            x0 = max(0.0, (left + xc) / 2.0 - margin)
            x1 = min(page.width, (xc + right) / 2.0 + margin)
            spans[name] = (x0, x1)

        best = spans
        break

    return best

# ------------ helpers for row extraction ------------
def _band(words, top, bot):
    return [w for w in words if (w["top"] >= top and w["top"] < bot)]

def _join_in_span(band_words, x0, x1) -> str:
    sel = [w for w in band_words if ((w["x0"] + w["x1"]) / 2.0) >= x0 and ((w["x0"] + w["x1"]) / 2.0) <= x1]
    sel = sorted(sel, key=lambda z: (round(z["top"], 1), z["x0"]))
    txt = " ".join(w["text"] for w in sel)
    return re.sub(r"\s+", " ", txt).strip()

# def _money_rightmost(band_words, x0, x1) -> str:
#     """
#     Pick the rightmost money token inside the span.
#     This is more reliable for SBI where the cell can contain multiple numbers.
#     """
#     sel = [w for w in band_words if ((w["x0"] + w["x1"]) / 2.0) >= x0 and ((w["x0"] + w["x1"]) / 2.0) <= x1]
#     if not sel:
#         return ""
#     sel = sorted(sel, key=lambda z: z["x1"])  # rightmost last
#     for w in reversed(sel):
#         m = MONEY_RX.search(w["text"])
#         if m:
#             return _clean_money_str(m.group(0))
#     # fallback: search concatenated text
#     return _clean_money_str(MONEY_RX.findall(_join_in_span(band_words, x0, x1) or "")[-1] if MONEY_RX.findall(_join_in_span(band_words, x0, x1) or "") else "")
def _glue_numeric_fragments_in_text(text: str) -> str:
    """
    Collapse splits inside numbers:
      '20 953 .01' -> '20953.01'
      '3 435.00'   -> '3435.00'
    Works on the whole span text, not per-token.
    """
    s = text or ""
    # remove spaces between digits (e.g., '20 953' -> '20953')
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)
    # remove spaces around decimal point (e.g., '53 .01' -> '53.01')
    s = re.sub(r"\s+(?=\.)", "", s)
    s = re.sub(r"(?<=\.)\s+", "", s)
    return s

# def _money_rightmost(band_words, x0, x1) -> str:
#     """
#     Pick the **rightmost valid money** inside the column span.
#     SBI often has multiple numbers (time, ref, amounts).
#     """
#     sel = [w for w in band_words if (w["x0"] + w["x1"]) / 2.0 >= x0 and (w["x0"] + w["x1"]) / 2.0 <= x1]
#     if not sel:
#         return ""
#     sel = sorted(sel, key=lambda z: z["x1"])  # sort left→right
#     # check from rightmost backward
#     for w in reversed(sel):
#         m = MONEY_RX.search(w["text"].replace(",", ""))
#         if m:
#             return m.group(0)
#     # fallback: whole concatenated span
#     txt = " ".join(w["text"] for w in sel)
#     matches = MONEY_RX.findall(txt.replace(",", ""))
#     return matches[-1] if matches else ""

def _money_rightmost(band_words, x0, x1) -> str:
    """
    Pick the rightmost valid amount inside the span.
    Strategy:
      1) join all text in the span;
      2) glue numeric splits (e.g., '20 953 .01' -> '20953.01');
      3) FIRST search with decimal-required regex to avoid stray integers like '5';
      4) if nothing found, fallback to permissive regex.
    """
    sel = [w for w in band_words if (w["x0"] + w["x1"]) / 2.0 >= x0 and (w["x0"] + w["x1"]) / 2.0 <= x1]
    if not sel:
        return ""

    sel = sorted(sel, key=lambda z: (round(z["top"], 1), z["x0"]))
    raw = " ".join(w["text"] for w in sel)
    raw = raw.replace(",", "")
    raw = _glue_numeric_fragments_in_text(raw)

    # prefer decimal numbers (avoids matching a lone '5')
    matches = MONEY_RX_DEC.findall(raw)
    if not matches:
        matches = MONEY_RX.findall(raw)

    return matches[-1] if matches else ""

def _find_date_anchors(words, x0_date, x1_date):
    rows: Dict[float, List[dict]] = {}
    for w in words:
        xm = (w["x0"] + w["x1"]) / 2.0
        if x0_date <= xm <= x1_date:
            y = round(w["top"], 1)
            rows.setdefault(y, []).append(w)

    anchors = []
    for _, ws in sorted(rows.items()):
        ws_sorted = sorted(ws, key=lambda z: z["x0"])
        joined = " ".join(w["text"] for w in ws_sorted)
        m = DATE_RX.search(joined)
        if m:
            anchors.append({
                "top": min(w["top"] for w in ws_sorted),
                "text": m.group(0),
            })
    return sorted(anchors, key=lambda z: round(z["top"], 1))

def _extract_rows_from_page(page: pdfplumber.page.Page, boxes: Dict[str, Tuple[float, float]]) -> List[list]:
    words = page.extract_words(x_tolerance=3.0, y_tolerance=2.0, keep_blank_chars=False)
    if not words:
        return []

    x0_date, x1_date = boxes["date"]
    anchors = _find_date_anchors(words, x0_date, x1_date)
    if not anchors:
        return []

    rows: List[list] = []
    for i, a in enumerate(anchors):
        y_top = a["top"] - 1.0
        y_bot = (anchors[i + 1]["top"] - 0.5) if i + 1 < len(anchors) else (page.height - 2.0)
        bw = _band(words, y_top, y_bot)

        # amounts (use rightmost money per span)
        withdraw = _to_float(_money_rightmost(bw, *boxes["debit"]))   # Debit
        deposit  = _to_float(_money_rightmost(bw, *boxes["credit"]))  # Credit
        balance  = _to_float(_money_rightmost(bw, *boxes["balance"])) # Balance

        # narration
        det_txt = _join_in_span(bw, *boxes["details"]) or ""
        n1, n2 = "", ""
        if det_txt:
            m = re.search(r'(?:\bUPI\b|\bIMPS\b|\bNEFT\b|\bRTGS\b|\bACH\b|\bATM\b|\bPOS\b|/CR/|/DR/)', det_txt, flags=re.I)
            if m:
                cut = m.start()
                n1 = det_txt[:cut].strip(" -")
                n2 = det_txt[cut:].strip()
            elif len(det_txt) > 64:
                n1 = det_txt[:64].rstrip()
                n2 = det_txt[64:].lstrip()
            else:
                n1 = det_txt

        date_txt = _norm_date(a["text"])
        rows.append([date_txt, n1, n2, withdraw, deposit, balance])

    return rows

# ------------ public API ------------
def sbi_2(pdf_paths: List[str], passwords: List[str]) -> List[List[list]]:
    all_tables: List[List[list]] = []
    for path in pdf_paths or []:
        pdf = _open_pdf(path, passwords)
        if not pdf:
            continue
        try:
            first = pdf.pages[0]
            accno = _find_account_no(first) or ""

            # Find header boxes once (with fallback to later pages)
            boxes = _header_boxes(first)
            if not boxes:
                for pg in pdf.pages[1:]:
                    boxes = _header_boxes(pg)
                    if boxes:
                        break

            # If no boxes at all, still return a visible (empty) header table
            if not boxes:
                all_tables.append([
                    [BANK_NAME, accno, "", "", "", ""],
                    ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
                ])
                continue

            out_rows: List[list] = []
            prev_boxes = boxes
            for pg in pdf.pages:
                page_boxes = _header_boxes(pg) or prev_boxes
                rows = _extract_rows_from_page(pg, page_boxes)
                if rows:
                    out_rows.extend(rows)
                    prev_boxes = page_boxes

            table = [
                [BANK_NAME, accno, "", "", "", ""],
                ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
            ] + (out_rows or [])
            all_tables.append(table)

        finally:
            pdf.close()
    return all_tables
