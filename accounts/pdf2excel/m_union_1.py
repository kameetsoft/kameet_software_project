# accounts/pdf2excel/m_union_1.py
# -*- coding: utf-8 -*-
import re
from typing import List, Any, Optional
import pdfplumber
from dateutil import parser as dtparse
from dateutil.parser import ParserError

BANK_NAME = "UNION BANK"
# DATE_RX = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

DATE_RX = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/(19|20)\d{2}\b"
)
FOOTER_RX = re.compile(
    r'(?:This is system generated statement|NEFT :|RTGS :|Bharat Bill Payment ServiceBBPS|'
    r'https?://www\.unionbankofindia\.co\.in|Registered office:|Request to our customers|'
    r'Scan the QR code|Details of statement|Statement Date|Statement Period|'
    r'S\.No Date Transaction Id)',
    re.I
)

TEXT_ROW_RX = re.compile(
    r'^\s*\d{1,4}\s+(?P<date>(?:0?[1-9]|[12][0-9]|3[01])[/\-](?:0?[1-9]|1[0-2])/(?:19|20)\d{2})\s+'
    r'(?P<txnid>[A-Z0-9]+)\s+'
    r'(?P<remarks>.+?)\s+'
    r'(?P<amt>[\d,]+\.\d{2})\s+\((?P<asign>Cr|Dr)\)\s+'
    r'(?P<bal>[\d,]+\.\d{2})\s+\((?P<bsign>Cr|Dr)\)\s*$',
    re.I
)
def _parse_rows_from_text(page_text: str):
    if not page_text:
        return []
    # strip empties and bank footers
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not FOOTER_RX.search(ln)]

    out = []
    for ln in lines:
        m = TEXT_ROW_RX.search(ln)
        if not m:
            continue

        nd = _norm_date(m.group('date'))
        if not nd:
            continue

        remarks = (m.group('remarks') or '').strip()
        amt_val = _as_float(m.group('amt'))
        bal_val = _as_float(m.group('bal'))

        # sign handling
        deposit  = amt_val if m.group('asign').upper() == 'CR' else 0.0
        withdraw = amt_val if m.group('asign').upper() == 'DR' else 0.0
        if m.group('bsign').upper() == 'DR' and bal_val > 0:
            bal_val = -bal_val

        n1, n2 = remarks[:90], remarks[90:]
        out.append([nd, n1, n2, withdraw, deposit, bal_val])
    return out

# --- small helpers ------------------------------------------------------------
def _open_pdf(pdf_path: str, passwords: List[str]) -> Optional[pdfplumber.PDF]:
    for pwd in (passwords or []) + [None]:
        try:
            return pdfplumber.open(pdf_path, password=pwd)
        except Exception:
            continue
    return None

def _norm_date(s: str) -> str:
    if not s:
        return ""
    try:
        # Union shows dd/mm/yyyy; we output dd-mm-yyyy
        dt = dtparse.parse(s.strip(), dayfirst=True)
        # return dt.strftime("%d-%m-%Y")
        if dt.year < 1990 or dt.year > 2100:
            return ""
        return dt.strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError):
        return ""

def _as_float(x: Any) -> float:
    if x is None:
        return 0.0
    s = str(x)
    # keep sign, remove commas/spaces/non-numeric (except dot and minus)
    s_clean = re.sub(r"[^\d\.\-]", "", s)
    if s_clean in ("", "-", "--", "."):
        return 0.0
    try:
        return float(s_clean)
    except Exception:
        return 0.0

