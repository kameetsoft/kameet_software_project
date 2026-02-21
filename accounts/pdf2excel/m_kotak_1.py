# -*- coding: utf-8 -*-
"""
Kotak extractor for layout:
  'Date  Narration  Chq/Ref No  Withdrawal(Dr)/Deposit(Cr)  Balance'

API (BOB-like):
    from pdf2excel.m_kotak_1 import kotak_1
    tables = kotak_1([r"...\file.pdf"], ["pwd1", "pwd2"])
    -> [
         [
           ["KOTAK", "<account_no>", "", "", "", ""],
           ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
           ["03-06-2023","UPI/GARAGEPRENEURS ...","UPI-315460631661", 22953.35, 0.0, 3337.00],
           ...
         ]
       ]
"""

import re
from typing import List, Tuple, Dict, Optional
import pdfplumber
from dateutil.parser import parse as dtparse
from dateutil.parser import ParserError

BANK_NAME = "KOTAK"

# ------------ regex helpers ------------
DATE_RX = re.compile(
    r"\b([0-3]?\d)[-/\s](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|"
    r"0?[1-9]|1[0-2])[-/\s](20\d{2})\b",
    re.I
)

ACCOUNT_RX = re.compile(r"Account\s*No\.?\s*([0-9]{6,20})", re.I)
AMT_RX = re.compile(r"[-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?")
DR_RX = re.compile(r"\(?\s*Dr\s*\)?", re.I)
CR_RX = re.compile(r"\(?\s*Cr\s*\)?", re.I)

HEADER_HINTS = [
    re.compile(r"^\s*Date\s+Narration\s+.*(Withdrawal|Deposit).*(Balance)\s*(Chq/Ref\s*No)?", re.I),
    re.compile(r"^\s*Date\s+Narration\s+Chq/Ref\s*No", re.I),
]

SKIP_LINE_RX = re.compile(
    r"(Cust\.Reln\.No|Currency|Branch|Nominee|Period|GUJARAT|SURAT|Interest\s*Pd|Int\.Pd|This\s+statement|Page\s+\d+\s+of|www\.)",
    re.I
)

# def _looks_like_date(s: str) -> bool:
#     if not s:
#         return False
#     if DATE_RX.search(s):
#         return True
#     # last fallback: strict parse with dayfirst
#     try:
#         _ = dtparse(s, dayfirst=True, fuzzy=False)
#         return True
#     except Exception:
#         return False

# Replace the whole function
def _looks_like_date(s: str) -> bool:
    """Accept only dd-mm-YYYY / dd/mm/YYYY / dd MON YYYY (YYYY must be 20xx)."""
    if not s:
        return False
    m = DATE_RX.search(s.strip())
    return bool(m)  # <- only our regex, no fuzzy parse


# def _parse_date(s: str) -> str:
#     s = s.strip().replace("\u200b", " ").replace("\xa0", " ")
#     # normalize to dd-mm-YYYY
#     try:
#         dt = dtparse(s, dayfirst=True, fuzzy=True)
#         return dt.strftime("%d-%m-%Y")
#     except Exception:
#         # if it contains pieces like 03-06-2023 but with spaces in between
#         m = DATE_RX.search(s)
#         if m:
#             try:
#                 dt = dtparse(m.group(0), dayfirst=True, fuzzy=True)
#                 return dt.strftime("%d-%m-%Y")
#             except Exception:
#                 return s
#         return s

def _parse_date(s: str) -> str:
    t = s.strip().replace("\u200b"," ").replace("\xa0"," ")
    m = DATE_RX.search(t)
    if not m:
        # last attempt after hard normalization
        t2 = t.replace(" ", "")
        m = DATE_RX.search(t2)
        if not m:
            return s.strip()
    try:
        dt = dtparse(m.group(0), dayfirst=True, fuzzy=False)
        # accept only 2000–2099
        if 2000 <= dt.year <= 2099:
            return dt.strftime("%d-%m-%Y")
    except Exception:
        pass
    return s.strip()



def _clean_amt(raw: str) -> float:
    if not raw:
        return 0.0
    t = raw.upper().replace("\u200b", " ").replace("\xa0", " ")
    sign = -1.0 if DR_RX.search(t) else 1.0
    m = AMT_RX.search(t)
    if not m:
        return 0.0
    num = m.group(0).replace(",", "")
    try:
        return float(num) * sign
    except Exception:
        return 0.0

def _clean_balance(raw: str) -> float:
    # Kotak prints balance with (Cr) most of the time; treat as positive
    if not raw:
        return 0.0
    m = AMT_RX.search(raw)
    if not m:
        return 0.0
    try:
        return float(m.group(0).replace(",", ""))
    except Exception:
        return 0.0

