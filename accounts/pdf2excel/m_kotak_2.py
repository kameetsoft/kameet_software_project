# -*- coding: utf-8 -*-
"""
Kotak Mahindra Bank – NEW FORMAT (NO TABLE LINES)
DATE | TRANSACTION DETAILS | CHEQUE/REFERENCE# | DEBIT | CREDIT | BALANCE
"""

import re
import pdfplumber
from typing import List

BANK_NAME = "KOTAK"

DATE_RX = re.compile(r"\d{2}\s+[A-Za-z]{3},?\s+\d{4}")
# AMT_RX  = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
AMT_RX = re.compile(r"[-+]?\d[\d,]*\.\d{2}")  # works with/without commas and +/-

ACCOUNT_RX = re.compile(r"Account\s*#?\s*(\d{6,20})", re.I)

# Column X ranges (based on your PDF)
COLS = [
    (20, 110),    # DATE
    (110, 430),   # TRANSACTION DETAILS
    (430, 560),   # CHEQUE / REF
    (560, 650),   # DEBIT
    (650, 740),   # CREDIT
    (740, 860),   # BALANCE
]

# def _clean_amt(s):
#     if not s:
#         return 0.0
#     m = AMT_RX.search(s.replace(",", ""))
#     return float(m.group(0).replace(",", "")) if m else 0.0



def _clean_amt(s: str) -> float:
    if not s:
        return 0.0
    t = s.replace("\u200b", " ").replace("\xa0", " ").strip()
    m = AMT_RX.search(t)
    if not m:
        return 0.0
    return float(m.group(0).replace(",", ""))


def _pick_cols_from_header(page):
    """
    Find header x positions and build column boundaries dynamically.
    Works for Kotak NEW format: DATE | TRANSACTION DETAILS | CHEQUE/REFERENCE# | DEBIT | CREDIT | BALANCE
    """
    defaults = [
        (0, 0.16),   # DATE
        (0.16, 0.52),# DETAILS
        (0.52, 0.67),# REF
        (0.67, 0.77),# DEBIT
        (0.77, 0.87),# CREDIT
        (0.87, 1.00) # BALANCE
    ]

    try:
        words = page.extract_words(use_text_flow=True)
    except Exception:
        words = []

    if not words:
        w = page.width
        return [(a*w, b*w) for a, b in defaults]

    # collect header candidates (top area only)
    top_words = [w for w in words if w["top"] < 160]  # header region
    if not top_words:
        w = page.width
        return [(a*w, b*w) for a, b in defaults]

    def find_x(label):
        lab = label.upper()
        xs = []
        for w in top_words:
            t = (w.get("text") or "").upper()
            if lab in t:
                xs.append(w["x0"])
        return min(xs) if xs else None

    x_date = find_x("DATE")
    x_det  = find_x("TRANSACTION") or find_x("DETAILS")
    x_ref  = find_x("CHEQUE") or find_x("REFERENCE")
    x_deb  = find_x("DEBIT")
    x_cr   = find_x("CREDIT")
    x_bal  = find_x("BALANCE")

    xs = [x for x in [x_date, x_det, x_ref, x_deb, x_cr, x_bal] if x is not None]
    if len(xs) < 4:
        w = page.width
        return [(a*w, b*w) for a, b in defaults]

    xs = sorted(set(xs))
    w = page.width

    # build boundaries between header starts; last ends at page width
    bounds = []
    for i in range(len(xs)):
        x0 = xs[i]
        x1 = xs[i+1] if i+1 < len(xs) else w
        bounds.append((x0 - 5, x1 - 5))

    # ensure exactly 6 columns (pad/truncate)
    if len(bounds) >= 6:
        return bounds[:6]
    while len(bounds) < 6:
        bounds.append((bounds[-1][1], bounds[-1][1] + (w*0.1)))
    return bounds[:6]