def _collect_tables(page: pdfplumber.page.Page):
    """
    Return only plausible Union Bank tables:
    - Keep tables that have the Union header OR look like body chunks.
    - Allow large tables (the last page may come as a single ~700+ row chunk).
    """
    STRATEGIES = [
        dict(vertical_strategy="lines", horizontal_strategy="lines",
             intersection_tolerance=3, snap_tolerance=3, join_tolerance=3),
        dict(vertical_strategy="lines", horizontal_strategy="lines",
             intersection_tolerance=5, snap_tolerance=4, join_tolerance=4),
        dict(vertical_strategy="text", horizontal_strategy="text",
             snap_tolerance=3),
    ]

    def looks_header_row(row):
        s = " ".join((row or [])).upper()
        return all(k in s for k in ("S.NO", "DATE", "TRANSACTION", "REMARK", "AMOUNT", "BALANCE"))
    def looks_body_chunk(tbl):
        head = tbl[:5]
        date_hits, num_hits = 0, 0
        for r in head:
            r = r or []
            left = " ".join(str(c or "") for c in r[:3])
            if DATE_RX.search(left):
                date_hits += 1
            right = " ".join(str(c or "") for c in r[-3:])
            if re.search(r"\d", right):
                num_hits += 1
        # OLD: return (date_hits >= 2) and (num_hits >= 2)
        return (date_hits >= 1) and (num_hits >= 2)

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

            # Keep wider tables but still bound columns (bad splits create hundreds of cols).
            if n_cols < 4 or n_cols > 30:
                continue

            has_header = any(looks_header_row(r) for r in cleaned[:8])
            if not has_header and not looks_body_chunk(cleaned):
                continue

            # Allow up to 2000 rows so the last-page mega-chunk isn't dropped.
            if n_rows > 5000:
                continue

            sig = (n_rows, n_cols, tuple(len(r) for r in cleaned[:2]))
            if sig in seen_sig:
                continue
            seen_sig.add(sig)

            out.append(cleaned)

    return out

def _looks_union_header(row: List[str]) -> bool:
    s = " ".join((row or []))
    s_up = s.upper()
    # Union’s statement shows these exact column titles (order may vary slightly):
    # "S.No", "Date", "Transaction Id", "Remarks", "Amount(Rs.)", "Balance(Rs.)"
    must = ["S.NO", "DATE", "TRANSACTION", "REMARK", "AMOUNT", "BALANCE"]
    return all(m in s_up for m in must)


def _find_header(tbl: List[List[str]]) -> int:
    for i, r in enumerate(tbl[:8]):
        s = " ".join((r or [])).upper()
        if all(k in s for k in ("S.NO", "DATE", "TRANSACTION", "REMARK", "AMOUNT", "BALANCE")):
            return i
    # fallback: pick the first row that at least has DATE/AMOUNT/BALANCE
    for i, r in enumerate(tbl[:8]):
        s = " ".join((r or [])).upper()
        if "DATE" in s and "AMOUNT" in s and "BALANCE" in s:
            return i
    # if nothing looks like a header, signal invalid to caller
    return -1


def _find_account_number(text: str) -> Optional[str]:
    # Seen as: "Account Number 615802010000458" (or "Account Number : 6158...")
    m = re.search(r"Account\s*Number\s*[:\-]?\s*(\d{8,20})", text, flags=re.I)
    if m:
        return m.group(1)
    return None

# --- main ---------------------------------------------------------------------
# def union_1(pdf_paths: List[str], passwords: List[str]):
#     """
#     Parse Union Bank statements like:
#     S.No | Date | Transaction Id | Remarks | Amount(Rs.) | Balance(Rs.)

#     Output per account:
#     [
#       [ [BANK_NAME, ACCOUNT_NO, "", "", "", ""],
#         ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#         [row...],
#         ...
#       ],
#       ...
#     ]
#     """
#     data_table: List[List[List[Any]]] = []

#     for pdf_path in pdf_paths:
#         pdf = _open_pdf(pdf_path, passwords)
#         if not pdf:
#             continue

#         try:
#             # detect account number from the first page (or any page)
#             account_no = ""
#             try:
#                 for p in pdf.pages[:2]:
#                     t = p.extract_text() or ""
#                     acct = _find_account_number(t)
#                     if acct:
#                         account_no = acct
#                         break
#             except Exception:
#                 pass
#             if not account_no:
#                 account_no = "Unknown-1"

#             rows_out: List[List[Any]] = []
#             seen_global = set()
#             MAX_ROWS_GLOBAL = 5000
#             added_global = 0
            
#             for page in pdf.pages:
#                 # Each page contains repeated “S.No Date Transaction Id …” header and rows
#                 tables = _collect_tables(page)
#                 if not tables:
#                     continue

#                 for tbl in tables:
#                     if not tbl or len(tbl) < 2:
#                         continue

#                     h_idx = _find_header(tbl)
#                     if h_idx < 0:
#                         continue
#                     body = tbl[h_idx + 1 :]
#                     # de-dup + safety cap per table
#                     # seen_rows = set()
#                     # added = 0
#                     # MAX_ROWS = 5000