def _pick_cols_from_page(page) -> List[Tuple[float, float]]:
    """
    Return column boundaries [(x0,x1), ...] for:
      0: Date
      1: Narration
      2: Chq/Ref No
      3: Amount (Dr/Cr)
      4: Balance
    If not detected, use robust defaults that match common Kotak layout.
    """
    # Defaults work well for most Kotak A4 statements exported from net banking
    defaults = [
        (20, 110),    # Date
        (110, 500),   # Narration
        (500, 600),   # Chq/Ref
        (600, 700),   # Amount
        (700, 820),   # Balance
    ]

    try:
        lines = (page.extract_text() or "").splitlines()
    except Exception:
        return defaults

    header_line = None
    for ln in lines[:40]:  # just scan top of page
        for rx in HEADER_HINTS:
            if rx.search(ln):
                header_line = ln
                break
        if header_line:
            break

    if not header_line:
        return defaults

    # If we have words we can approximate from their centers
    try:
        words = page.extract_words(use_text_flow=True)
    except Exception:
        return defaults

    # naive heuristic: find representative tokens by name
    def _find_word_xcenter(token: str) -> Optional[float]:
        token_upper = token.upper()
        best = None
        for w in words:
            wt = w.get("text", "").upper()
            if token_upper in wt:
                xc = (w["x0"] + w["x1"]) / 2
                best = xc if (best is None or xc < best) else best
        return best

    date_x  = _find_word_xcenter("Date")
    narr_x  = _find_word_xcenter("Narration")
    chq_x   = _find_word_xcenter("Chq")
    amount_x= _find_word_xcenter("Deposit") or _find_word_xcenter("Withdrawal") or _find_word_xcenter("Amount")
    bal_x   = _find_word_xcenter("Balance")

    # Build edges from found centers; fall back if missing
    xs = []
    for xc in [date_x, narr_x, chq_x, amount_x, bal_x]:
        if xc is not None:
            xs.append(xc)
    if len(xs) < 3:
        return defaults

    xs = sorted(xs)
    # widen to bands
    bands = []
    prev = 10.0
    for xc in xs:
        bands.append((prev, xc + 40))
        prev = xc + 40
    bands.append((prev, 9999.0))

    # Ensure exactly 5 columns
    if len(bands) >= 5:
        return bands[:5]
    # pad if shorter
    while len(bands) < 5:
        bands.append((bands[-1][1], bands[-1][1] + 120))
    return bands[:5]

def _bin_rows(words, y_bin: float) -> Tuple[List[float], Dict[float, List[dict]]]:
    y_keys: List[float] = []
    buckets: Dict[float, List[dict]] = {}
    for w in words:
        y = round(w["top"] / y_bin) * y_bin
        if y not in buckets:
            buckets[y] = []
            y_keys.append(y)
        buckets[y].append(w)
    return y_keys, buckets