def kotak_2(pdf_paths: List[str], passwords: List[str]):
    tables = []

    for pdf_path in pdf_paths:
        for pw in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=pw) as pdf:

                    # ---------------- ACCOUNT NO ----------------
                    account_no = ""
                    for p in pdf.pages[:2]:
                        txt = p.extract_text() or ""
                        m = ACCOUNT_RX.search(txt)
                        if m:
                            account_no = m.group(1)
                            break

                    table = [
                        [BANK_NAME, account_no, "", "", "", ""],
                        ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"]
                    ]

                    for page in pdf.pages:
                        words = page.extract_words(use_text_flow=True)
                        if not words:
                            continue

                        # group by Y (row)
                        rows = {}
                        for w in words:
                            y = round(w["top"] / 4) * 4
                            rows.setdefault(y, []).append(w)


                        col_bounds = _pick_cols_from_header(page)

                        for y in sorted(rows):
                            cols = [""] * 6
                            for w in rows[y]:
                                xc = (w["x0"] + w["x1"]) / 2
                                # for i, (x0, x1) in enumerate(COLS):
                                for i, (x0, x1) in enumerate(col_bounds):
                                    if x0 <= xc <= x1:
                                        cols[i] += " " + w["text"]
                                        break

                            cols = [c.strip() for c in cols]
                            mdate = DATE_RX.search(cols[0] or "")
                            if not mdate:
                                continue

                            date = mdate.group(0).strip()

                            # if extra text is stuck in date column, move it into narration
                            tail = (cols[0].replace(date, "")).strip()
                            narr = (tail + " " + (cols[1] or "")).strip()
                            ref  = (cols[2] or "").strip()
                            # 🔧 FIX: Sometimes debit amount spills into REF column
                            spill_amt = _clean_amt(ref)
                            if spill_amt and not cols[3]:
                                cols[3] = ref        # move amount to DEBIT column
                                ref = ""             # clear narration2

                            # if not cols[0] or not DATE_RX.search(cols[0]):
                            #     continue

                            # date = cols[0]
                            # narr = cols[1]
                            # ref  = cols[2]
                            # debit  = _clean_amt(cols[3])
                            # credit = _clean_amt(cols[4])
                            # bal    = _clean_amt(cols[5])
                            # ---------- SMART AMOUNT DETECTION ----------
                            # amounts = []

                            # for c in cols[3:]:
                            #     m = AMT_RX.search(c.replace(",", ""))
                            #     if m:
                            #         amounts.append(float(m.group(0).replace(",", "")))

                            # debit = 0.0
                            # credit = 0.0
                            # balance = 0.0

                            # if len(amounts) >= 1:
                            #     balance = amounts[-1]   # rightmost is ALWAYS balance

                            # if len(amounts) == 2:
                            #     # opening balance OR pure credit
                            #     credit = amounts[0]

                            # elif len(amounts) == 3:
                            #     # debit OR credit + balance
                            #     if "DEBIT" in narr.upper() or "-" in cols[3]:
                            #         debit = amounts[0]
                            #     else:
                            #         credit = amounts[0]

                            # debit   = _clean_amt(cols[3])
                            # credit  = _clean_amt(cols[4])
                            # balance = _clean_amt(cols[5])

                            # raw_debit  = _clean_amt(cols[3])
                            # raw_credit = _clean_amt(cols[4])
                            # balance    = abs(_clean_amt(cols[5]))

                            # # Kotak rule:
                            # # Debit = money out → withdrawals (positive)
                            # # Credit = money in → deposits (positive)

                            # debit = abs(raw_debit) if raw_debit < 0 else abs(raw_debit)
                            # credit = abs(raw_credit)
                            raw_debit  = _clean_amt(cols[3])
                            raw_credit = _clean_amt(cols[4])
                            balance    = abs(_clean_amt(cols[5]))

                            withdrawal = 0.0
                            deposit    = 0.0

                            row_text = f"{narr} {ref}".upper()

                            # --- KOTAK INTELLIGENT RULES ---

                            # 1️⃣ Opening balance is always CREDIT
                            if "OPENING BALANCE" in row_text:
                                deposit = balance

                            # 2️⃣ Explicit debit keywords OR minus sign
                            elif "-" in cols[3] or "DEBIT" in row_text:
                                withdrawal = abs(raw_debit or raw_credit)

                            # 3️⃣ Credit keywords (NEFT / IMPS / RTGS / CREDIT)
                            elif any(k in row_text for k in ["NEFT", "IMPS", "RTGS", "CREDIT"]):
                                deposit = abs(raw_debit or raw_credit)

                            # 4️⃣ Fallback: column-based
                            elif raw_credit:
                                deposit = abs(raw_credit)

                            elif raw_debit:
                                withdrawal = abs(raw_debit)


                            table.append([
                                date,
                                narr,
                                ref,
                                withdrawal,
                                deposit,
                                balance
                            ])

                    if len(table) > 2:
                        tables.append(table)
                break
            except Exception:
                continue

    return tables
