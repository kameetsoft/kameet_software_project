# pdf2excel/m_canara_1.py
import pdfplumber
import re
from dateutil import parser
from dateutil.parser import ParserError
import pandas as pd

bank_name = "CANARA"

# ---------------- Helper functions ----------------

DATE_ANCHOR_RX = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
AMT_ONLY_RX = re.compile(r"\d[\d,]*\.?\d*")
DR_RX = re.compile(r"\bDR\b", re.I)
CR_RX = re.compile(r"\bCR\b", re.I)
CHEQUE_LINE_RX = re.compile(r"^Chq", re.I)

def _to_number(txt):
    try:
        return float(str(txt).replace(",", "").strip())
    except Exception:
        return None

def _parse_date(txt):
    try:
        return parser.parse(txt, dayfirst=True).strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError):
        return ""

# ---------------- Main Canara extractor ----------------

def _canara_rows_from_text(page, last_bal_in):
    """
    Simplified text parser for Canara Bank.
    """
    txt = page.extract_text(x_tolerance=1.5, y_tolerance=3.0) or ""
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]

    out = []
    last_bal = last_bal_in
    started = False
    head = []
    i = 0

    while i < len(lines):
        ln = lines[i].strip()
        UL = ln.upper()

        if not started:
            if UL.startswith("DATE PARTICULARS"):
                started = True
            elif UL.startswith("OPENING BALANCE"):
                toks = list(AMT_ONLY_RX.finditer(ln))
                bal = _to_number(toks[-1].group(0)) if toks else None
                if bal is not None:
                    last_bal = bal
            i += 1
            continue

        if UL.startswith(("DATE PARTICULARS", "PAGE ")):
            i += 1
            continue

        m = DATE_ANCHOR_RX.search(ln)
        if m:
            amount_tokens = list(AMT_ONLY_RX.finditer(ln[m.end():]))
            if not amount_tokens:
                head.append(ln)
                i += 1
                continue

            date = _parse_date(m.group(0))
            debit = credit = 0.0
            bal = None

            if len(amount_tokens) >= 2:
                amt = _to_number(amount_tokens[-2].group(0)) or 0.0
                bal = _to_number(amount_tokens[-1].group(0))
                chunk_text = (" ".join(head + [ln])) if head else ln
                has_dr = bool(DR_RX.search(chunk_text))
                has_cr = bool(CR_RX.search(chunk_text))
                if has_cr and not has_dr:
                    debit, credit = 0.0, abs(amt)
                elif has_dr and not has_cr:
                    debit, credit = abs(amt), 0.0
                elif bal is not None and last_bal is not None:
                    delta = round(bal - last_bal, 2)
                    debit, credit = (0.0, abs(amt)) if delta > 0 else (abs(amt), 0.0)
                else:
                    debit, credit = abs(amt), 0.0
            else:
                bal = _to_number(amount_tokens[-1].group(0))

            j = i + 1
            tail = []
            while j < len(lines):
                nxt = lines[j].strip()
                UU = nxt.upper()

                if UU.startswith(("PAGE ", "DATE PARTICULARS")):
                    break
                if CHEQUE_LINE_RX.match(nxt):
                    tail.append(nxt)
                    j += 1
                    break
                mm = DATE_ANCHOR_RX.search(nxt)
                if mm and list(AMT_ONLY_RX.finditer(nxt[mm.end():])):
                    break
                if nxt:
                    tail.append(nxt)
                j += 1

            nar = " ".join(head + tail).strip()
            nar = re.sub(r"(?:\bDR\b|\bCR\b)\s*$", "", nar, flags=re.I).strip()
            nar = re.sub(r"\bopening\s+bal(?:ance)?\b[^0-9]*\d[\d,]*(?:\.\d+)?", "", nar, flags=re.I)
            nar = re.sub(r"\s{2,}", " ", nar).strip()
            n1 = nar
            n2 = ""

            out.append([
                date,
                n1,
                n2,
                float(debit or 0.0),
                float(credit or 0.0),
                "" if bal is None else float(bal),
            ])
            if bal is not None:
                last_bal = bal

            head = []
            i = j
            continue

        head.append(ln)
        i += 1

    return out, last_bal

# ---------------- Public entry ----------------

def canara_1(pdf_paths, passwords):
    """
    Entry point like other bank modules. Returns tables in standard format:
    [
      [ [BANK_NAME, account_no], headers, rows... ]
    ]
    """
    data_table = []
    for pdf_path in pdf_paths:
        rows = []
        last_bal = None

        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    for page in pdf.pages:
                        page_rows, last_bal = _canara_rows_from_text(page, last_bal)
                        if page_rows:
                            rows.extend(page_rows)
                break
            except Exception:
                continue

        if not rows:
            continue

        # Canara: no reliable account number in text → fallback Unknown
        account_number = "Unknown"
        account_row = [bank_name, account_number, "", "", "", ""]
        headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

        data_table.append([account_row, headers] + rows)

    return data_table

# Debug run
if __name__ == "__main__":
    pdf_files = [r"E:\Python\PDF\CANARA\sample.pdf"]
    pdf_passwords = ["password1", "password2"]
    final_data = canara_1(pdf_files, pdf_passwords)
    from tabulate import tabulate
    for table in final_data:
        print(tabulate(table, tablefmt="grid"))