#                     # Try to map columns by name in header row (robust to minor variations)
#                     header = [c.upper() for c in (tbl[h_idx] if h_idx < len(tbl) else [])]
#                     def _col(name_parts, default=None):
#                         for i, h in enumerate(header):
#                             if all(part in h for part in name_parts):
#                                 return i
#                         return default

#                     c_sno   = _col(["S.NO"], 0)
#                     c_date  = _col(["DATE"], 1)
#                     c_txn   = _col(["TRANSACTION", "ID"], 2)
#                     c_rem   = _col(["REMARK"], 3)
#                     c_amt   = _col(["AMOUNT"], 4)    # “Amount(Rs.)”
#                     c_bal   = _col(["BALANCE"], 5)   # “Balance(Rs.)”
#                     seen_rows = set()   # (date, remarks, amt_raw, bal_raw)
#                     added = 0
#                     MAX_ROWS = 5000

#                     for r in body:
#                         if not r or all(not (x or "").strip() for x in r):
#                             continue
#                         # Some extracted tables might have ragged lengths
#                         def cell(ci):
#                             return r[ci] if (ci is not None and ci < len(r)) else ""
#                         # date_raw = cell(c_date)
#                         # nd = _norm_date(date_raw)

#                         # # Fallback: some first data rows are ragged; scan the whole row for a date
#                         # if not nd:
#                         #     joined = " ".join([str(x or "") for x in r])
#                         #     m = DATE_RX.search(joined)
#                         #     if m:
#                         #         nd = _norm_date(m.group(0))
#                         # if not nd:
#                         #     # still no valid date → skip non-transaction lines
#                         #     continue
#                         date_raw = cell(c_date)
#                         nd = _norm_date(date_raw)

#                         # Fallback for clipped first row under header:
#                         # 1) try neighbors to the right/left (Union tables sometimes shift 1 col)
#                         if not nd and c_date is not None:
#                             for off in (1, -1, 2, -2):
#                                 ci = c_date + off
#                                 if 0 <= ci < len(r):
#                                     nd = _norm_date(r[ci])
#                                     if nd:
#                                         break

#                         # 2) final fallback: scan the whole row for dd/mm/yyyy
#                         # if not nd:
#                         #     joined = " ".join(str(x or "") for x in r)
#                         #     m = DATE_RX.search(joined)
#                         #     if m:
#                         #         nd = _norm_date(m.group(0))
#                         # 2) final fallback: scan only the left part of the row for a date
#                         if not nd:
#                             left_cells = r[: min(len(r), 4)]
#                             joined = " ".join(str(x or "") for x in left_cells)
#                             m = re.search(r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/20\d{2}\b", joined)
#                             if not m:
#                                 m = DATE_RX.search(joined)  # try 19xx as well
#                             if m:
#                                 nd = _norm_date(m.group(0))

#                         if not nd:
#                             # still no valid date → skip non-transaction lines
#                             continue

#                         # Narration MUST be only the remarks (no Transaction Id in narration)
#                         txn_id = cell(c_txn)      # we read but do not use in narration
#                         remarks = cell(c_rem)
#                         full_narr = (remarks or "").strip()

#                         # split narration into N1/N2
#                         n1 = full_narr[:90]
#                         n2 = full_narr[90:]

#                         # date_raw = cell(c_date)
#                         # nd = _norm_date(date_raw)
#                         # if not nd:
#                         #     # skip divider/summary rows
#                         #     continue

#                         # txn_id = cell(c_txn)
#                         # remarks = cell(c_rem)
#                         # # Sometimes UPI/IMPS line spills into TxnId column; merge both into narration
#                         # full_narr = " ".join([x for x in [txn_id, remarks] if x]).strip()

#                         # # split narration into N1/N2
#                         # n1 = full_narr[:90]
#                         # n2 = full_narr[90:]
#                         amt_raw = cell(c_amt)
#                         bal_raw = cell(c_bal)
#                         # Require we have at least date/remarks/amount/balance cells present
#                         if (c_rem is None or c_bal is None or c_amt is None or
#                             c_rem >= len(r) or c_bal >= len(r) or c_amt >= len(r)):
#                             continue

#                         # Balance cell must contain a number; otherwise it's a broken split
#                         if not re.search(r"\d", str(bal_raw)):
#                             continue