def kotak_1(pdf_paths: List[str], passwords: List[str]):
    tables: List[List[List]] = []  # list of tables per account
    seen_accounts: Dict[str, int] = {}  # account -> tables index

    for pdf_path in pdf_paths:
        account_number_found = ""
        # try passwords in order (+ None)
        for pw in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=pw) as pdf:
                    if not pdf.pages:
                        continue

                    # best-effort account number (scan few pages)
                    for p in pdf.pages[:3]:
                        txt = p.extract_text() or ""
                        m = ACCOUNT_RX.search(txt)
                        if m:
                            account_number_found = m.group(1)
                            break

                    # set up table for this account
                    if account_number_found not in seen_accounts:
                        table = [
                            [BANK_NAME, account_number_found or "", "", "", "", ""],
                            ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
                        ]
                        seen_accounts[account_number_found] = len(tables)
                        tables.append(table)

                    table_idx = seen_accounts[account_number_found]
                    table = tables[table_idx]

                    # process pages
                    for page in pdf.pages:
                        # Skip pages with no words
                        try:
                            words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
                        except Exception:
                            continue
                        if not words:
                            continue

                        # rough filter to skip address/header lines
                        page_text_head = (page.extract_text() or "").splitlines()[:30]
                        if any(SKIP_LINE_RX.search(ln or "") for ln in page_text_head):
                            pass  # we’ll still parse; filters are row-level

                        col_bounds = _pick_cols_from_page(page)
                        y_bin = 4.0  # works well on Kotak PDFs

                        y_keys, buckets = _bin_rows(words, y_bin)
                        y_keys.sort()

                        # Assemble provisional rows
                        provisional = []
                        for y in y_keys:
                            row_words = buckets[y]
                            # skip obvious headers/footers
                            raw_line = " ".join([w["text"] for w in row_words])
                            if SKIP_LINE_RX.search(raw_line):
                                continue

                            cols = [""] * 5
                            for w in sorted(row_words, key=lambda z: z["x0"]):
                                xc = (w["x0"] + w["x1"]) / 2.0
                                for i, (x0, x1) in enumerate(col_bounds):
                                    if x0 <= xc <= x1:
                                        cols[i] = (cols[i] + " " + w["text"]).strip()
                                        break
                            if any(c.strip() for c in cols):
                                provisional.append(cols)

                        # Stitch multi-line entries: if Date empty, append to previous
                        # stitched = []
                        # for cols in provisional:
                        #     date_s, narr_s, ref_s, amt_s, bal_s = [c.strip() for c in cols]
                        #     if not any([date_s, narr_s, ref_s, amt_s, bal_s]):
                        #         continue
                        #     if not _looks_like_date(date_s) and stitched:
                        #         # continuation of previous line
                        #         prev = stitched[-1]
                        #         # append narration/ref to previous
                        #         if narr_s:
                        #             prev[1] = (prev[1] + " " + narr_s).strip()
                        #         if ref_s:
                        #             prev[2] = (prev[2] + " " + ref_s).strip()
                        #         # if amount/balance spilled lines, keep last non-empty
                        #         if amt_s:
                        #             prev[3] = (prev[3] + " " + amt_s).strip()
                        #         if bal_s:
                        #             prev[4] = (prev[4] + " " + bal_s).strip()
                        #     else:
                        #         stitched.append([date_s, narr_s, ref_s, amt_s, bal_s])

                        # --- STITCH: treat missing date as continuation; also treat "date but empty payload" as continuation ---
                        stitched = []
                        for cols in provisional:
                            date_s, narr_s, ref_s, amt_s, bal_s = [c.strip() for c in cols]

                            # skip fully empty rows
                            if not any([date_s, narr_s, ref_s, amt_s, bal_s]):
                                continue

                            is_date = _looks_like_date(date_s)
                            row_has_payload = any([narr_s, ref_s, amt_s, bal_s])

                            if (not is_date) and stitched:
                                # continuation of previous line
                                prev = stitched[-1]
                                if narr_s:
                                    prev[1] = (prev[1] + " " + narr_s).strip()
                                if ref_s:
                                    prev[2] = (prev[2] + " " + ref_s).strip()
                                # if amount/balance spilled onto this line, keep last non-empty token
                                if amt_s:
                                    prev[3] = (prev[3] + " " + amt_s).strip()
                                if bal_s:
                                    prev[4] = (prev[4] + " " + bal_s).strip()
                                continue

                            if is_date and (not row_has_payload) and stitched:
                                # looks like a date, but no narration/ref/amount/balance -> likely a spill;
                                # treat as continuation (do not start a new row)
                                continue

                            # start a fresh row
                            stitched.append([date_s, narr_s, ref_s, amt_s, bal_s])


                        # Convert to target schema rows
                        for row in stitched:
                            date_s, narr_s, ref_s, amt_s, bal_s = row
                            if not _looks_like_date(date_s):
                                continue
                            date_fmt = _parse_date(date_s)

                            # classify amt into withdrawal/deposit
                            amt_val = _clean_amt(amt_s)
                            withdrawal = abs(amt_val) if amt_val < 0 else 0.0
                            deposit   = amt_val if amt_val > 0 else 0.0

                            balance = _clean_balance(bal_s)

                            # NARRATION 1 / 2: keep ref in narration 2
                            narr1 = (narr_s or "").strip()
                            narr2 = (ref_s or "").strip()

                            # --- NEW: drop empty/noise rows ---
                            if not narr1 and not narr2 and withdrawal == 0.0 and deposit == 0.0 and balance == 0.0:
                                continue

                            table.append([
                                date_fmt,         # DATE
                                narr1,            # NARRATION 1
                                narr2,            # NARRATION 2 (Chq/Ref No)
                                withdrawal,       # WITHDRAWAL
                                deposit,          # DEPOSIT
                                balance,          # CL BALANCE
                            ])
                break  # opened successfully with this password
            except Exception:
                # try next password
                continue

    return tables


# quick manual test (optional)
if __name__ == "__main__":
    pdfs = [r"E:\path\to\KOTAK.pdf"]
    pws = ["pwd1", "pwd2"]
    out = kotak_1(pdfs, pws)
    from tabulate import tabulate
    for t in out:
        print(tabulate(t[:20], tablefmt="grid"))
