# m_canara.py
import re
import pdfplumber
import pandas as pd
from dateutil.parser import parse as dtparse

DATE_RX = re.compile(r"\b(\d{1,2}[-/](?:\d{1,2}|[A-Za-z]{3})[-/]\d{2,4})\b")
NUM_RX  = re.compile(r"(?<!\w)(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?!\w)")

def _to_float(s):
    if s is None: return None
    s = str(s).strip().replace(",", "")
    if not s: return None
    try: return float(s)
    except: return None

def _fmt_date(s):
    try:
        d = dtparse(s, dayfirst=True, fuzzy=True)
        return d.strftime("%d/%m/%Y")
    except:
        return ""

def _is_credit_text(txt: str) -> bool:
    t = txt.upper()
    return (
        "UPI/CR" in t
        or "CASH DEPOSIT" in t
        or t.startswith("BY CLG")
        or "SBINT" in t or "INTEREST" in t
        or ("DEPOSIT" in t and "CASH" in t)
    )

def _is_debit_text(txt: str) -> bool:
    t = txt.upper()
    return (
        "UPI/DR" in t
        or "SMS CHARGES" in t
        or "CHQ PAID" in t or "MICR INWARD" in t
        or "ANNUAL CHARGES" in t
        or "DEBIT CARD" in t
        or "CHARGES" in t
        or "WITHDRAW" in t
    )

# def parse_canara_pdf(pdf_path: str, password: str | None = None) -> pd.DataFrame:
#     """
#     Parse a Canara e-passbook into columns:
#     DATE | NARRATION 1 | NARRATION 2 | WITHDRAWAL | DEPOSIT | CL. BALANCE
#     """
#     rows = []
#     opening_balance = None

#     with pdfplumber.open(pdf_path, password=password) as pdf:
#         all_lines = []
#         for pg in pdf.pages:
#             txt = pg.extract_text(x_tolerance=1.5, y_tolerance=3.0) or ""
#             for ln in txt.splitlines():
#                 s = ln.strip()
#                 if s:
#                     all_lines.append(s)

#     for ln in all_lines:
#         if "Opening Balance" in ln:
#             m = NUM_RX.findall(ln)
#             if m:
#                 opening_balance = _to_float(m[-1])
#                 break

#     last_balance = opening_balance
#     i, n = 0, len(all_lines)

#     while i < n:
#         line = all_lines[i]
#         md = DATE_RX.search(line)
#         if not md:
#             i += 1
#             continue

#         date = _fmt_date(md.group(1))
#         i += 1

#         # collect narration lines until a line ends with "<amount> <balance>"
#         narr_lines, amt, bal = [], None, None
#         while i < n:
#             cur = all_lines[i]
#             if DATE_RX.search(cur):
#                 break
#             nums = NUM_RX.findall(cur)
#             if len(nums) >= 2:
#                 amt = _to_float(nums[-2])
#                 bal = _to_float(nums[-1])
#                 pre = cur[:cur.rfind(nums[-2])].strip()
#                 if pre:
#                     narr_lines.append(pre)
#                 i += 1
#                 break
#             else:
#                 narr_lines.append(cur)
#                 i += 1

#         narr = re.sub(r"\s+", " ", " ".join(narr_lines)).strip()

#         # classify
#         wd = dep = 0.0
#         if _is_credit_text(narr):
#             dep = float(amt or 0.0)
#         elif _is_debit_text(narr):
#             wd = float(amt or 0.0)
#         else:
#             if bal is not None and last_balance is not None and amt is not None:
#                 if bal > last_balance: dep = float(amt)
#                 elif bal < last_balance: wd = float(amt)
#                 else: wd = float(amt or 0.0)
#             else:
#                 # first txn and we didn't capture opening balance → prefer deposit (empirical for Canara)
#                 dep = float(amt or 0.0)

#         # split narration to two cols (mostly keep in NARRATION 1)
#         n1, n2 = narr, ""
#         if len(narr) > 180:
#             cut = narr.rfind(" ", 0, len(narr)//2)
#             if cut == -1: cut = len(narr)//2
#             n1, n2 = narr[:cut].strip(), narr[cut:].strip()

#         rows.append([date, n1, n2, wd, dep, "" if bal is None else float(bal)])
#         if bal is not None: last_balance = bal