#                         # Amount column indicates DR/CR for the transaction
#                         amt_val = _as_float(amt_raw)
#                         is_cr = "(CR" in amt_raw.upper() or " CR)" in amt_raw.upper()
#                         is_dr = "(DR" in amt_raw.upper() or " DR)" in amt_raw.upper()
#                         deposit  = amt_val if is_cr else 0.0
#                         withdraw = amt_val if is_dr else 0.0

#                         # Balance: make (Dr) negative
#                         bal_val = _as_float(bal_raw)
#                         bal_is_dr = "(DR" in bal_raw.upper() or " DR)" in bal_raw.upper()
#                         if bal_is_dr and bal_val > 0:
#                             bal_val = -bal_val

#                         # ---- GUARDS (not inside any if) ----
#                         # Skip subtotal/info rows (no DR/CR and zero amounts)
#                         # if (deposit == 0.0 and withdraw == 0.0) and not re.search(r"\b(CR|DR)\b", str(amt_raw), re.I):
#                         #     continue

#                         # # De-dup across multi-pass extraction
#                         # row_sig = (nd, (remarks or ""), str(amt_raw), str(bal_raw))
#                         # if row_sig in seen_rows:
#                         #     continue
#                         # seen_rows.add(row_sig)

#                         # # Append ONCE
#                         # rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])
#                         # added += 1
#                         # if added >= MAX_ROWS:
#                         #     break
#                         # Skip subtotal/info rows (no DR/CR and zero amounts)
#                         if (deposit == 0.0 and withdraw == 0.0) and not re.search(r"\b(CR|DR)\b", str(amt_raw), re.I):
#                             continue

#                         # De-dup across strategies/tables/pages: normalize spaces and amounts
#                         norm_remarks = re.sub(r"\s+", " ", (remarks or "")).strip()
#                         row_sig = (nd, norm_remarks, f"{withdraw:.2f}", f"{deposit:.2f}", f"{bal_val:.2f}")
#                         if row_sig in seen_global:
#                             continue
#                         seen_global.add(row_sig)

#                         rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])
#                         added_global += 1
#                         if added_global >= MAX_ROWS_GLOBAL:
#                             break

#                         # amt_raw = cell(c_amt)
#                         # bal_raw = cell(c_bal)

#                         # # Amount column indicates DR/CR for the *transaction*:
#                         # # e.g., "3000.00 (Cr)" -> deposit, "80.00 (Dr)" -> withdrawal
#                         # amt_val = _as_float(amt_raw)
#                         # is_cr = "(CR" in amt_raw.upper() or " CR)" in amt_raw.upper()
#                         # is_dr = "(DR" in amt_raw.upper() or " DR)" in amt_raw.upper()
#                         # deposit = amt_val if is_cr else 0.0
#                         # withdraw = amt_val if is_dr else 0.0

#                         # # Balance shows (Cr)/(Dr). Make Dr negative balance for consistency.
#                         # bal_val = _as_float(bal_raw)
#                         # bal_is_dr = "(DR" in bal_raw.upper() or " DR)" in bal_raw.upper()
#                         # if bal_is_dr and bal_val > 0:
#                         #     bal_val = -bal_val
#                         #     # Skip subtotal/info rows (no DR/CR and zero amounts)
#                         #     if (deposit == 0.0 and withdraw == 0.0) and not re.search(r"\b(CR|DR)\b", str(amt_raw), re.I):
#                         #         continue

#                         #     # De-dup identical lines that might appear from multiple passes
#                         #     row_sig = (nd, (remarks or ""), str(amt_raw), str(bal_raw))
#                         #     if row_sig in seen_rows:
#                         #         continue
#                         #     seen_rows.add(row_sig)

#                         #     rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])
#                             # added += 1
#                             # if added >= MAX_ROWS:
#                             #     break

#                         # rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])

#             if rows_out:
#                 account_row = [BANK_NAME, account_no, "", "", "", ""]
#                 headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
#                 data_table.append([account_row, headers] + rows_out)

#         finally:
#             try:
#                 pdf.close()
#             except Exception:
#                 pass

#     return data_table


