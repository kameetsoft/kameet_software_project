# pdf2excel/m_kalupur_1.py
# -*- coding: utf-8 -*-
"""
Kalupur Bank extractor module (BOB-like API)

Usage:
    from pdf2excel.m_kalupur_1 import kalupur_1
    tables = kalupur_1([r"C:\path\to\Kalupur.pdf"], ["pass1","pass2"])

Return shape:
    [
      [
        ["KALUPUR", "<ACCOUNT_NO>", "", "", "", ""],
        ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
        ["29-06-2022","QUARTERLY SMS CHRG","", 15.00, 0.00, 57194.18],
        ...
      ]
    ]
"""

import re
from typing import List
import pdfplumber
from dateutil.parser import parse, ParserError


BANK_NAME = "KALUPUR"

# Column x-boundaries tuned for the statement that has header:
# "Date  Value Date  TR-Mode- Instr.No  Particulars  Debit Amt.  Credit Amt.  Balance"
# (works on sample “Kalupur 0703.pdf”)
COLUMN_BOUNDS = [
    (25, 80),     # Date
    (80, 140),    # Value Date
    (140, 180),   # TR-Mode / Instr.No (kept but not used in final row)
    (180, 372),   # Particulars (we map this to NARRATION 1)
    (372, 437),   # Debit Amt.
    (437, 538),   # Credit Amt.
    (538, 1000),  # Balance
]


def _is_date(s: str) -> bool:
    if not s or len(re.findall(r"\d", str(s))) < 3:
        return False
    try:
        parse(s, dayfirst=True, fuzzy=False)
        return True
    except Exception:
        return False


def _clean_amount(s: str) -> float:
    if not s or s.strip() == "-" or s.strip() == "":
        return 0.0
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def _get_account_number(page_text: str) -> str:
    # The sample shows:
    # "Account Number Drawing Power\n04420100703 0.00"
    m = re.search(r"Account Number.*?\n(\d+)", page_text)
    if m:
        return m.group(1)
    # fallback (looser)
    m2 = re.search(r"\bAccount\s*Number\b.*?(\d{6,20})", page_text, re.IGNORECASE | re.DOTALL)
    return m2.group(1) if m2 else "UNKNOWN"


def kalupur_1(pdf_paths: List[str], passwords: List[str]):
    data_table = []

    for pdf_path in pdf_paths:
        account_number = "UNKNOWN"
        all_rows = []  # rows as sliced by COLUMN_BOUNDS across all pages

        # try passwords + None at end
        for pw in list(passwords) + [None]:
            try:
                with pdfplumber.open(pdf_path, password=pw) as pdf:
                    if not pdf.pages:
                        return [{"error": "PDF file is empty"}]

                    # account number from first page text
                    first_text = pdf.pages[0].extract_text() or ""
                    account_number = _get_account_number(first_text)

                    # extract words page-by-page and bucket into rows by Y (like your BOB code)
                    for page in pdf.pages:
                        words = page.extract_words() or []
                        # ignore header area (up to just below the header line)
                        # header line y≈291 in the sample; 320 is a safe cutoff
                        usable = [w for w in words if w["top"] >= 320]

                        # bucket by approximate y (to group words in same text line)
                        y_step = 1  # tight bucketing; this file's y is stable
                        y_positions = []
                        rows = []
                        for w in usable:
                            y = round(w["top"] / y_step) * y_step
                            if y not in y_positions:
                                y_positions.append(y)
                                rows.append([])
                            idx = y_positions.index(y)
                            rows[idx].append([w["text"], w["x0"], w["x1"]])

                        # project every row into our columns via center-x
                        for row in rows:
                            cells = [""] * len(COLUMN_BOUNDS)
                            for text, x0, x1 in row:
                                xc = (x0 + x1) / 2.0
                                for i, (xs, xe) in enumerate(COLUMN_BOUNDS):
                                    if xs <= xc <= xe:
                                        cells[i] = (cells[i] + " " + text).strip() if cells[i] else text
                                        break
                            if any(cells):
                                all_rows.append(cells)
                # if we got here without exception, break password loop
                break
            except Exception:
                # try next password
                continue

        # build final table rows (keep only lines with a valid Date)
        table_rows = []
        for r in all_rows:
            # r = [date, value_date, tr_mode, particulars, debit, credit, balance]
            if _is_date(r[0]):
                date_str = r[0].strip()
                particulars = (r[3] or "").strip()
                dr = (r[4] or "").strip()
                cr = (r[5] or "").strip()
                bal = (r[6] or "").strip()

                # DATE format
                try:
                    d = parse(date_str, dayfirst=True, fuzzy=True)
                    date_str = d.strftime("%d-%m-%Y")
                except Exception:
                    pass

                # numbers
                dr_val = _clean_amount(dr)
                cr_val = _clean_amount(cr)
                bal_val = _clean_amount(bal)

                table_rows.append([date_str, particulars, "", dr_val, cr_val, bal_val])

        # table skeleton
        account_row = [BANK_NAME, account_number, "", "", "", ""]
        headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

        data_table.append([account_row, headers] + table_rows)

    return data_table


# Debug run
if __name__ == "__main__":
    pdf_files = [r"E:\PDFs\Kalupur\Kalupur_0703.pdf"]
    pdf_passwords = ["", "wrong"]
    out = kalupur_1(pdf_files, pdf_passwords)
    # pretty print (optional)
    from tabulate import tabulate
    for table in out:
        print(tabulate(table, tablefmt="grid"))