#     df = pd.DataFrame(rows, columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])
#     if not df.empty:
#         try:
#             df["__d"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
#             df = df.sort_values("__d").drop(columns="__d")
#         except:
#             pass
#     return df
def parse_canara_pdf(pdf_path: str, password: str | None = None) -> pd.DataFrame:
    """
    Parse a Canara e-passbook into:
    DATE | NARRATION 1 | NARRATION 2 | WITHDRAWAL | DEPOSIT | CL. BALANCE
    Works even when amount and balance are on separate lines.
    """
    rows = []
    opening_balance = None

    with pdfplumber.open(pdf_path, password=password) as pdf:
        all_lines = []
        for pg in pdf.pages:
            # slightly larger tolerances to keep nearby text together
            txt = pg.extract_text(x_tolerance=2.0, y_tolerance=4.0) or ""
            for ln in txt.splitlines():
                s = (ln or "").strip()
                if s:
                    all_lines.append(s)

    # Opening balance (if present)
    for ln in all_lines:
        if "Opening Balance" in ln:
            m = NUM_RX.findall(ln)
            if m:
                opening_balance = _to_float(m[-1])
                break

    last_balance = opening_balance
    i, n = 0, len(all_lines)

    while i < n:
        line = all_lines[i]
        md = DATE_RX.search(line)
        if not md:
            i += 1
            continue

        date = _fmt_date(md.group(1))
        i += 1

        # --- collect narration + numbers across multiple lines until next date
        narr_bits: list[str] = []
        num_buf: list[str] = []        # collect ALL numeric tokens; we will use the last two
        amt = bal = None

        while i < n:
            cur = all_lines[i]

            # Stop at the next dated row (start of next txn)
            if DATE_RX.search(cur):
                break

            # Gather numeric tokens from this line (could be none / one / many)
            toks = NUM_RX.findall(cur)

            # Append any text BEFORE the first number on the line (so we don't pull the numeric-only lines)
            if toks:
                # text before first number
                pre = cur.split(toks[0], 1)[0].strip()
                # keep only if it has alpha chars (avoid adding blank or numeric-only fragments)
                if re.search(r"[A-Za-z]", pre):
                    narr_bits.append(pre)
                num_buf.extend(toks)
            else:
                # whole line is narration (no numbers)
                narr_bits.append(cur)

            i += 1

        # Need at least two numbers across the whole block => <amount, balance>
        if len(num_buf) >= 2:
            amt = _to_float(num_buf[-2])
            bal = _to_float(num_buf[-1])

        # build narration
        narr = " ".join(narr_bits)
        # remove embedded times like 13:28:18 or 11:00:22 etc.
        narr = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", narr)
        narr = re.sub(r"\s+", " ", narr).strip(" -/")

        # --- classify deposit vs withdrawal ---
        wd = dep = 0.0
        if _is_credit_text(narr):
            dep = float(amt or 0.0)
        elif _is_debit_text(narr):
            wd = float(amt or 0.0)
        else:
            if bal is not None and last_balance is not None and amt is not None:
                if bal > last_balance:
                    dep = float(amt)
                elif bal < last_balance:
                    wd = float(amt)
                else:
                    # no change → rarely happens; lean to withdrawal
                    wd = float(amt or 0.0)
            else:
                # very first txn without captured opening balance: favor deposit for Canara layouts
                dep = float(amt or 0.0)

        # split narration into two cols (keep most in NARRATION 1)
        n1, n2 = narr, ""
        if len(narr) > 180:
            cut = narr.rfind(" ", 0, len(narr)//2)
            if cut == -1: cut = len(narr)//2
            n1, n2 = narr[:cut].strip(), narr[cut:].strip()

        rows.append([date, n1, n2, wd, dep, "" if bal is None else float(bal)])
        if bal is not None:
            last_balance = bal

    # finalize frame
    df = pd.DataFrame(rows, columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])
    if not df.empty:
        try:
            df["__d"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
            df = df.sort_values("__d").drop(columns="__d")
        except:
            pass
    return df

def detect_canara(pdf_path: str, password: str | None = None) -> tuple[bool, str | None]:
    """
    Returns (is_canara, account_number_or_None).
    """
    acct = None
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            txt = (pdf.pages[0].extract_text() or "").upper()
            if ("CANARA" in txt and "DEPOSITS" in txt and "WITHDRAWALS" in txt) or "E-PASSBOOK" in txt:
                # try to pull account no., if present
                raw = pdf.pages[0].extract_text() or ""
                m = re.search(r"(?:A/c|A/C|Account(?:\s*No\.?| Number))\s*[:\-]?\s*([0-9Xx\*]{6,})", raw, re.I)
                if m: acct = m.group(1)
                return True, acct
    except Exception:
        pass
    return False, None

def try_canara_rows(pdf_path: str, passwords: list[str] | None) -> list[list] | None:
    """
    If the PDF is Canara, returns list-of-lists ready for Excel:
      [ ['CANARA BANK', <acct>, '', '', '', ''],
        ['DATE','NARRATION 1','NARRATION 2','WITHDRAWAL','DEPOSIT','CL. BALANCE'],
        ...data rows...
      ]
    Otherwise returns None.
    """
    for pwd in (passwords or []) + [None]:
        ok, acct = detect_canara(pdf_path, pwd)
        if not ok:
            continue
        df = parse_canara_pdf(pdf_path, password=pwd)
        account_row = ["CANARA BANK", acct or "", "", "", "", ""]
        headers     = ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"]
        return [account_row, headers] + df.fillna("").values.tolist()
    return None
def canara_1(pdf_path: str, passwords: list[str] | None):
    """
    Entry point expected by bank_modules["canara_1"].
    Returns list-of-lists:
      [ ['CANARA BANK', <acct>, '', '', '', ''],
        ['DATE','NARRATION 1','NARRATION 2','WITHDRAWAL','DEPOSIT','CL. BALANCE'],
        ...data rows...
      ]
    """
    # Try full Canara detection path (handles passwords)
    rows = try_canara_rows(pdf_path, passwords)
    if rows is not None:
        return rows

    # Fallback: parse directly with available passwords (in case detect_canara() missed)
    headers = ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"]
    for pwd in (passwords or []) + [None]:
        try:
            df = parse_canara_pdf(pdf_path, password=pwd)
            # We didn’t get acct via detect_canara; leave blank rather than failing
            account_row = ["CANARA BANK", "", "", "", "", ""]
            return [account_row, headers] + df.fillna("").values.tolist()
        except Exception:
            continue

    # Last-resort empty shape to keep the pipeline from crashing
    return [["CANARA BANK", "", "", "", "", ""], headers]