def union_1(pdf_paths: List[str], passwords: List[str]):
    """
    Parse Union Bank statements like:
    S.No | Date | Transaction Id | Remarks | Amount(Rs.) | Balance(Rs.)

    Returns your standard list-of-tables format.
    """
    data_table: List[List[List[Any]]] = []

    for pdf_path in pdf_paths:
        pdf = _open_pdf(pdf_path, passwords)
        if not pdf:
            continue

        try:
            # --- detect account number from the first page(s) ---
            account_no = ""
            try:
                for p in pdf.pages[:2]:
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
            seen_global = set()
            MAX_ROWS_GLOBAL = 5000
            added_global = 0
            prev_bal = None 
            # remember last known column mapping across chunks/pages
            last_cols: Optional[tuple] = None  # (c_date, c_txn, c_rem, c_amt, c_bal)

            for page in pdf.pages:
                page_added_before = added_global
                tables = _collect_tables(page)
                if not tables:
                    continue

                for tbl in tables:
                    if not tbl or len(tbl) < 1:
                        continue

                    # ---- find header in this chunk; if none, reuse previous mapping ----
                    h_idx = _find_header(tbl)
                    if h_idx >= 0:
                        header = [c.upper() for c in (tbl[h_idx] if h_idx < len(tbl) else [])]

                        def _col(name_parts, default=None):
                            for i, h in enumerate(header):
                                if all(part in h for part in name_parts):
                                    return i
                            return default

                        c_date = _col(["DATE"], 1)
                        c_txn  = _col(["TRANSACTION", "ID"], 2)
                        c_rem  = _col(["REMARK"], 3)
                        c_amt  = _col(["AMOUNT"], 4)
                        c_bal  = _col(["BALANCE"], 5)

                        last_cols = (c_date, c_txn, c_rem, c_amt, c_bal)
                        body = tbl[h_idx + 1 :]
                    else:
                        if not last_cols:
                            continue  # no header seen yet; skip this fragment
                        c_date, c_txn, c_rem, c_amt, c_bal = last_cols
                        body = tbl  # entire chunk is body rows

                    # ---- parse body rows ----
                    for r in body:
                        if not r or all(not (x or "").strip() for x in r):
                            continue

                        def cell(ci):
                            return r[ci] if (ci is not None and 0 <= ci < len(r)) else ""

                        # Date
                        date_raw = cell(c_date)
                        nd = _norm_date(date_raw)

                        # neighbor fallback (tables sometimes shift by a column)
                        if not nd and c_date is not None:
                            for off in (1, -1, 2, -2):
                                ci = c_date + off
                                if 0 <= ci < len(r):
                                    nd = _norm_date(r[ci])
                                    if nd:
                                        break

                        m=None
                        # # final fallback: scan only the left part of the row
                        # final fallback: try left part first...
                        if not nd:
                            left_cells = r[: min(len(r), 4)]
                            joined_left = " ".join(str(x or "") for x in left_cells)
                            m = re.search(r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/20\d{2}\b", joined_left)
                            if not m:
                                m = DATE_RX.search(joined_left)  # allow 19xx

                        # ...and if still no date, scan the ENTIRE row (last-page mis-splits)
                        if not nd and not m:
                            joined_all = " ".join(str(x or "") for x in r)
                            m = re.search(r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/20\d{2}\b", joined_all)
                            if not m:
                                m = DATE_RX.search(joined_all)

                        if m and not nd:
                            nd = _norm_date(m.group(0))

                        if not nd:
                            continue  # not a transaction row

                        # if not nd:
                        #     left_cells = r[: min(len(r), 4)]
                        #     joined = " ".join(str(x or "") for x in left_cells)
                        #     m = re.search(r"\b(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[0-2])/20\d{2}\b", joined)
                        #     if not m:
                        #         m = DATE_RX.search(joined)  # allow 19xx
                        #     if m:
                        #         nd = _norm_date(m.group(0))
                        # if not nd:
                        #     continue  # not a transaction row

                        # Require we have at least remarks/amount/balance indices & a numeric balance
                        if (c_rem is None or c_amt is None or c_bal is None or
                            c_rem >= len(r) or c_amt >= len(r) or c_bal >= len(r)):
                            continue
                        amt_raw = cell(c_amt)
                        bal_raw = cell(c_bal)
                        if not re.search(r"\d", str(bal_raw)):
                            continue  # ragged/broken split

                        # Narration (remarks only; do NOT include txn id)
                        remarks = cell(c_rem)
                        txnid_raw = cell(c_txn)
                        txnid_norm = re.sub(r"\s+", "", txnid_raw or "")

                        full_narr = (remarks or "").strip()
                        n1, n2 = full_narr[:90], full_narr[90:]

                        # Amount -> withdraw/deposit via (Dr)/(Cr)
                        # Balance (make Dr negative)
                        bal_val = _as_float(bal_raw)
                        u_bal = bal_raw.upper()
                        if ("(DR" in u_bal or " DR)" in u_bal) and bal_val > 0:
                            bal_val = -bal_val

                        # Ignore opening/closing balance summary rows
                        if re.search(r"\b(OPENING|CLOSING)\s+BALANCE\b", str(remarks), re.I):
                            prev_bal = bal_val
                            continue

                        # Amount -> withdraw/deposit
                        amt_val = _as_float(amt_raw)
                        u_amt = (amt_raw or "").upper()
                        deposit, withdraw = 0.0, 0.0

                        if "CR" in u_amt:
                            deposit = amt_val
                        elif "DR" in u_amt:
                            withdraw = amt_val
                        elif amt_val > 0 and prev_bal is not None:
                            # Fallback: infer sign from balance delta when "(Cr)/(Dr)" is missing
                            delta = round(bal_val - prev_bal, 2)
                            if abs(delta - amt_val) <= 0.05:
                                deposit = amt_val
                            elif abs(delta + amt_val) <= 0.05:
                                withdraw = amt_val
                            else:
                                # As a last resort, don't drop the row; keep amount but leave deposit/withdraw 0
                                pass

                        # Do NOT skip just because CR/DR text is missing; only drop fully empty/garbage rows
                        if amt_val == 0.0 and not re.search(r"\d", str(amt_raw)):
                            prev_bal = bal_val
                            continue

                        # amt_val = _as_float(amt_raw)
                        # u_amt = amt_raw.upper()
                        # is_cr = "(CR" in u_amt or " CR)" in u_amt
                        # is_dr = "(DR" in u_amt or " DR)" in u_amt
                        # deposit  = amt_val if is_cr else 0.0
                        # withdraw = amt_val if is_dr else 0.0

                        # # Balance (make Dr negative)
                        # bal_val = _as_float(bal_raw)
                        # u_bal = bal_raw.upper()
                        # if ("(DR" in u_bal or " DR)" in u_bal) and bal_val > 0:
                        #     bal_val = -bal_val

                        # # skip info/subtotal lines
                        # if (deposit == 0.0 and withdraw == 0.0) and not re.search(r"\b(CR|DR)\b", str(amt_raw), re.I):
                        #     continue

                        # de-dup across strategies/chunks/pages
                        norm_remarks = re.sub(r"\s+", " ", full_narr).strip()
                        # row_sig = (nd, norm_remarks, f"{withdraw:.2f}", f"{deposit:.2f}", f"{bal_val:.2f}")
                        row_sig = (nd, norm_remarks, f"{withdraw:.2f}", f"{deposit:.2f}", f"{bal_val:.2f}", txnid_norm)

                        if row_sig in seen_global:
                            continue
                        seen_global.add(row_sig)

                        rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])
                        prev_bal = bal_val
                        added_global += 1
                        if added_global >= MAX_ROWS_GLOBAL:
                            break

                    if added_global >= MAX_ROWS_GLOBAL:
                        break
                # if added_global >= MAX_ROWS_GLOBAL:
                #     break
                # ---- TEXT FALLBACK (when no table rows were added for this page) ----
                if added_global == page_added_before:
                    txt = page.extract_text() or ""
                    extra = _parse_rows_from_text(txt)
                    for nd, n1, n2, withdraw, deposit, bal_val in extra:
                        norm_remarks = re.sub(r"\s+", " ", (n1 + " " + n2)).strip()
                        row_sig = (nd, norm_remarks, f"{withdraw:.2f}", f"{deposit:.2f}", f"{bal_val:.2f}")
                        if row_sig in seen_global:
                            continue
                        rows_out.append([nd, n1, n2, withdraw, deposit, bal_val])
                        seen_global.add(row_sig)
                        prev_bal = bal_val
                        added_global += 1
                        if added_global >= MAX_ROWS_GLOBAL:
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
