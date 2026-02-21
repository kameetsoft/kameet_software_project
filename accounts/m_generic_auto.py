# m_generic_auto.py
# pip install pdfplumber dateparser python-dateutil pandas
# (Optional OCR fallback) pip install pdf2image pytesseract  && install Tesseract + poppler

import re
import io
import pdfplumber
from dateutil.parser import parse as dtparse, ParserError
from datetime import datetime
import pandas as pd

BANK_UNKNOWN = "BANK"

ALIASES = {
    "date": [
        r"\bdate\b",
        r"\btxn\s*date\b",
        r"\btransaction\s*date\b",
        r"\bvalue\s*date\b",
    ],
    "desc": [
        r"\bnarration\b",
        r"\bdescription\b",
        r"\bparticulars\b",
        r"\bdetails?\b",
        r"\bremark[s]?\b",
    ],
    "ref": [
        r"\bref(\.|erence)?\b",
        r"\bchq(\.|ue)?\s*no\b",
        r"\bcheque\s*no\b",
        r"\bupi\s*id\b",
        r"\butr\b",
    ],
    "debit": [
        r"\bdebit\b",
        r"\bdr\b",
        r"\bwdl?\b",
        r"\bwithdraw[a-z]*\b",
        r"\bpaid\b",
        r"\bwithdrawal\s*amt\.?\b",
        r"\bwithdrawal\s*amount\b",
        r"\bdr\.?\s*amount\b",
        r"\bdebit\s*amount\b",
    ],
    "credit": [
        r"\bcredit\b",
        r"\bcr\b",
        r"\bdeposit[s]?\b",
        r"\brecd?\b",
        r"\breceived\b",
        r"\bdeposit\s*amt\.?\b",
        r"\bdeposit\s*amount\b",
        r"\bcr\.?\s*amount\b",
        r"\bcredit\s*amount\b",
    ],
    "balance": [
        r"\bbalance\b",
        r"\bclosing\b",
        r"\bcl\.?\s*bal(?:ance)?\b",
        r"\brunning\s*bal(?:ance)?\b",
    ],
    "amount": [
        r"\bamount\b",
        r"\bamt\b",
        r"\bvalue\b",
    ],
    "drcr": [
        r"\bdr/?cr\b",
        r"\bcr/?dr\b",
        r"\btype\b",
        r"\btran\s*type\b",
    ],
}


# allow optional serial number before the date
LINE_START_DATE = re.compile(
    r"^\s*(?:\d{1,4}\s+)?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
)
# TXN_HEAD_RX = re.compile(r"^(?:ACH|UPI|IMPS|NEFT|RTGS|ATM|POS|MIN\s*BAL|GST|CHQ|CHEQUE)\b", re.I)

AMT_TOKEN = re.compile(
    r"(?P<num>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+\.\d+)\s*(?P<tag>Dr|Cr)?",
    re.I
)
REFISH_TAIL_RX = re.compile(r"^[\d\s/.-]{8,}$")
TXN_HEAD_RX = re.compile(r"^(?:ACH|UPI|IMPS|NEFT|RTGS|ATM|POS|MIN\s*BAL|GST|CHQ|CHEQUE)\b", re.I)
OPENING_BAL_RX = re.compile(r"^\s*opening\s+balance\b", re.I)
CLOSING_BAL_RX = re.compile(r"^\s*closing\s+balance\b", re.I)

# --- BOM header/summary junk to ignore completely ---
BOM_NOISE_RX = re.compile(r"""
    (?:^|\s)Nomination\s+Flag\b
  | \bStatement\s+for\s+Account\b
  | \bChannel\b
  | \bOpening\s+Balance\b.*\d
  | \bTotal\s+Transaction\s+Count\b
  | \bTotal\s+Debit\s+Amount\b
  | \bTotal\s+Credit\s+Amount\b
  | \bfrom\s+\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\s+to\s+\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b
  | \bto\s+\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\s+Total\s+Transaction\s+Count\b
""", re.I | re.X)

DATE_RX = re.compile(r"""
 (?:\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4})   # 10-Jan-2024
|(?:\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})       # 10/01/2024
|(?:\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})         # 2024-01-10
""", re.IGNORECASE | re.VERBOSE)
HEAD_DATE_SHARD_RX = re.compile(r"^\s*\d{1,2}[/.-]\d{1,2}\b")

NUM_RX = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
DR_RX  = re.compile(r"\bDR\b", re.I)
CR_RX  = re.compile(r"\bCR\b", re.I)
# --- add near the other regex/constants at the top (reuse your imports) ---
HEADER_DROP_RX = re.compile(
    r"""^(
        page\s+\d+(\s*of\s*\d+)?       |   # Page 1 of 3 / Page 2
        statement\s+of\s+account       |
        account\s+statement            |
        customer\s*id                  |
        branch\s*:                     |
        ifs(c|c\s*code)?               |
        ifsc\s*code                    |
        micr\s*code                    |
        address\s*:                    |
        contact\s*:                    |
        phone\s*:                      |
        a/?c\s*(no\.?|number)\s*:      |
        period\s*:                     |
        from\s+[0-9a-z/.\-]+\s+to\s+[0-9a-z/.\-]+
    )\b""",
    re.I | re.X,
)
# Make header detection tolerant to "Dr Amount" / "Cr Amount"
ALIASES["debit"]  += [r"\bdr\.?\s*amount\b", r"\bdebit\s*amount\b"]
ALIASES["credit"] += [r"\bcr\.?\s*amount\b", r"\bcredit\s*amount\b"]

OPENING_BAL_RX = re.compile(r"\bopening\s+bal(ance)?\b", re.I)
CLOSING_BAL_RX = re.compile(r"\bclosing\s+bal(ance)?\b", re.I)
CHEQUE_LINE_RX = re.compile(r"^\s*(?:Chq|Cheque)\s*[:\-]?\s*\S+", re.I)

TITLE_PREFIX_RX = re.compile(r"(?i)^account\s+statement\s+for\b")

# --- at top with the other regexes ---
DATE_ANCHOR_RX = re.compile(r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
AMT_ONLY_RX = re.compile(
    r"(?<!\w)(?:\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+\.\d+)(?!\w)"
)


FOOTER_DROP_RX = re.compile(
    r"""(?xi)
    ^\s*Page\s+No\b|                    # "Page No - 12"
    ^\s*Page\s+\d+(?:\s*of\s*\d+)?\s*$| # "Page 1" / "Page 1 of 3"
    ^\s*Unless\s+constituent\s+notifies|
    ^\*?COMPUTER\s+GENERATED|
    ^\*\s*PLEASE\s+ENSURE|
    ^\*\s*CUSTOMERS\s+ARE\s+REQUESTED|
    ^\*\s*Pls\s+note\s+Penal\s+interest|
    ^\s*Abbreviations\s+are\s+as\s+under
    """
)
PAGE_TITLE_RX = re.compile(r"(?i)^\s*account\s+statement(?:\s+for)?\b[:\-\s]*")

DESC_NOISE_RX = re.compile(r"""(?xi)
    immediately\s+of\s+any\s+discrepancy.*|
    entries\s+shown\s+in\s+the\s+statement\s+of\s+account.*|
    the\s+bank\s+official\.?\s*please\s+do\s+not\s+accept\s+statement.*|
    without\s+making\s+them.*|
    average\s+balance.*|
    avoid\s+levy\s+of\s+charges.*
""")

# FOR HDFC BANK
TXN_HEAD_RX = re.compile(r"""
    \b(?:ACH|NEFT|IMPS|UPI|RTGS|CHQ(?:\s*DEP)?|CHEQUE|TPT|ATM|POS|CARD|INTEREST|CHARGES?)\b
""", re.I | re.X)

# Make balance detection catch "Closing Balance" exactly too
ALIASES["balance"] += [r"\bclosing\s*balance\b", r"\bclo?sing\s*bal\.?\b"]
# HDFC page header/footer noise and summary markers
HDFC_HEADER_NOISE_RX = re.compile(
    r"(?:Phone\s*no\.?|OD\s*Limit|Email\s*:|Cust\s*ID|Account\s*No\s*:|"
    r"Preferred\s+Customer|A/C\s+Open\s+Date|RTGS/NEFT\s+IFSC|Branch\s+Code|"
    r"Product\s+Code|Registered\s+Office\s+Address|State\s+account\s+branch\s+GSTN)",
    re.I,
)

HDFC_SUMMARY_START_RX = re.compile(r"^\s*STATEMENT\s+SUMMARY\b", re.I)
HDFC_SUMMARY_INLINE_RX = re.compile(r"\bOpening\s+Balance\b|\bClosing\s+Bal", re.I)
# strict Indian-number grabber (e.g., 1,406,070.02)
NUM_INR_RX = re.compile(r'[-+]?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?')

def _num_from_text(x):
    s = str(x or "").replace("\u00a0", " ").strip()
    m = NUM_INR_RX.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except Exception:
        return None
    
# PNB Bank
# --- header/intro lines that sometimes sit inside the Description x-range
DESC_HEADER_LINE_RX = re.compile(r"""(?xi)
    ^\s*(account\s+statement|statement\s+period|customer\s+details|branch\s+name|
         description\s+branch\s+name|txn\.?\s*no\.?|kims\s*remarks|cheque\s*no\.?)\b
""")

#PNB Bank
# --- multi-word footers/disclaimers; match complete joined lines
FOOTER_DROP_LINE_RX = re.compile(r"""(?xi)
    ^\s*page\s+no\b|
    ^\s*page\s+\d+(?:\s*of\s*\d+)?\s*$|
    ^\s*unless\s+constituent\s+notifies\b|
    ^\*?computer\s+generated\b|
    ^\*\s*please\s+ensure\b|
    ^\*\s*customers\s+are\s+requested\b|
    ^\*\s*pls\s+note\s+penal\s+interest\b|
    ^\s*abbreviations\s+are\s+as\s+under\b
""")

# --- add near your other regexes ---
# Transaction-Id leak at the very start of Remarks (e.g., "S3482272 UPI/...")
TXNID_LEAK_RX = re.compile(
    r"^\s*(?:S\d{6,9}|[A-Z]\d{5,12}|\d{7,12})(?=\s*(?:/|UPI|IMPS|NEFT|RTGS|ACH|ATM|POS))",
    re.I
)

# NEXT_TXN_TOKEN_RX = re.compile(r"\b(?:NEFT|IMPS|RTGS|ACH|POS|ATM|BIL|SMS\s+CHRG|CASH\s+HAND|UPI/DR|UPI/)\b", re.I)
NEXT_TXN_TOKEN_RX = re.compile(
    r"""(?xi)
    (?:\bNEFT(?:[_-](?:IN|OUT))?:?      # NEFT_IN, NEFT-OUT, NEFT:
     |\bNEFT[_-][A-Z0-9]+               # NEFT-XXXX forms
     |\bIMPS\b|\bRTGS\b|\bACH\b|\bPOS\b|\bATM\b
     |\bBIL\b|\bSMS\s+CHRG\b|\bCASH\s+HAND\b
     |\bUPI/|\bUPI_|\bUPI\b             # UPI tokens
     |/PAY\b|/Pay\b
     |\bYESBN[A-Z0-9]*\b|\bYESB[A-Z0-9]*\b
    )
    """
)


# special starts we treat specially
SPECIAL_START_RX = re.compile(
    r"^(?:UPI/DR\b|UPI/CR\b|TO\s+SELF\b|BY\s+SELF\b|BY\s+CASH\b)",
    re.I
)

FOOTER_CUT = re.compile(r"""(?xi)
    https?://\S+ |
    request\s+to\s+our\s+customers.*$ |
    registered\s+office.*$ |
    NEFT\s*:.*$ | RTGS\s*:.*$ | UPI\s*:.*$ |
    this\s+is\s+system\s+generated.*$
""")

# --- FUZZY footer/legend detector for Union (handles OCR doubled letters etc.) ---
def _norm_letters(s: str) -> str:
    """
    Lowercase, keep only letters/spaces, collapse runs like 'ss' -> 's',
    and strip extra spaces. Designed to catch OCR-doubled letters in footer text.
    """
    import re as _re
    t = "".join(ch for ch in (s or "").lower() if ch.isalpha() or ch.isspace())
    t = _re.sub(r"(.)\1{1,}", r"\1", t)     # collapse runs of same char
    t = _re.sub(r"\s+", " ", t).strip()
    return t

# phrases that commonly appear in Union footers/legends/logos
_UNION_FOOTER_KEYS = {
    "this is system generated statement",
    "registered office",
    "details of statement",
    "request to our customers",
    "for any discrepancy",
    "bharat bill payment service",
    "unified payment interface",   # UPI
    "vyom",                        # Union Vyom app/logo
    "page no", "page of", "page",
}

def _looks_footerish(s: str) -> bool:
    t = _norm_letters(s)
    if not t:
        return False
    for key in _UNION_FOOTER_KEYS:
        if key in t:
            return True
    return False

def _split_special_narration(s: str) -> tuple[str, str]:
    t = (s or "").strip()
    if not t or not SPECIAL_START_RX.match(t):
        return t, ""

    # TO SELF / BY CASH: keep head, DROP tail
    m = re.match(r"^(?P<head>(?:TO\s+SELF|BY\s+CASH)\b(?:\s*[-–—]?\s*\d{3,})?)\s*(?P<tail>.*)$", t, re.I)
    if m:
        return m.group("head").strip(), ""   # <-- drop tail

    # UPI/DR or UPI/CR followed by a new txn token: keep head, DROP tail
    m2 = NEXT_TXN_TOKEN_RX.search(t)
    if m2 and m2.start() > 0:
        return t[:m2.start()].strip(), ""    # <-- drop tail

    return t, ""

# for punjab
def _truncate_special_narration(s: str) -> str:
    """
    If narration starts with UPI/DR, TO SELF, or BY CASH, keep only that logical
    chunk and drop anything that looks like the start of the next transaction's
    narration that may have bled in (e.g., NEFT_IN:..., UPI/..., ATM..., etc.)
    Also keeps optional cheque number after TO SELF / BY CASH.
    """
    t = s.strip()
    if not t or not SPECIAL_START_RX.match(t):
        return t

    # Case 1: TO SELF / BY CASH -> keep 'TO SELF'/'BY CASH' and optional '- 304659' etc.
    m = re.match(r"^(?P<head>(?:TO\s+SELF|BY\s+CASH)\b(?:\s*[-–—]?\s*\d{3,})?)", t, re.I)
    if m:
        return m.group("head").strip()

    # Case 2: UPI/DR ... -> cut before any token that looks like start of a *new* narration
    # (NEFT/..., IMPS, ATM, another UPI/, etc.)
    m2 = NEXT_TXN_TOKEN_RX.search(t, pos=0)
    if m2 and m2.start() > 0:
        # If the token is UPI/ and it’s the very first thing, keep the whole line.
        if not t[:m2.start()].strip():
            return t
        return t[:m2.start()].strip()

    return t

def _rows_from_text(page):
    """
    Fallback when extract_tables() fails.
    For each date-grouped chunk, infer amounts using:
      - DR/CR tags in narration (e.g., 'UPI/DR', 'UPI/CR')
      - Heuristic order: Deposits | Withdrawals | Balance
    """
    txt = page.extract_text(x_tolerance=1.5, y_tolerance=3.0) or ""
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]

    # group into chunks that start with a date
    chunks, buf = [], []
    for ln in lines:
        if DATE_ANCHOR_RX.search(ln):  # date can be anywhere (e.g., "S123 17-04-2025 ...")
            if buf:
                chunks.append(" ".join(buf)); buf = []
            buf.append(ln)
        else:
            if buf:
                buf.append(ln)

    if buf:
        chunks.append(" ".join(buf))

    out = []
    last_bal = None

    for ch in chunks:
        m = DATE_ANCHOR_RX.search(ch)
        if not m:
            continue
        date = _parse_date(m.group(0))
        tail = ch[m.end():].strip()


        # DR/CR markers
        has_dr = bool(DR_RX.search(tail))
        has_cr = bool(CR_RX.search(tail))

        # keep ONLY money-looking tokens (must contain '.' or ',')
        all_tokens   = list(AMT_TOKEN.finditer(tail))
        money_tokens = [t for t in all_tokens if ('.' in t.group('num') or ',' in t.group('num'))]

        debit = credit = 0.0
        bal = None
        cut_at = len(tail)

        if len(money_tokens) >= 2:
            # previous = amount, last = balance
            amt_tok = money_tokens[-2]
            bal_tok = money_tokens[-1]
            amt = _to_number(amt_tok.group("num")) or 0.0
            bal = _to_number(bal_tok.group("num"))
            cut_at = amt_tok.start()

            # strict rule: DR -> WITHDRAWAL, CR -> DEPOSIT
            if has_cr and not has_dr:
                debit, credit = 0.0, amt
            elif has_dr and not has_cr:
                debit, credit = amt, 0.0
            else:
                # no tag: use balance delta if available, else default to withdrawal
                if bal is not None and last_bal is not None:
                    if bal > last_bal:  debit, credit = 0.0, amt
                    elif bal < last_bal: debit, credit = amt, 0.0
                    else:                debit, credit = amt, 0.0
                else:
                    debit, credit = amt, 0.0

        elif len(money_tokens) == 1:
            bal = _to_number(money_tokens[-1].group("num"))
            cut_at = money_tokens[-1].start()
        # else: leave all zero

        # narration before first amount used
        nar = tail[:cut_at].strip()
        nar = re.sub(r"(?:\bDr\b|\bCR?\b)\s*$", "", nar, flags=re.I).strip()
        n1, n2 = _split_narration(nar)

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
    return out

# def _is_date(s: str) -> bool:
#     if not s: return False
#     s = str(s).strip()
#     if DATE_RX.search(s):
#         try:
#             dtparse(s, dayfirst=True, fuzzy=True)
#             return True
#         except ParserError:
#             return False
#     try:
#         dtparse(s, dayfirst=True, fuzzy=True)
#         return True
#     except ParserError:
#         return False

# def _parse_date(s: str) -> str:
#     try:
#         d = dtparse(str(s), dayfirst=True, fuzzy=True)
#         return d.strftime("%d/%m/%Y")
#     except Exception:
#         return ""

def _is_date(s: str) -> bool:
    if not s: 
        return False
    s = str(s).strip()
    # m = DATE_RX.fullmatch(s) or DATE_RX.search(s)   # need an explicit date pattern
    m = DATE_RX.fullmatch(s)
    if not m:
        return False
    try:
        dtparse(m.group(0), dayfirst=True, fuzzy=False)
        return True
    except ParserError:
        return False

def _parse_date(s: str) -> str:
    s = str(s or "")
    m = DATE_RX.fullmatch(s) or DATE_RX.search(s)
    if not m:
        return ""
    try:
        d = dtparse(m.group(0), dayfirst=True, fuzzy=False)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return ""
def _to_number(s):
    if s is None: return None
    t = str(s).strip()
    if not t: return None
    # Handle parentheses for negatives and DR/CR tails like "1,234.56 DR"
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg = True
        t = t[1:-1]
    # strip non-numeric except .,- and ,
    t = re.sub(r"[^0-9\-,.]", "", t)
    if not t: return None
    t = t.replace(",", "")
    try:
        val = float(t)
        return -val if neg else val
    except Exception:
        return None

def _classify_header_cell(h):
    """Return one of: date, desc, ref, debit, credit, balance, amount, drcr, unknown"""
    if h is None: return "unknown"
    s = str(h).strip().lower()
    # collapse spaces
    s = re.sub(r"\s+", " ", s)
    for key, patterns in ALIASES.items():
        for p in patterns:
            if re.search(p, s, re.I):
                return key
    return "unknown"

def _score_header_row(row):
    cats = [_classify_header_cell(c) for c in row]
    score = 0
    # Want to see at least date + (debit/credit OR amount+drcr) + maybe balance/desc
    if "date" in cats: score += 2
    if "debit" in cats or "credit" in cats: score += 2
    if "amount" in cats and "drcr" in cats: score += 2
    if "balance" in cats: score += 1
    if "desc" in cats: score += 1
    # Penalize if most are unknown
    unknowns = sum(1 for c in cats if c == "unknown")
    score -= unknowns * 0.2
    return score, cats

def _pick_header(table):
    """
    Given a raw table (list of rows), pick the best header row index and the category per column.
    """
    best = (-1, None, None)  # (score, idx, cats)
    for i, row in enumerate(table[:6]):  # look at first few rows
        score, cats = _score_header_row(row)
        if score > best[0]:
            best = (score, i, cats)
    return best[1], best[2]  # idx, cats

def _ensure_dataframe(table):
    # strip empty rows/cols
    rows = [[(c if c is not None else "").strip() if isinstance(c, str) else c for c in r] for r in table]
    # drop rows that are completely empty
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return pd.DataFrame()
    # make all same length
    width = max(len(r) for r in rows)
    rows = [r + [""]*(width - len(r)) for r in rows]
    return pd.DataFrame(rows)

def _extract_tables_with_variants(page):
    # try a few strategies; return list[table-as-list-of-rows]
    tables = []
    for vs, hs, itol in [
        ("lines", "lines", 2),
        ("text", "text", 0),
        ("lines", "text", 1),
        ("text", "lines", 1),
    ]:
        t = page.extract_tables({
            "vertical_strategy": vs,
            "horizontal_strategy": hs,
            "intersection_tolerance": itol,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
        })
        for table in t or []:
            # keep non-trivial tables
            if table and sum(bool(any(c for c in row)) for row in table) >= 3:
                tables.append(table)
    return tables

def _pick_transaction_table(candidates):
    """
    score tables by: has a date-like first column in many rows,
    has numeric columns, sensible width (4-10)
    """
    best = (0, None)
    for tbl in candidates:
        if not tbl: continue
        width = max(len(r) for r in tbl)
        if width < 4 or width > 12:  # too narrow or too wide
            continue
        # count rows with date-ish cell in first two columns
        rows = [r for r in tbl if any(str(c).strip() for c in r)]
        datey = 0
        numericish = 0
        for r in rows[1:]:
            if len(r) >= 1 and _is_date(r[0]): datey += 1
            if any(NUM_RX.search(str(c or "")) for c in r): numericish += 1
        score = datey * 2 + numericish
        if score > best[0]:
            best = (score, tbl)
    return best[1]

def _clean_text(s: str) -> str:
    s = (s or "").replace("\n", " ").replace("\r", " ")
    # collapse repeated spaces but keep slashes/ids
    s = re.sub(r"\s+", " ", s).strip()
    # remove trailing "DR/CR" tags that sneak into narration
    s = re.sub(r"(?:\bDR\b|\bCR\b)\s*$", "", s, flags=re.I).strip()
    return s


def _split_narration(desc: str):
    """
    Keep narration in one column unless it's very long.
    Only split if > 140 chars, and split at a space boundary.
    """
    # s = _clean_text(desc)
    # # if len(s) <= 140:
    # if len(s) <= 400:   # was 140; keep most entries in NARRATION 1
    #     return s, ""
    # mid = s.rfind(" ", 0, len(s)//2)
    # if mid == -1:
    #     mid = len(s)//2
    # return s[:mid].strip(), s[mid:].strip()
    s = _clean_text(desc)
    if len(s) <= 400:            # <- increase (was 180)
        return s, ""
    mid = s.rfind(" ", 0, 380)   # prefer a space near 380 chars
    if mid == -1:
        mid = 380
    return s[:mid].strip(), s[mid:].strip()


def _collect_text_bits(cells, cutoff_idx=None, exclude_cols=None):
    """All non-empty, non-pure-number text cells before the first amount-like column."""
    bits = []
    cutoff = cutoff_idx if cutoff_idx is not None else len(cells)
    exclude_cols = exclude_cols or set()
    for j, v in enumerate(cells):
        if j in exclude_cols:
            continue
        if j >= cutoff:
            break
        s = _clean_text(v)
        if not s:
            continue
        # avoid pulling pure amounts into narration
        if NUM_RX.fullmatch(s):
            continue
        bits.append(s)
    return bits

#Canara Bank
def _looks_canara(first_page_text: str) -> bool:
    t = (first_page_text or "").upper()
    return (
        "CANARA" in t
        or "CANARA E-PASSBOOK" in t
        or "IFSC CODE CNRB" in t
        or re.search(r"\bCNRB0\d{4}\b", t) is not None
        or ("STATEMENT FOR A/C" in t and "BRANCH CODE" in t and "CUSTOMER ID" in t)
    )

def _canara_column_boxes(page):
    """
    Find column x-bounds by locating 'Date | Particulars | Deposits | Withdrawals | Balance'
    on the current page. Returns dict name -> (x_left, x_right) or {} if not found.
    """
    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)
    wanted = {"date", "particulars", "deposits", "withdrawals", "balance"}
    seen = {}
    for w in words:
        t = (w["text"] or "").strip().lower()
        if t in wanted and t not in seen:
            seen[t] = ((w["x0"] + w["x1"]) / 2.0)  # center x

    if len(seen) < 3:
        return {}

    cols = sorted(seen.items(), key=lambda kv: kv[1])  # by x center
    centers = [c for _, c in cols]
    names   = [n for n, _ in cols]

    # Build vertical split positions at midpoints between neighbor centers
    bounds = [0.0]
    for a, b in zip(centers, centers[1:]):
        bounds.append((a + b) / 2.0)
    bounds.append(page.width)

    boxes = {}
    for i, name in enumerate(names):
        boxes[name] = (bounds[i], bounds[i + 1])
    return boxes

def _canara_rows_from_layout(page, last_bal_in):
    """
    Coordinate-based parser for Canara. Keeps ALL particulars for a date band in NARRATION 1.
    Falls back to text parser if we cannot detect header columns.
    """
    boxes = _canara_column_boxes(page)
    if not boxes:
        return _canara_rows_from_text(page, last_bal_in)

    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)
    # assign column by x-mid
    for w in words:
        xm = (w["x0"] + w["x1"]) / 2.0
        col = None
        for name, (L, R) in boxes.items():
            if L <= xm <= R:
                col = name
                break
        w["col"] = col

    # anchors = rows that have a date **in the date column**
    anchors = []
    for w in words:
        if w["col"] == "date" and DATE_ANCHOR_RX.search(w["text"] or ""):
            anchors.append(w)
    anchors.sort(key=lambda w: w["top"])

    # nothing that looks like a table? fallback to text
    if not anchors:
        return _canara_rows_from_text(page, last_bal_in)

    out = []
    last_bal = last_bal_in
    for idx, a in enumerate(anchors):
        y_top = a["top"] - 0.5
        y_bot = (anchors[idx + 1]["top"] - 0.5) if idx + 1 < len(anchors) else (page.height + 1)
        
        band = [w for w in words if y_top <= w["top"] < y_bot]

        # date from the first date-col word that parses
        date_txt = None
        for w in sorted([w for w in band if w["col"] == "date"], key=lambda z: z["x0"]):
            if DATE_ANCHOR_RX.search(w["text"] or ""):
                date_txt = DATE_ANCHOR_RX.search(w["text"]).group(0)
                break
        date = _parse_date(date_txt or "")

        # narration = *all* words in 'particulars' within the band (keeps Chq: lines too)
        
        parts = [w["text"] for w in sorted([w for w in band if w["col"] == "particulars"],
                                           key=lambda z: (round(z["top"], 1), z["x0"]))]
        nar = " ".join(parts).strip()
        nar = re.sub(r"(?:\bDR\b|\bCR\b)\s*$", "", nar, flags=re.I).strip()
        nar = re.sub(r"\s+", " ", nar)
        n1, n2 = nar, ""  # single-column narration for Canara

        # amounts (read the last numeric in each money column inside the band)
        def _last_amount(colname):
            col_words = [w["text"] for w in band if w["col"] == colname]
            nums = [m.group(0) for txt in col_words for m in AMT_ONLY_RX.finditer(txt or "")]
            return _to_number(nums[-1]) if nums else None

        dep = _last_amount("deposits") or 0.0
        wdl = _last_amount("withdrawals") or 0.0
        bal = _last_amount("balance")

        # Resolve if only one side is set or both accidentally set
        debit, credit = float(wdl or 0.0), float(dep or 0.0)
        if debit and credit:  # rarely both show up because of OCR; prefer the non-zero column
            if abs(debit) >= abs(credit):
                credit = 0.0
            else:
                debit = 0.0

        # If both zero but balance changed, synthesize using delta
        if (not debit and not credit) and (bal is not None) and (last_bal is not None):
            delta = round(bal - last_bal, 2)
            if delta > 0:
                credit = abs(delta)
            elif delta < 0:
                debit = abs(delta)

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

    return out, last_bal

def _canara_extract(pdf) -> pd.DataFrame:
    rows = []
    last_bal = None

    for page in pdf.pages:
        page_rows, last_bal = _canara_rows_from_text(page, last_bal)

        if page_rows:
            rows.extend(page_rows)

    if not rows:
        return pd.DataFrame(columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    df = pd.DataFrame(rows, columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    # keep narration in one column for Canara
    df["NARRATION 1"] = (
        df["NARRATION 1"].astype(str)
        .str.cat(df["NARRATION 2"].astype(str), sep=" ")
        .str.replace(r"\s+", " ", regex=True).str.strip()
    )
    df["NARRATION 2"] = ""

    # sort by date if possible
    try:
        df["__d"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
        df = df.sort_values("__d").drop(columns="__d")
    except Exception:
        pass

    # final safety swap using balance deltas
    prev_bal = None
    for r in range(len(df)):
        bal = df.at[r, "CL. BALANCE"]
        bal = None if bal == "" else float(bal)
        if prev_bal is not None and bal is not None:
            delta = round(bal - prev_bal, 2)
            w = float(df.at[r, "WITHDRAWAL"] or 0.0)
            d = float(df.at[r, "DEPOSIT"] or 0.0)
            if delta > 0 and w > 0 and d == 0:
                df.at[r, "WITHDRAWAL"], df.at[r, "DEPOSIT"] = 0.0, w
            elif delta < 0 and d > 0 and w == 0:
                df.at[r, "WITHDRAWAL"], df.at[r, "DEPOSIT"] = d, 0.0
        if bal is not None:
            prev_bal = bal

    return df

def _canara_rows_from_text(page, last_bal_in):
    """
    Text parser for Canara:
      • A transaction anchor is a line with a DATE and ≥1 amount AFTER the date.
      • Narration ends at the FIRST 'Chq:' line (included) or at the next anchor/header.
      • Keep narration in NARRATION 1 only.
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

        # wait for the real table header
        if not started:
            if UL.startswith("DATE PARTICULARS"):
                started = True
            elif UL.startswith("OPENING BALANCE"):
                # just record opening balance for delta logic; DO NOT emit a row
                toks = list(AMT_ONLY_RX.finditer(ln))
                bal = _to_number(toks[-1].group(0)) if toks else None
                if bal is not None:
                    last_bal = bal
            i += 1
            continue

        if UL.startswith(("DATE PARTICULARS", "PAGE ")):
            i += 1
            continue

        # NOTE: do NOT pre-attach 'Chq:' lines here; tail loop below handles them.

        # anchor?
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
            else:  # exactly one token -> balance only
                bal = _to_number(amount_tokens[-1].group(0))

            # ---- collect tail lines until first 'Chq:' or next anchor/header
            j = i + 1
            tail = []
            while j < len(lines):
                nxt = lines[j].strip()
                UU  = nxt.upper()

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
            # ---- end tail collection
            nar = " ".join(head + tail).strip()
            nar = re.sub(r"(?:\bDR\b|\bCR\b)\s*$", "", nar, flags=re.I).strip()
            # remove any "Opening Balance 12,345.67" fragment if one slipped through
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

        # narration continuation before next anchor
        head.append(ln)
        i += 1

    return out, last_bal

# --- PNB header/intro detectors ---
DESC_HEADER_INTRO_RX = re.compile(r"""(?xi)
    ^\s*account\s+statement\b|
    ^\s*statement\s+period\b|
    ^\s*customer\s+details\b|
    ^\s*nominee\b|
    ^\s*description\b|
    ^\s*branch\s*name\b|
    ^\s*cheque\s*no\.?\b|
    ^\s*kims\s*remarks\b|
    ^\s*txn\.?\s*no\.?\b
""")

# --- cut first-row junk that comes before the real description ---
FIRST_ROW_CUT_BEFORE_DESC = re.compile(
    r"^.*?\bDescription\s+Branch\s+Name\b\s*", re.I
)

# --- stronger anchors for footer/disclaimer fragments that can bleed into the last row ---
DISCLAIMER_ANCHOR_RX = re.compile(r"""(?xi)
    unless\s+constituent\s+notifies|
    immediately\s+of\s+any\s+discrepancy|
    (?:computer|compu[sr]er)\s+generated|
    shown\s+in\s+the\s+statement\s+of\s+account|
    statement\s+of\s+account\s+do\s+not\s+require|
    please\s+do\s+not\s+accept|
    customers\s+are\s+requested|
    abbreviations\s+are\s+as\s+under
""")

PAGE_HEAD_LEAD_RX = re.compile(
    r"(?i)^\s*account\s+statement\s+for\s+(?:account\s+number\s+\d+)\s*"
)
# KEY_CASH_SELF_RX = re.compile(r"\b(?:TO\s+SELF|BY\s+CASH)\b", re.I)
# LEAD_LONGNUM_BEFORE_KEY_RX = re.compile(r"^\s*\d{9,}\s+(?=(?:TO\s+SELF|BY\s+CASH)\b)", re.I)
KEY_CASH_SELF_RX = re.compile(r"\b(?:TO\s+SELF|BY\s+SELF|BY\s+CASH)\b", re.I)
LEAD_LONGNUM_BEFORE_KEY_RX = re.compile(
    r"^\s*\d{9,}\s+(?=(?:TO\s+SELF|BY\s+SELF|BY\s+CASH)\b)", re.I
)

# optional: remove the stray 'null' that appears in NEFT_IN:null
NEFT_NULL_RX = re.compile(r"(?i)(NEFT[_-]IN:)\s*null/?")
NEXT_TXN_HARD_CUT_RX = re.compile(r"""(?xi)
    \bNEFT(?:[_-](?:IN|OUT))?:?     |
    \bNEFT[_-][A-Z0-9]+             |
    \bIMPS\b|\bRTGS\b|\bACH\b|\bPOS\b|\bATM\b|
    \bBIL\b|\bSMS\s+CHRG\b|\bCASH\s+HAND\b|
    \bYESBN[A-Z0-9]*\b|\bYESB[A-Z0-9]*\b
""")
# panjab PNB
def _fix_first_last_narration_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Touch ONLY two rows:
      - First row: remove header/intro junk before 'Description Branch Name'
      - Last row : cut off disclaimers/footers from the first anchor phrase onward
    """
    if df is None or df.empty or "NARRATION 1" not in df.columns:
        return df

    out = df.copy()

    # --- first row cleanup ---
    i0 = out.index[0]
    s0 = str(out.at[i0, "NARRATION 1"] or "")
    # drop any leading header junk up to 'Description Branch Name'
    s0 = FIRST_ROW_CUT_BEFORE_DESC.sub("", s0)
    # also strip any generic header-y phrases you already had:
    s0 = re.sub(DESC_HEADER_INTRO_RX, "", s0).strip()
    s0 = re.sub(DESC_HEADER_LINE_RX,  "", s0).strip()
    s0 = re.sub(HEADER_DROP_RX,       "", s0).strip()
    s0 = re.sub(r"\s{2,}", " ", s0).strip(" -:/|")
    out.at[i0, "NARRATION 1"] = s0

    # --- last row cleanup ---
    il = out.index[-1]
    sl = str(out.at[il, "NARRATION 1"] or "")
    # find first occurrence of any disclaimer/footer phrase and cut there
    m = (DISCLAIMER_ANCHOR_RX.search(sl)
         or FOOTER_DROP_LINE_RX.search(sl)
         or FOOTER_DROP_RX.search(sl))
    if m:
        sl = sl[:m.start()].rstrip(" -:/|")
    sl = re.sub(r"\s{2,}", " ", sl)
    out.at[il, "NARRATION 1"] = sl

    return out

# panjan PNB
def _looks_pnb(first_page_text: str) -> bool:
    """
    Heuristic: PNB pages show 'Txn No.' + 'Dr Amount' + 'Cr Amount' + 'KIMS Remarks' in header.
    """
    t = (first_page_text or "").lower()
    return (
        ("txn no" in t and "txn date" in t) and
        ("dr amount" in t or "cr amount" in t) and
        ("balance" in t) and
        ("kims" in t and "remark" in t)   # strong signal from PNB layout
    )


def _pnb_column_boxes(page):
    """
    Find PNB columns by the header band that contains:
      Txn Date | Description | Dr Amount | Cr Amount | Balance
    Returns dict {name: (xL, xR)} or {} if not found.
    """
    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

    # Collect by horizontal line (rounded top)
    lines = {}
    for w in words:
        y = round(w["top"], 1)
        lines.setdefault(y, []).append(w)
    for y in lines:
        lines[y].sort(key=lambda z: z["x0"])

    def has(txt, needle):
        return needle in (txt or "").strip().lower()

    centers = {}
    def mark(name, ws):
        if not ws: return
        xm = sum((w["x0"] + w["x1"]) / 2.0 for w in ws) / len(ws)
        centers[name] = xm

    # Look across ALL lines (earlier code only looked at top 60%)
    for y, ws in lines.items():
        low = [(i, (w["text"] or "").strip().lower()) for i, w in enumerate(ws)]
        for i, t in low:
            # "Txn Date" sometimes split across two words
            if t == "txn" and i + 1 < len(low) and low[i + 1][1].startswith("date"):
                mark("date", [ws[i], ws[i + 1]])
            if "description" in t:
                mark("desc", [ws[i]])
            if "balance" in t:
                mark("bal", [ws[i]])
            # allow loose "dr amount" / "cr amount"
            if t == "dr" and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("dr", [ws[i], ws[i + 1]])
            if t == "cr" and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("cr", [ws[i], ws[i + 1]])
            # sometimes they print "debit amount"/"credit amount"
            if "debit" in t and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("dr", [ws[i], ws[i + 1]])
            if "credit" in t and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("cr", [ws[i], ws[i + 1]])

    required = {"date", "desc", "bal"}
    if not required.issubset(centers.keys()):
        return {}

    cols_sorted = sorted(centers.items(), key=lambda kv: kv[1])
    xs = [0.0] + [(a[1] + b[1]) / 2.0 for a, b in zip(cols_sorted, cols_sorted[1:])] + [page.width]

    boxes = {}
    for (name, xm), L, R in zip(cols_sorted, xs, xs[1:]):
        boxes[name] = (L, R)

    # If DR/CR missing, split the gap between description and balance
    if "dr" not in boxes or "cr" not in boxes:
        L = boxes.get("desc", (0, 0))[1]
        R = boxes.get("bal", (page.width, page.width))[0]
        if R > L:
            mid = (L + R) / 2.0
            boxes["dr"] = (L, mid)
            boxes["cr"] = (mid, R)

    return boxes


def _pnb_rows_from_layout(page, last_bal_in):
    """
    PNB layout parser with post-processing that merges isolated "BY CASH"/"TO SELF"
    rows into neighbor rows when they stand alone without amounts.
    """
    boxes = _pnb_column_boxes(page)
    if not boxes:
        return [], last_bal_in

    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

    # tag words with column
    for w in words:
        xm = (w["x0"] + w["x1"]) / 2.0
        w["col"] = None
        for name, (L, R) in boxes.items():
            if L <= xm <= R:
                w["col"] = name
                break

    anchors = [w for w in words if w["col"] == "date" and DATE_ANCHOR_RX.search(w.get("text") or "")]
    anchors.sort(key=lambda w: w["top"])

    from collections import defaultdict

    def last_num(colname, band):
        col_words = [(round(w["top"], 1), (w.get("text") or "")) for w in band if w.get("col") == colname]
        if not col_words:
            return None
        lines = defaultdict(list)
        for y, txt in col_words:
            if FOOTER_DROP_RX.search(txt):
                continue
            lines[y].append(txt)
        picked = None
        for y in sorted(lines.keys()):
            line = " ".join(lines[y])
            line = re.sub(r"\b(CR?|DR?)\.?/?\b", "", line, flags=re.I)
            nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
            if nums:
                tok = nums[-1]
                if ("," in tok) or ("." in tok):
                    picked = _to_number(tok)
        return picked

    def last_balance_text_and_val(band):
        col_words = [(round(w["top"], 1), (w.get("text") or "")) for w in band if w.get("col") == "bal"]
        if not col_words:
            return None, None
        lines = defaultdict(list)
        for y, txt in col_words:
            if FOOTER_DROP_RX.search(txt):
                continue
            lines[y].append(txt)
        printed = None
        for y in sorted(lines.keys()):
            line = " ".join(lines[y]).strip()
            line = re.sub(r"\b(CR?|DR?)\.?/?\b", "", line, flags=re.I)
            nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
            if nums:
                printed = nums[-1]
        if printed is None:
            return None, None
        return printed, _to_number(printed)

    def fmt_money(x): return "" if x is None else f"{float(x):,.2f}"

    out = []
    last_bal_val = last_bal_in

    # if no anchors, return empty (fallback upstream will handle)
    if not anchors:
        return out, last_bal_val

    # build vertical cuts
    cuts = [0.0] + [(anchors[i]["top"] + anchors[i+1]["top"]) / 2.0 for i in range(len(anchors)-1)] + [page.height + 1]
    carry_tail = ""

    for idx, a in enumerate(anchors):
        y_top = cuts[idx]
        y_bot = cuts[idx + 1]
        band  = [w for w in words if y_top <= w["top"] < y_bot]

        # date
        date_txt = None
        for w in sorted([w for w in band if w.get("col") == "date"], key=lambda z: z["x0"]):
            m = DATE_ANCHOR_RX.search(w.get("text") or "")
            if m:
                date_txt = m.group(0)
                break
        date = _parse_date(date_txt or "")

        # narration words in desc column
        desc_words = sorted([w for w in band if w.get("col") == "desc"],
                            key=lambda z: (round(z["top"], 1), z["x0"]))
        parts = []
        for w in desc_words:
            t = (w.get("text") or "").strip()
            if not t or t in {"-", "–", "—"}: 
                continue
            if FOOTER_DROP_RX.search(t) or TITLE_PREFIX_RX.search(t):
                continue
            parts.append(t)
       
        narration = re.sub(r"\s{2,}", " ", " ".join(parts)).strip()
        narration = re.sub(r"^\s*[-–—•·]+\s*", "", narration)
        narration = PAGE_TITLE_RX.sub("", narration)
       # HARD TRUNCATE only when narration *starts* with UPI/DR or TO SELF/BY CASH,
        # and only cut at tokens that cannot belong to the same UPI narration.
        if SPECIAL_START_RX.match(narration or ""):
            m_cut = NEXT_TXN_HARD_CUT_RX.search(narration)
            # be conservative: only cut if the token appears a bit later in the string
            if m_cut and m_cut.start() >= 10:
                narration = narration[:m_cut.start()].strip()

        narration, _ = _split_special_narration(narration)

        # cleanup specific artifacts
        narration = PAGE_HEAD_LEAD_RX.sub("", narration)
        if KEY_CASH_SELF_RX.search(narration):
            narration = LEAD_LONGNUM_BEFORE_KEY_RX.sub("", narration)
        narration = NEFT_NULL_RX.sub(r"\1", narration)
        narration = _truncate_special_narration(narration)

        # amounts
        dr = last_num("dr", band) or 0.0
        cr = last_num("cr", band) or 0.0
        if dr and cr:
            if abs(dr) >= abs(cr):
                cr = 0.0
            else:
                dr = 0.0

        # balance
        bal_txt, bal_val = last_balance_text_and_val(band)
        if bal_val is None and last_bal_val is not None:
            bal_val = round(last_bal_val - float(dr or 0.0) + float(cr or 0.0), 2)
            bal_txt = fmt_money(bal_val)
        # --- synthesize Dr/Cr from balance delta ONLY for normal rows
        if (not dr and not cr) and (bal_val is not None) and (last_bal_val is not None):
            delta = round(bal_val - last_bal_val, 2)
            if delta > 0:  cr = abs(delta)
            elif delta < 0: dr = abs(delta)

       
        out.append([date, narration, "", float(dr or 0.0), float(cr or 0.0), bal_txt or ""])
        if bal_val is not None:
            last_bal_val = bal_val

    # -------------------------
    # POST-PROCESS: merge isolated "BY CASH"/"TO SELF" rows
    # -------------------------
    def _is_key_cash_row(narr):
        return bool(KEY_CASH_SELF_RX.search(str(narr or "")))

    merged = []
    i = 0
    while i < len(out):
        row = out[i]
        date, n1, n2, wdl, dep, baltxt = row
        # treat 0.0 or "" as "no amount"
        has_amounts = bool((wdl and float(wdl) != 0.0) or (dep and float(dep) != 0.0))
        if _is_key_cash_row(n1) and not has_amounts:
            # prefer merge into previous row
            if merged:
                prev = merged[-1]
                prev[1] = (str(prev[1]).strip() + " " + str(n1).strip()).strip()
                prev[2] = (str(prev[2]).strip() + " " + str(n2).strip()).strip()
                if baltxt:
                    prev[5] = baltxt or prev[5]
                # copy amounts if previous lacks them
                if (not prev[3] or float(prev[3]) == 0.0) and wdl:
                    prev[3] = wdl
                if (not prev[4] or float(prev[4]) == 0.0) and dep:
                    prev[4] = dep
                # drop this row
                i += 1
                continue
            else:
                # no previous row: try merge into next
                if i + 1 < len(out):
                    nxt = out[i + 1]
                    nxt[1] = (str(n1).strip() + " " + str(nxt[1]).strip()).strip()
                    nxt[2] = (str(n2).strip() + " " + str(nxt[2]).strip()).strip()
                    if (not nxt[3] or float(nxt[3]) == 0.0) and wdl:
                        nxt[3] = wdl
                    if (not nxt[4] or float(nxt[4]) == 0.0) and dep:
                        nxt[4] = dep
                    if baltxt and (not nxt[5]):
                        nxt[5] = baltxt
                    i += 1
                    continue
                else:
                    # last row -> keep as-is
                    merged.append(row)
                    i += 1
                    continue
        # default: keep row
        merged.append(row)
        i += 1

    out = merged
    return out, last_bal_val


def _pnb_extract_with_boxes(pdf, base_boxes=None) -> pd.DataFrame:
    """
    PNB extractor (coordinate-driven, narration preserved).
    - DATE: 'Txn Date'
    - NARRATION 1: exact Description text (order preserved). NARRATION 2: always "".
    - WITHDRAWAL: Dr Amount
    - DEPOSIT: Cr Amount
    - CL. BALANCE: exact number string from 'Balance' (keep commas/decimals; ignore Cr./Dr.).
                   If unreadable, derive from previous: prev - Dr + Cr, formatted '#,##0.00'.
    """
    def fmt_money(x): return "" if x is None else f"{float(x):,.2f}"
    def overlaps(a0,a1,b0,b1,ratio=0.30):
        inter = max(0.0, min(a1,b1) - max(a0,b0))
        return inter >= ratio * (a1 - a0)

    from collections import defaultdict
    all_rows, last_bal_val = [], None

    for page in pdf.pages:
        # get boxes per page (fallback to base_boxes on pages that miss headers)
        boxes = _pnb_column_boxes(page) or base_boxes
        if not boxes:
            continue

        words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

        # column tag
        for w in words:
            xm = (w["x0"] + w["x1"]) / 2.0
            w["col"] = None
            for name, (L, R) in boxes.items():
                if L <= xm <= R:
                    w["col"] = name
                    break

        # anchors = dates in 'date' column
        anchors = [w for w in words if w["col"] == "date" and DATE_ANCHOR_RX.search(w.get("text") or "")]
        anchors.sort(key=lambda w: w["top"])

        def last_num(colname, band):
            """
            Return the last money-like token (must contain a comma or a decimal point)
            from the named column inside this band. Never search other columns/band.
            Never accept plain integers (prevents picking up account numbers, UTRs, etc.).
            """
            from collections import defaultdict
            lines = defaultdict(list)
            for w in band:
                if w.get("col") != colname:
                    continue
                txt = (w.get("text") or "")
                if FOOTER_DROP_RX.search(txt):
                    continue
                lines[round(w["top"], 1)].append(txt)

            for y in sorted(lines.keys()):
                line = " ".join(lines[y])
                # strip DR/CR labels then look for money-like tokens
                line = re.sub(r"\b(CR?|DR?)\.?/?\b", "", line, flags=re.I)
                nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
                if nums:
                    val = _to_number(nums[-1])
                    if val is not None:
                        return val
            return None

        def last_balance_text_and_val(band):
            col_words = [(round(w["top"], 1), (w.get("text") or "")) for w in band if w.get("col") == "bal"]
            if not col_words: return None, None
            lines = defaultdict(list)
            for y, txt in col_words:
                if FOOTER_DROP_RX.search(txt): continue
                lines[y].append(txt)
            printed = None
            for y in sorted(lines.keys()):
                line = " ".join(lines[y]).strip()
                line = re.sub(r"\b(Cr|Dr)\.?\b", "", line, flags=re.I)  # ignore label, keep numeric text
                nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
                if nums:
                    printed = nums[-1]  # e.g. "47,799.16"
            if printed is None: return None, None
            return printed, _to_number(printed)
        # build vertical cut lines at the midpoints between date anchors
        cuts = [0.0] + [(anchors[i]["top"] + anchors[i+1]["top"]) / 2.0 for i in range(len(anchors)-1)] + [page.height + 1]
        carry_tail = ""
        for idx, a in enumerate(anchors):
            y_top = cuts[idx]
            y_bot = cuts[idx + 1]
            band  = [w for w in words if y_top <= w["top"] < y_bot]
           # date
            date_txt = None
            for w in sorted([w for w in band if w.get("col") == "date"], key=lambda z: z["x0"]):
                m = DATE_ANCHOR_RX.search(w.get("text") or "")
                if m: date_txt = m.group(0); break
            date = _parse_date(date_txt or "")

            # narration (exactly as in Description x-range)
            desc_L = boxes["desc"][0] - 15.0
            right_guards = [boxes[n][0] for n in ("dr","cr","bal") if n in boxes]
            desc_R = min(right_guards) - 1.0 if right_guards else page.width
            desc_words = sorted(
                [w for w in band if w.get("col") == "desc"],
                key=lambda z: (round(z["top"], 1), z["x0"])
            )
            parts = []
            for w in desc_words:
                t = (w.get("text") or "").strip()
                if not t or t in {"-", "–", "—"}: 
                    continue
                if FOOTER_DROP_RX.search(t) or TITLE_PREFIX_RX.search(t):
                    continue
                parts.append(t)
            

            narration = re.sub(r"\s{2,}", " ", " ".join(parts)).strip()
            narration = re.sub(r"^\s*[-–—•·]+\s*", "", narration)

            # NEW: drop "Account Statement for ..." if it leaked into the first row
            narration = PAGE_TITLE_RX.sub("", narration)
            # HARD TRUNCATE only when narration *starts* with UPI/DR or TO SELF/BY CASH,
            # and only cut at tokens that cannot belong to the same UPI narration.
            if SPECIAL_START_RX.match(narration or ""):
                m_cut = NEXT_TXN_HARD_CUT_RX.search(narration)
                # be conservative: only cut if the token appears a bit later in the string
                if m_cut and m_cut.start() >= 10:
                    narration = narration[:m_cut.start()].strip()

            narration, _ = _split_special_narration(narration)

            # keep the specific account-number remover too
            narration = PAGE_HEAD_LEAD_RX.sub("", narration)
            
            # ---- keep "BY CASH" / "TO SELF" clean & self-contained
            if KEY_CASH_SELF_RX.search(narration):
                narration = LEAD_LONGNUM_BEFORE_KEY_RX.sub("", narration)
                # narration = re.sub(r"^(.*?\b(?:TO\s+SELF|BY\s+CASH)\b).*?$", r"\1", narration, flags=re.I)

            # remove 'NEFT_IN:null' artifact
            narration = NEFT_NULL_RX.sub(r"\1", narration)
            narration = _truncate_special_narration(narration)
            
            # amounts
            dr = last_num("dr", band) or 0.0
            cr = last_num("cr", band) or 0.0

            if dr and cr:
                if abs(dr) >= abs(cr): cr = 0.0
                else: dr = 0.0

            # balance (exact text)
            bal_txt, bal_val = last_balance_text_and_val(band)
            if bal_val is None and last_bal_val is not None:
                bal_val = round(last_bal_val - float(dr or 0.0) + float(cr or 0.0), 2)
                bal_txt = fmt_money(bal_val)
            # If both sides are still zero but the balance changed, synthesize from delta
            # --- synthesize Dr/Cr from balance delta ONLY for normal rows
            if (not dr and not cr) and (bal_val is not None) and (last_bal_val is not None):
                delta = round(bal_val - last_bal_val, 2)
                if delta > 0:  cr = abs(delta)
                elif delta < 0: dr = abs(delta)

            all_rows.append([date, narration, "", float(dr or 0.0), float(cr or 0.0), bal_txt or ""])
            if bal_val is not None:
                last_bal_val = bal_val

    if not all_rows:
        return pd.DataFrame(columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    df = pd.DataFrame(all_rows, columns=[
        "DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"
    ])

    # <<< only this line is new:
    df = _fix_first_last_narration_only(df)

    return df


def _pnb_extract(pdf) -> pd.DataFrame:
    rows = []
    last_bal = None
    for page in pdf.pages:
        page_rows, last_bal = _pnb_rows_from_layout(page, last_bal)
        if not page_rows:
            continue
        else:
            rows.extend(page_rows)

    if not rows:
        return pd.DataFrame(columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    df = pd.DataFrame(rows, columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    # sort by date (safe)
    try:
        df["__d"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
        df = df.sort_values("__d").drop(columns="__d")
    except Exception:
        pass

    # one more safety swap using balance deltas (like your other paths)
    prev = None
    for r in range(len(df)):
        bal = df.at[r, "CL. BALANCE"]
        bal = None if bal == "" else float(bal)
        if prev is not None and bal is not None:
            delta = round(bal - prev, 2)
            w = float(df.at[r, "WITHDRAWAL"] or 0.0)
            d = float(df.at[r, "DEPOSIT"] or 0.0)
            if delta > 0 and w > 0 and d == 0:
                df.at[r, "WITHDRAWAL"], df.at[r, "DEPOSIT"] = 0.0, w
            elif delta < 0 and d > 0 and w == 0:
                df.at[r, "WITHDRAWAL"], df.at[r, "DEPOSIT"] = d, 0.0
        if bal is not None:
            prev = bal

    return df

# UNION BANK
# match 1,234.56 (Dr) OR 1,234.56 Dr anywhere in the string
UNION_AMT_TAGGED_RX = re.compile(r"""
    (?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+)       # money like 1,234.56 or 1234.56
    \s*
    (?:                                                 # tag variants
        [\(\[\{]\s*(?P<tag>dr|cr|debit|credit|deb|cred)\s*[\)\]\}]   # (Dr)/(Cr)
      | (?P<tag2>dr|cr)\b                                             # or bare Dr/Cr
    )
""", re.I | re.X)

# Union column header cues (case-insensitive)
UNION_HEADER_HINT_RX = re.compile(r"""(?xi)
    \bunion\s+bank\s+of\s+india\b|
    \bS\.?No\b.*\bTransaction\s+Id\b.*\bRemarks\b.*\bAmount\(Rs\.?\)\b.*\bBalance\(Rs\.?\)\b|
    \bVyom\b|
    unionbankofindia\.co\.in
""")
# Anything that marks the start of Union's legend / footer block
UNION_LEGEND_START_RX = re.compile(r"""(?xi)
    ^\s*(?:NEFT|RTGS|UPI|BBPS)\b|
    https?://\S+|
    ^\s*this\s+is\s+system\s+generated\b|
    ^\s*registered\s+office\b|
    ^\s*details\s+of\s+statement\b|
    request\s+to\s+our\s+customers
""")

# put this once near your other regexes (top of the file)
FOOTER_CUT_RX = re.compile(
    r"""(?xi)
        https?://\S+                          |  # any URL
        request\s+to\s+our\s+customers.*?statement\.?  |  # Union footer sentence
        details\s+of\s+statement.*$              # other footer lead-ins
    """
)

# replace your current UNION_FOOTER_CUT_RX with:
UNION_FOOTER_CUT_RX = re.compile(r"""(?xi)
    https?://\S+                                  |   # any URL
    request\s+to\s+our\s+customers.*?statement    |   # footer sentence
    details\s+of\s+statement.*$                   |
    for\s+any\s+discrepancy.*$                    |
    ^\s*registered\s+office\b.*$                  |
    ^\s*details\s+of\s+statement\b.*$             |
    ^\s*neft\s*:\s*national\s+electronic\s+fund   |   # legend block
    ^\s*rtgs\s*:\s*real\s+time\s+gross            |
    ^\s*upi\s*:\s*unified\s+payment               |
    ^\s*bharat\s+bill\s+payment\s+service         |
    ^\s*this\s+is\s+system\s+generated            |
    ^\s*s\.?\s*no\.?\s+date\s+transaction\s+id\s+remarks\s+amount\(rs\.?\)\s+balance\(rs\.?\)\s*$  # header row
""")

# "Opening Balance" / "Closing Balance" cues that can appear in Remarks
UNION_OB_RX = re.compile(r"\bopening\s+bal(?:ance)?\b", re.I)
UNION_CB_RX = re.compile(r"\bclosing\s+bal(?:ance)?\b", re.I)
UNION_CLOSING_RX = re.compile(r"\bclosing\s+bal(?:ance)?\b", re.I)


def _looks_union(first_page_text: str) -> bool:
    t = first_page_text or ""
    return bool(UNION_HEADER_HINT_RX.search(t))


def _union_column_boxes(page):
    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

    # collect header word centers by row
    lines = {}
    for w in words:
        y = round(w["top"], 1)
        lines.setdefault(y, []).append(w)
    for y in lines:
        lines[y].sort(key=lambda z: z["x0"])

    centers = {}
    def mark(key, ws):
        xm = sum((w["x0"] + w["x1"]) / 2.0 for w in ws) / len(ws)
        centers[key] = xm

    def norm(s): return (s or "").strip().lower()
    for y, ws in lines.items():
        low = [(i, norm(w["text"])) for i, w in enumerate(ws)]
        for i, t in low:
            if re.fullmatch(r"s\.?\s*no\.?", t): mark("sno", [ws[i]])
            if t == "date": mark("date", [ws[i]])
            if t.startswith("transaction") and i + 1 < len(low) and "id" in low[i + 1][1]:
                mark("txnid", [ws[i], ws[i + 1]])
            if t == "transaction" and i + 1 < len(low) and low[i + 1][1] == "id":
                mark("txnid", [ws[i], ws[i + 1]])
            if "remarks" in t: mark("remarks", [ws[i]])
            if t.startswith("amount"): mark("amount", [ws[i]])
            if t.startswith("balance"): mark("balance", [ws[i]])

    # Canonicalize by physical order so Amount is always left of Balance
    present = [k for k in ["sno","date","txnid","remarks","amount","balance"] if k in centers]
    if len(present) < 4:
        return {}

    ordered = sorted(present, key=lambda k: centers[k])  # left → right
    canonical = ["sno","date","txnid","remarks","amount","balance"]
    centers = { canonical[i]: centers[ordered[i]] for i in range(len(ordered)) }

    # build vertical splits
    cols_sorted = sorted(centers.items(), key=lambda kv: kv[1])
    splits = [0.0] + [(a[1] + b[1]) / 2.0 for a, b in zip(cols_sorted, cols_sorted[1:])] + [page.width]
    boxes = {}
    for (name, xm), L, R in zip(cols_sorted, splits, splits[1:]):
        boxes[name] = (L, R)

    # small padding
    def widen(LR, pad=6.0):
        return (max(0.0, LR[0]-pad), min(page.width, LR[1]+pad))
    for k in list(boxes):
        boxes[k] = widen(boxes[k], 6.0)

    return boxes



def _union_scan_opening_balance(words, first_anchor_top, boxes):
    """
    Find 'Opening Balance' printed above the first transaction row and return its numeric value.
    Works even if words weren't tagged into 'balance' column yet.
    """
    bal_L, bal_R = boxes["balance"]
    # widen a bit – some PDFs shift the printed balance slightly
    bal_L -= 10.0
    bal_R += 10.0

    # Look only ABOVE the first txn band (header area)
    header_words = [w for w in words if w["top"] < first_anchor_top]
    header_words.sort(key=lambda z: (round(z["top"], 1), z["x0"]))

    # Prefer lines that actually mention "Opening Balance"
    linebuf = {}
    for w in header_words:
        y = round(w["top"], 1)
        linebuf.setdefault(y, []).append(w)

    import re as _re
    ob_rx = _re.compile(r"\bopening\s+bal(?:ance)?\b", _re.I)

    # pass 1: lines mentioning Opening Balance (anywhere), pick a number in the balance x-range
    for y in sorted(linebuf.keys()):
        parts = linebuf[y]
        joined_txt = " ".join((p.get("text") or "").strip() for p in parts if (p.get("text") or "").strip())
        if not ob_rx.search(joined_txt):
            continue
        # collect numbers positioned inside balance x-range
        nums_txt = []
        for p in parts:
            xm = (p.get("x0", 0) + p.get("x1", 0)) / 2.0
            if bal_L <= xm <= bal_R:
                t = (p.get("text") or "")
                nums_txt.extend(m.group(0) for m in AMT_ONLY_RX.finditer(t))
        if nums_txt:
            val = _to_number(nums_txt[-1])
            if val is not None:
                return float(val)

    # pass 2: if no explicit 'Opening Balance' text, pick the last money token in balance x-range above anchors
    flat_txt = " ".join((w.get("text") or "") for w in header_words
                        if bal_L <= ((w.get("x0",0)+w.get("x1",0))/2.0) <= bal_R)
    nums = list(AMT_ONLY_RX.finditer(flat_txt or ""))
    if nums:
        val = _to_number(nums[-1].group(0))
        if val is not None:
            return float(val)

    return None


def _union_remarks_exact(band):
    """
    Join ALL words printed in the 'remarks' column for this row band,
    preserving order and spacing as-is. No cleaning other than collapsing
    multiple spaces and stripping ends. We intentionally do NOT remove
    DR/CR, numbers, or tokens inside the remarks cell.
    """
    parts = []
    for w in sorted(band, key=lambda z: (round(z.get("top", 0.0), 1), z.get("x0", 0.0))):
        if w.get("col") != "remarks":
            continue
        t = (w.get("text") or "").strip()
        if not t:
            continue
        parts.append(t)
    # collapse repeated spaces only
    return re.sub(r"\s{2,}", " ", " ".join(parts)).strip()

def _chars_in_box(page, x0, y0, x1, y1):
    """Return all characters that fall inside the given rectangle."""
    out = []
    for ch in getattr(page, "chars", []):
        cx0, cy0, cx1, cy1 = ch.get("x0",0), ch.get("top",0), ch.get("x1",0), ch.get("bottom",0)
        if (cx1 >= x0) and (cx0 <= x1) and (cy1 >= y0) and (cy0 <= y1):
            out.append(ch)
    return out

def _text_from_chars(chars, y_tol=1.5, gap_tol=1.0):
    """Rebuild line text from pdfplumber chars."""
    if not chars:
        return ""
    # group by approximate line (y bucket)
    lines = {}
    for ch in chars:
        y = round(ch.get("top", 0.0) / y_tol)
        lines.setdefault(y, []).append(ch)
    out_lines = []
    for y in sorted(lines):
        row = sorted(lines[y], key=lambda c: c.get("x0",0.0))
        txt=[]; prev=None
        for c in row:
            x0, x1 = c.get("x0",0.0), c.get("x1",0.0)
            if prev is not None and (x0-prev) > gap_tol:
                txt.append(" ")
            txt.append(c.get("text",""))
            prev = x1
        out_lines.append("".join(txt).strip())
    return re.sub(r"\s{2,}", " ", " ".join(out_lines)).strip()


# --- fuzzy footer cutter (tolerates OCR double-letters like "TThhiiss") ---
def _fuzzy_phrase_rx(phrase: str) -> str:
    pat = []
    for ch in phrase.lower():
        if ch.isalpha():
            pat.append(ch + "+")          # allow double letters
        elif ch.isspace():
            pat.append(r"\s+")
        else:
            pat.append(re.escape(ch))
    return r"(?:" + "".join(pat) + ")"



# Much more tolerant to OCR: allows doubled/missing letters inside words
_FOOTER_FUZZY_RXS = [
    re.compile(r"t+h+i+s+\s+i+s+\s+s+y+s+t+e+m+", re.I),                 # "This is system ..."
    re.compile(r"u+n+i+f+i+e+d+\s+p+a+y+m+e+n+t+\s+i+n+t+e+r+", re.I),   # "Unified Payment Inter..."
    re.compile(r"n+a+t+i+o+n+a+l+\s+e+l+e+c+t+r+o+n+i+c+\s+f+u+n+d+", re.I),  # "National Electronic Fund ..."
    re.compile(r"r+e+g+i+s+t+e+r+e+d+\s+o+f+f+i+c+e+", re.I),
    re.compile(r"r+e+q+u+e+s+t+\s+t+o+\s+o+u+r+\s+c+u+s+t+o+m+e+r+s+", re.I),
    re.compile(r"p+a+g+e+\s+n+o+", re.I),
]


def _cut_footer_noise(s: str) -> str:
    if not s:
        return s
    cut_pos = []

    # URLs are always footer-ish here
    m = re.search(r"https?://\S+", s, re.I)
    if m:
        cut_pos.append(m.start())

    # fuzzy phrases (handles doubled letters / spacing)
    for rx in _FOOTER_FUZZY_RXS:
        mm = rx.search(s)
        if mm:
            cut_pos.append(mm.start())

    if not cut_pos:
        return s
    return s[: min(cut_pos)].rstrip(" -:/|")


# def extract_union_narration(page, boxes, y0, y1):
#     """
#     Capture narration text exactly as seen in Remarks column.
#     Ensures prefixes like 'UPIAR/...' are not cut.
#     """

  
#     def _chars_in_box(xL, yT, xR, yB):
#         out = []
#         for ch in getattr(page, "chars", []):
#             if (ch["x1"] >= xL and ch["x0"] <= xR
#                 and ch["bottom"] > yT and ch["top"] < yB):
#                 out.append(ch)
#         out.sort(key=lambda z: (round(z["top"], 1), z["x0"]))
#         return out

#     def _text_from_chars(chars):
#         lines = {}
#         for ch in chars:
#             y = round(ch.get("top", 0.0), 1)
#             lines.setdefault(y, []).append(ch)
#         parts = []
#         for y in sorted(lines):
#             row = "".join(c.get("text", "") for c in lines[y])
#             parts.append(row.strip())
#         return re.sub(r"\s+", " ", " ".join(parts)).strip()

#     # column edges
#     rL, rR = boxes["remarks"]
#     aL, _  = boxes["amount"]

#     # --- widen strongly to the left to never cut 'UPI' ---

#     txn_R = boxes.get("txnid", (0.0, rL))[1]          # right edge of Txn Id col (fallback to rL)

#     L = max(0.0, rL - 40.0)   # go far left, beyond Remarks start
#     R = min(aL - 1.0, rR + 8.0)

#     nar = _text_from_chars(_chars_in_box(L, y0, R, y1))

#     # If narration starts with just digits or clipped, retry even wider
#     # if nar and not nar.upper().startswith("UPI"):
#     #     L2 = max(0.0, rL - 70.0)
#     #     nar2 = _text_from_chars(_chars_in_box(L2, y0, R, y1))
#     #     if nar2 and "UPI" in nar2.upper():
#     #         nar = nar2

#     # # Remove stray leading serial numbers if any (from S.No column)
#     # nar = re.sub(r"^\s*\d+\s+", "", nar)
#       # If it looks clipped (starts with '/', 'PIAR', etc.), cautiously widen left,
#     # but still never go left of the TxnId column.
#     if nar and re.match(r"^(?:/|PIAR|IAR)", nar, re.I):
#         for bump in (8.0, 14.0, 20.0):
#             L_try = max(txn_R + 2.0, (rL - 4.0) - bump)
#             nar2 = _text_from_chars(_chars_in_box(L_try, y0, R, y1))
#             if nar2 and "UPI" in nar2.upper():
#                 nar = nar2
#                 break

#     # Remove any stray S.No/TxnId prefix that may have leaked earlier pages
#     # nar = re.sub(r"^\s*(?:\d+|[A-Z]\d{5,})\s+", "", nar)

#     # new — strips S.No or TxnId even if there is NO space before / or UPI
#     nar = re.sub(r"^\s*(?:\d+|[A-Z]\d{5,})(?=\s*(?:/|UPI))", "", nar, flags=re.I)


#     # Cut footer if leaked
#     m = FOOTER_CUT.search(nar)
#     if m:
#         nar = nar[:m.start()].rstrip(" -:/|")
#     nar = _cut_footer_noise(nar)
#     return nar

# def extract_union_narration(page, boxes, y0, y1, right_until=None):
def extract_union_narration(page, boxes, y0, y1, right_until=None, strict_left=False):

    """
    Capture narration text exactly as seen in Remarks column.
    Ensures prefixes like 'UPIAR/...' are not cut.
    Only trims footer/legend noise; does NOT strip S.No/TxnId any more
    (that is done conditionally by the caller for the last row only).
    """
    def _chars_in_box(xL, yT, xR, yB):
        out = []
        for ch in getattr(page, "chars", []):
            if (ch["x1"] >= xL and ch["x0"] <= xR and ch["bottom"] > yT and ch["top"] < yB):
                out.append(ch)
        out.sort(key=lambda z: (round(z["top"], 1), z["x0"]))
        return out

    def _text_from_chars(chars):
        lines = {}
        for ch in chars:
            y = round(ch.get("top", 0.0), 1)
            lines.setdefault(y, []).append(ch)
        parts = []
        for y in sorted(lines):
            row = "".join(c.get("text", "") for c in lines[y])
            parts.append(row.strip())
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    # column edges
    rL, rR = boxes["remarks"]
    aL, _  = boxes["amount"]

    # default right edge (old behavior)
    # R_default = min(aL - 1.0, rR + 8.0)

    # R_default = min(aL - 0.5, rR + 20.0)
    # # allow caller to tighten/loosen the right edge up to the first amount token
    # if right_until is not None:
    #     R = min(max(right_until - 0.8, rL + 2.0), aL - 0.5)
    # else:
    #     R = R_default
    # be very generous; hug the Amount left border
    R_default = min(aL - 0.05, rR + 40.0)

    if right_until is not None:
        # even when using a dynamic cut, never trim earlier than ~0.05pt left of Amount
        # R = min(max(right_until - 0.2, rL + 2.0), aL - 0.05)
        R = max(R_default, max(right_until - 0.2, rL + 2.0))
    else:
        R = R_default

    # strongly widen to the left so 'UPI...' never gets clipped
    txn_R = boxes.get("txnid", (0.0, rL))[1]
    # L = max(0.0, rL - 40.0)
    L = (rL + 0.5) if strict_left else max(0.0, rL - 40.0)

    nar = _text_from_chars(_chars_in_box(L, y0, R, y1))

    # If narration looks clipped (starts with '/', 'PIAR', etc.), cautiously widen left,
    # but never go left of TxnId column.
    if nar and re.match(r"^(?:/|PIAR|IAR)", nar, re.I):
        for bump in (8.0, 14.0, 20.0):
            L_try = max(txn_R + 2.0, (rL - 4.0) - bump)
            nar2 = _text_from_chars(_chars_in_box(L_try, y0, R, y1))
            if nar2 and "UPI" in nar2.upper():
                nar = nar2
                break

    # hard cut if any residual footer/legend leaked into the joined string
    m = UNION_FOOTER_CUT_RX.search(nar)
    if m:
        nar = nar[:m.start()].rstrip(" -:/|")

    # fuzzy footer cut (OCR tolerant) as a last pass
    nar = _cut_footer_noise(nar)
    return nar

def _union_rows_from_layout(page, last_bal_in, is_last_page=False):
    """
    Robust Union parser:
      • Anchors = words in DATE column matching DATE_ANCHOR_RX
      • Narration = ALL words whose x-mid ∈ [remarks.L, amount.L) for the same y-band
      • Amount = prefer same-line tagged (Dr/Cr), else column scan
      • Balance = same-line if possible, else nearest balance line, else band scan
      • If amount is zero but balance moved, synthesize side from delta
      • Opening/Closing Balance rows keep printed balance and zero amounts
    """
    boxes = _union_column_boxes(page)
    if not boxes:
        return [], last_bal_in

    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)
    if not words:
        return [], last_bal_in

    # tag column by x-mid
    for w in words:
        xm = (w["x0"] + w["x1"]) / 2.0
        col = None
        for name, (L, R) in boxes.items():
            if L <= xm <= R:
                col = name
                break
        w["col"] = col

    # anchors = date words ONLY inside 'date' column
    anchors = [w for w in words if w["col"] == "date" and DATE_ANCHOR_RX.search(w.get("text") or "")]
    anchors.sort(key=lambda w: w["top"])

    # where the 'Closing Balance' banner sits (to clamp the last band)
    closing_words = [w for w in words if UNION_CLOSING_RX.search(w.get("text") or "")]
    closing_y = min([w["top"] for w in closing_words], default=page.height + 1)

    if not anchors:
        return [], last_bal_in

    # carry page-to-page balance, but prefer printed Opening Balance if present
    last_bal = last_bal_in
    ob = _union_scan_opening_balance(words, anchors[0]["top"], boxes)
    if ob is not None:
        last_bal = ob

    # ---------- helpers ----------
    def _join_col(colname, band):
        pick = [w for w in band if w.get("col") == colname]
        pick.sort(key=lambda z: (round(z["top"], 1), z["x0"]))
        txt = " ".join((w.get("text") or "").strip() for w in pick if (w.get("text") or "").strip())
        return re.sub(r"\s+", " ", txt).strip()

    # def _narration_between(band, L, R):
    def _narration_between(band, L, R, *, is_last_page=False):
        parts = []
        for w in sorted(band, key=lambda z: (round(z["top"], 1), z["x0"])):
            xm = (w.get("x0", 0.0) + w.get("x1", 0.0)) / 2.0
            t  = (w.get("text") or "").strip()
            if not t:
                continue
            # keep only tokens inside the remarks band, but never pure money tokens
            if L <= xm < R and not AMT_ONLY_RX.fullmatch(t):
                # skip obvious footer/legend/header fragments
                if FOOTER_DROP_RX.search(t) or UNION_FOOTER_CUT_RX.search(t) or _looks_footerish(t):
                    continue
                parts.append(t)

        s = re.sub(r"\s+", " ", " ".join(parts)).strip()
        s = re.sub(r"(?:\bDR\b|\bCR\b)[.)]?$", "", s, flags=re.I).strip()

        # hard cut if any residual footer/legend leaked into the joined string
        m_foot = UNION_FOOTER_CUT_RX.search(s)
        if m_foot:                           # cut always (safe; pattern is very specific)
            s = s[:m_foot.start()].rstrip(" -:/|")

        return s

    def _line_words(band, y0, col=None, tol=3.0):
        """words that sit on (approximately) the same y as y0"""
        yref = round(y0, 1)
        out = []
        for w in band:
            if col is not None and w.get("col") != col:
                continue
            if abs(round(w.get("top", 0.0), 1) - yref) <= tol:
                out.append(w)
        out.sort(key=lambda z: z.get("x0", 0.0))  # left→right
        return out

    def _last_money_on_line(words_on_line):
        txt = " ".join((w.get("text") or "") for w in words_on_line)
        txt = re.sub(r"\b(CR?|DR?)\b[.)]?", "", txt, flags=re.I)
        nums = list(AMT_ONLY_RX.finditer(txt or ""))
        return _to_number(nums[-1].group(0)) if nums else None

    # pick the balance from the balance-column line NEAREST to this row
    def _balance_nearest_from_line(band, row_y, max_tol=3.0):
        from collections import defaultdict
        groups = defaultdict(list)
        for w in band:
            if w.get("col") != "balance":
                continue
            y = round(w.get("top", 0.0), 1)
            groups[y].append(w)

        best_val, best_gap = None, 1e9
        target = round(row_y, 1)
        for y, ws in groups.items():
            gap = abs(y - target)
            if gap > max_tol:
                continue
            line = " ".join((w.get("text") or "") for w in ws).strip()
            if FOOTER_DROP_RX.search(line) or UNION_FOOTER_CUT_RX.search(line) or _looks_footerish(line) or UNION_LEGEND_START_RX.search(line):
                 continue
            if UNION_CLOSING_RX.search(line):  # skip 'Closing Balance' banner line
                continue
            line = re.sub(r"\b(CR?|DR?)\b[.)]?", "", line, flags=re.I)
            nums = list(AMT_ONLY_RX.finditer(line))
            if not nums:
                continue
            v = _to_number(nums[-1].group(0))
            if v is None:
                continue
            if gap < best_gap:
                best_val, best_gap = v, gap
        return best_val
    def _first_amount_x_on_line(band, row_y, boxes, tol=2.0):
        """X-mid of the first numeric amount that appears on this row (either in Amount or Balance line).
        Returns None if not found."""
        yref = round(row_y, 1)

        def words_on_line(colname):
            return [w for w in band
                    if w.get("col") == colname and abs(round(w.get("top", 0.0), 1) - yref) <= tol]

        cand = []
        for colname in ("amount", "balance"):
            ws = sorted(words_on_line(colname), key=lambda z: z.get("x0", 0.0))
            for w in ws:
                t = (w.get("text") or "")
                m = AMT_ONLY_RX.search(t)
                if m:
                    xm = (w.get("x0", 0.0) + w.get("x1", 0.0)) / 2.0
                    cand.append(xm)
                    break
        return min(cand) if cand else None

    def _balance_from_balance_col(band):
        bal_L, bal_R = boxes["balance"]
        bal_L -= 6.0
        bal_R += 6.0

        from collections import defaultdict
        lines = defaultdict(list)
        for w in band:
            xm = (w.get("x0", 0.0) + w.get("x1", 0.0)) / 2.0
            if not (bal_L <= xm <= bal_R):
                continue
            y = round(w.get("top", 0.0), 1)
            lines[y].append(w)

        for y in sorted(lines.keys()):
            raw = " ".join((w.get("text") or "") for w in sorted(lines[y], key=lambda z: z.get("x0", 0.0))).strip()
               # skip obvious legend/footer lines
            if FOOTER_DROP_RX.search(raw) or UNION_FOOTER_CUT_RX.search(raw) or _looks_footerish(raw) or UNION_LEGEND_START_RX.search(raw):
                continue
            if UNION_CLOSING_RX.search(raw):
                continue
            raw = re.sub(r"\b(CR?|DR?)\b[.)]?", "", raw, flags=re.I)
            nums = [m.group(0) for m in AMT_ONLY_RX.finditer(raw)]
            if not nums:
                continue
            val = _to_number(nums[-1])
            if val is not None:
                return val
        return None

    def _amt_from_amount_col(band, bal_val=None):
        txt = _join_col("amount", band)
        if not txt:
            return (0.0, 0.0, False)
        m = UNION_AMT_TAGGED_RX.search(txt.strip())
        if not m:
            return (0.0, 0.0, False)
        a = _to_number(m.group("num"))
        if a is None:
            return (0.0, 0.0, False)
        tag = (m.group("tag") or m.group("tag2") or "").lower()
        wdl = float(a) if tag.startswith("d") else 0.0
        dep = float(a) if tag.startswith("c") else 0.0
        # guard: if the tagged amount equals the printed balance, treat as bleed
        if bal_val is not None:
            if (wdl and abs(wdl - bal_val) < 0.01) or (dep and abs(dep - bal_val) < 0.01):
                return (0.0, 0.0, False)
        return (wdl, dep, True)

    def _line_text_right_of(band, row_y, x_cut, tol=1.0):
        yref = round(row_y, 1)
        ws = [w for w in band if abs(round(w.get("top",0.0),1) - yref) <= tol
                            and ((w["x0"] + w["x1"]) / 2.0) >= x_cut]
        ws.sort(key=lambda z: z.get("x0", 0.0))
        return " ".join((w.get("text") or "") for w in ws)

    def _parse_amt_bal_from_line(txt):
        # first money token = amount, last money token = balance
        mm = list(re.finditer(r'(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)\.\d+(?!\w)|(?<!\w)\d{1,3}(?:,\d{3})+(?!\w)', txt))
        if not mm: return None, None, None
        amt = _to_number(mm[0].group(0))
        bal = _to_number(mm[-1].group(0))
        tag = None
        window = txt[mm[0].end(): mm[-1].start()]
        mtag = re.search(r'\b(Dr|Cr)\b', window, re.I)
        if mtag: tag = mtag.group(1).lower()
        return amt, bal, tag
    # ---------- /helpers ----------

    out = []

    # vertical bands between anchors
    cuts = [0.0] + [(anchors[i]["top"] + anchors[i + 1]["top"]) / 2.0
                    for i in range(len(anchors) - 1)] + [page.height + 1]

    # If the page has no Opening Balance line, seed from the first row itself.
    if last_bal is None:
        y_top0, y_bot0 = cuts[0], cuts[1]
        band0 = [w for w in words if y_top0 <= w["top"] < y_bot0]
        row_y0 = anchors[0]["top"]

        # 1) printed balance for row-0
        bal0 = _last_money_on_line(_line_words(band0, row_y0, col="balance", tol=2.0))
        if bal0 is None:
            bal0 = _balance_nearest_from_line(band0, row_y0, max_tol=2.0)
        if bal0 is None:
            bal0 = _balance_from_balance_col(band0)

        # 2) tagged amount (Dr/Cr) for row-0
        w0 = d0 = 0.0
        tagged0 = False
        amt_line_words0 = _line_words(band0, row_y0, col="amount", tol=2.0)
        m_amt0 = UNION_AMT_TAGGED_RX.search(" ".join((w.get("text") or "") for w in amt_line_words0))
        if m_amt0:
            aval0 = _to_number(m_amt0.group("num"))
            if aval0 is not None:
                tag0 = (m_amt0.group("tag") or m_amt0.group("tag2") or "").lower()
                if tag0.startswith("d"):  w0, tagged0 = float(aval0), True
                elif tag0.startswith("c"): d0, tagged0 = float(aval0), True
        if not tagged0:
            w0, d0, tagged0 = _amt_from_amount_col(band0, bal_val=bal0)

        # 3) back-compute prev balance to seed page:
        #    new_bal = prev - wdl + dep  => prev = new_bal + wdl - dep
        if (bal0 is not None) and tagged0:
            last_bal = round(bal0 + float(w0 or 0.0) - float(d0 or 0.0), 2)

    for i, a in enumerate(anchors):
        # ---- compute next_anchor_y early ----
        next_anchor_y = anchors[i + 1]["top"] if i + 1 < len(anchors) else (page.height + 1)

        # initial band
        y_top = max(cuts[i], a["top"] - 0.5)
        y_bot = cuts[i + 1]

        # clamp against the Closing Balance banner (if it sits inside this band)
        if closing_y < (page.height + 1):
            y_bot = min(y_bot, closing_y - 0.5)


        # -------- last row on the page --------
        if i == len(anchors) - 1:
            # start wide; this row has no "next anchor"
            y_bot = page.height + 1

            if closing_y < (page.height + 1):
                # allow a tiny overscan; we will cut the banner text from the joined string later
                y_bot = min(closing_y + 2.0, page.height + 1)
            else:
                y_bot = min(y_bot + 8.0, page.height + 1)

            # if this is the statement's last page, clamp to first legend/footer line
            if is_last_page:
                legend_tops = [
                    w["top"] for w in words
                    if UNION_LEGEND_START_RX.search(w.get("text") or "")
                    or UNION_FOOTER_CUT_RX.search(w.get("text") or "")
                    or _looks_footerish(w.get("text") or "")
                ]
                if legend_tops:
                    y_bot = min(y_bot, min(legend_tops) - 0.8)


        else:
            # -------- non-last rows --------
            # keep band within this row and the next
            y_bot = min(y_bot, next_anchor_y - 0.5)
            row_token_tops = [
                w["top"] for w in words
                if (w.get("col") in ("amount", "balance", "remarks"))
                and (a["top"] - 1.0 <= w["top"] <= next_anchor_y - 0.5)
            ]
            if row_token_tops:
                y_bot = max(y_bot, max(row_token_tops) + 2.0)

         
        if y_bot <= y_top:
            continue
        band = [w for w in words if y_top <= w["top"] < y_bot]
        # ... proceed as before ...

        # DATE
        date_txt = None
        for w in sorted([w for w in band if w.get("col") == "date"], key=lambda z: z["x0"]):
            m = DATE_ANCHOR_RX.search(w.get("text") or "")
            if m:
                date_txt = m.group(0)
                break
        date = _parse_date(date_txt or "")
        # --- NARRATION (robust) ---------------------------------------------
        row_y = a["top"]

        
        x_first_amt = _first_amount_x_on_line(band, row_y, boxes, tol=2.0)

        # strict for the entire last page:
        use_strict = bool(is_last_page)

        nar = extract_union_narration(
            page, boxes, y_top, y_bot,
            right_until=x_first_amt,
            strict_left=use_strict
        )



        # Trim footer/legend if any slipped in
        m_foot = UNION_FOOTER_CUT_RX.search(nar)
        if m_foot:
            nar = nar[:m_foot.start()].rstrip(" -:/|")

        m_close = UNION_CLOSING_RX.search(nar)
        if m_close:
            nar = nar[:m_close.start()].rstrip(" -:/|")

        if is_last_page:
            nar = TXNID_LEAK_RX.sub("", nar).lstrip()


        
        # NEW: if this is the very last row of the statement, drop a leading S.No/TxnId stuck to '/UPI'
        if is_last_page and i == len(anchors) - 1:
            nar = TXNID_LEAK_RX.sub("", nar).lstrip()
        # On the very last printed row only, drop a stray S.No/TxnId prefix if it
        # sits immediately before "/..." or "UPI..."
        if is_last_page and i == len(anchors) - 1:
            nar = re.sub(r"^\s*(?:\d+|[A-Z]\d{5,})(?=\s*(?:/|UPI))", "", nar, flags=re.I)

        # Fallback if narration is still empty
        if not nar:
            nar = re.sub(r"\s{2,}", " ", _join_col("remarks", band)).strip()
        # --- /NARRATION ------------------------------------------------------

        # ---------- SAME-LINE FIRST, then FALLBACKS ----------
        # defaults
        wdl = dep = 0.0
        tagged = False
        bal = None
        has_pdf_bal = False

        # 1) Same-line parse to the right of Amount column
        x_cut = boxes["amount"][0]
        txt_right = _line_text_right_of(band, row_y, x_cut, tol=1.0)
        amt_lin, bal_lin, tag_lin = _parse_amt_bal_from_line(txt_right)

        if bal_lin is not None:
            bal = bal_lin
            has_pdf_bal = True

        if (amt_lin is not None) and tag_lin:
            if tag_lin.lower().startswith("d"):
                wdl, tagged = float(amt_lin), True
            elif tag_lin.lower().startswith("c"):
                dep, tagged = float(amt_lin), True

        # 2) Column scan for amount ONLY if still not tagged
        if not tagged:
            amt_line_words = _line_words(band, row_y, col="amount", tol=2.0)
            m_amt = UNION_AMT_TAGGED_RX.search(" ".join((w.get("text") or "") for w in amt_line_words))
            if m_amt:
                aval = _to_number(m_amt.group("num"))
                if aval is not None:
                    tag = (m_amt.group("tag") or m_amt.group("tag2") or "").lower()
                    if tag.startswith("d"):  wdl, tagged = float(aval), True
                    elif tag.startswith("c"): dep, tagged = float(aval), True

        # 3) Balance fallbacks ONLY if bal is None
        if bal is None:
            bal = _last_money_on_line(_line_words(band, row_y, col="balance", tol=2.0))
            has_pdf_bal = bal is not None
        if bal is None:
            bal = _balance_nearest_from_line(band, row_y, max_tol=3.5)
            if bal is not None:
                has_pdf_bal = True
        if bal is None:
            bal = _balance_from_balance_col(band)
            if bal is not None:
                has_pdf_bal = True

        # 4) If still no balance but we have last_bal and a tagged amount, synthesize
        if bal is None and last_bal is not None and (wdl or dep):
            bal = round(last_bal - float(wdl or 0.0) + float(dep or 0.0), 2)

        # if tagged amount equals balance, drop it (it was the balance, not the amount)
        if tagged and bal is not None:
            if wdl and abs(wdl - bal) < 0.01: wdl, tagged = 0.0, False
            if dep and abs(dep - bal) < 0.01: dep, tagged = 0.0, False


        if not tagged:
            w2, d2, tagged2 = _amt_from_amount_col(band, bal_val=bal)
            if tagged2:
                wdl, dep, tagged = w2, d2, True
        # ---------- /SAME-LINE + FALLBACKS ----------

        # Opening/Closing balance rows: force zero amounts
        UL = nar.upper()
        if UNION_OB_RX.search(nar) or UL.startswith("OPENING BAL"):
            wdl, dep = 0.0, 0.0
        if UNION_CB_RX.search(nar) or UL.startswith("CLOSING BAL"):
            wdl, dep = 0.0, 0.0

        # If both sides zero but balance moved, synthesize amounts only
        if (not wdl and not dep) and (bal is not None) and (last_bal is not None):
            delta = round(bal - last_bal, 2)
            if delta > 0:  dep = abs(delta)
            elif delta < 0: wdl = abs(delta)

        # debug sanity (optional print)
        if bal is not None and last_bal is not None:
            expected = round(last_bal - float(wdl or 0.0) + float(dep or 0.0), 2)
            if abs(expected - bal) >= 0.01:
                print("BAL MISMATCH", date, nar[:40], "prev:", last_bal, "wdl:", wdl, "dep:", dep, "pdf:", bal, "calc:", expected)

        out.append([
            date,
            nar,
            "",
            float(wdl or 0.0),
            float(dep or 0.0),
            "" if bal is None else float(bal),
        ])

        if bal is not None:
            last_bal = bal

    return out, last_bal



def _union_extract(pdf) -> pd.DataFrame:
    rows = []
    last_bal = None
    

    
    n_pages = len(pdf.pages)
    last_bal = None
    # helper: detect the page that shows the "Closing Balance" banner
    def _page_has_closing_balance(pg):
        try:
            ws = pg.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)
        except Exception:
            return False
        for w in ws or []:
            if UNION_CLOSING_RX.search(w.get("text") or ""):
                return True
        return False

    # pre-compute which PDF page is the *statement* last page
    closing_flags = [ _page_has_closing_balance(pg) for pg in pdf.pages ]
    for idx, page in enumerate(pdf.pages):
        page_rows, last_bal = _union_rows_from_layout(page, last_bal, is_last_page=bool(closing_flags[idx]))

        # --- per-page fallback if nothing was parsed but the page has dates
        if not page_rows:
            txt = page.extract_text(x_tolerance=1.5, y_tolerance=3.0) or ""
            if DATE_ANCHOR_RX.search(txt):
                # reuse your generic text chunker (keeps balance+amount order)
                fallback_rows = _rows_from_text(page)
                if fallback_rows:
                    page_rows = fallback_rows
                    # keep last_bal in sync if fallback produced balances
                    for _, _, _, w, d, b in page_rows:
                        if b not in ("", None):
                            last_bal = float(b)

        if page_rows:
            rows.extend(page_rows)
    if not rows:
        return pd.DataFrame(columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    df = pd.DataFrame(rows, columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])

    # Final safety swap using balance delta (identical to other extractors)
    prev_bal = None
    for r in range(len(df)):
        bal = df.at[r, "CL. BALANCE"]
        bal = None if bal == "" else float(bal)
        if prev_bal is not None and bal is not None:
            delta = round(bal - prev_bal, 2)
            w = float(df.at[r, "WITHDRAWAL"] or 0.0)
            d = float(df.at[r, "DEPOSIT"]    or 0.0)
            if w == 0.0 and d == 0.0 and delta != 0.0:
                if delta > 0:  d = abs(delta)
                else:          w = abs(delta)
                df.at[r, "WITHDRAWAL"], df.at[r, "DEPOSIT"] = w, d
        if bal is not None:
            prev_bal = bal

    return df

# main code
def _normalize_rows(df, header_idx, cats):
    """
    Normalize a bank table to columns:
      DATE | NARRATION 1 | NARRATION 2 | WITHDRAWAL | DEPOSIT | CL. BALANCE
    """
    TOL = 0.01

    # --- normalize frame and header mapping ---
    df = df.copy()
    df.columns = [f"c{i}" for i in range(df.shape[1])]

    # We receive 'cats' already computed per column.
    where = {}
    for i, cat in enumerate(cats or []):
        if cat == "unknown":
            continue
        # keep first occurrence
        where.setdefault(cat, i)

    idx_date    = where.get("date", 0)
    idx_desc    = where.get("desc", None)
    idx_ref     = where.get("ref", None)
    idx_debit   = where.get("debit", None)     # Withdrawals
    idx_credit  = where.get("credit", None)    # Deposits
    idx_balance = where.get("balance", None)
    idx_amount  = where.get("amount", None)    # single Amount + DR/CR style
    idx_drcr    = where.get("drcr", None)

    # ---------------- HDFC tweak (exact insertion point) ----------------
    # If the header has *both* Debit and Credit columns, prefer them
    # and ignore the single Amount + DR/CR style to prevent mis-mapping.
    if (idx_debit is not None) and (idx_credit is not None):
        idx_amount = None
        idx_drcr = None
    # --------------------------------------------------------------------

    # If balance wasn't detected from headers, pick the right-most mostly-numeric column
    # (HDFC frequently splits "Closing Balance" across two header cells)
    data = df.iloc[header_idx + 1:].reset_index(drop=True)
    # --- HDFC: force-pick balance to the RIGHT of all amount-like columns (REPLACE your old scan with this) ---
    max_amt_col = max([c for c in [idx_debit, idx_credit, idx_amount, idx_drcr] if c is not None] + [-1])
    if idx_balance is None and not data.empty:
        cand = None
        for c in range(df.shape[1] - 1, max_amt_col, -1):  # only columns to the right of amounts
            col = data.get(f"c{c}")
            if col is None:
                continue
            num_hits = sum(_to_number(v) is not None for v in col)
            if num_hits >= max(3, int(len(data) * 0.6)):
                cand = c
                break
        if cand is not None:
            if idx_credit == cand:  # it was mis-tagged as Credit; free that slot
                idx_credit = None
            idx_balance = cand
    # -------------- /HDFC tweaks --------------


    # First row after header is data
    data = df.iloc[header_idx + 1:].reset_index(drop=True)
    n = len(data)

    # Find the first amount-like column index to delimit narration cells
    amount_like_idx = [i for i in [idx_debit, idx_credit, idx_amount, idx_drcr, idx_balance] if i is not None]
    cutoff_default = min(amount_like_idx) if amount_like_idx else df.shape[1]

    out = []
    last_bal = None

    i = 0
    while i < n:
        row = data.iloc[i]
        cells = [row.get(f"c{t}", "") for t in range(df.shape[1])]

        # --- detect transaction start by a date in the date column ---
        # --- detect transaction start by a clean date in the date column ---
        row_text = " ".join(str(x) for x in cells if x is not None)

        # Drop BOM/other header-summary junk rows
        if BOM_NOISE_RX.search(row_text) or HDFC_HEADER_NOISE_RX.search(row_text):
            i += 1
            continue

        raw_date = cells[idx_date] if idx_date is not None and idx_date < len(cells) else ""
        raw_date_str = str(raw_date or "").strip()

        # Require the date cell to be JUST a date (no words like "from", "to", etc.)
        if not DATE_RX.fullmatch(raw_date_str):
            i += 1
            continue


        if not _is_date(raw_date):
            i += 1
            continue

        date = _parse_date(raw_date)

        # cutoff for narration on THIS row (some banks put balance before amounts)
        cutoff = cutoff_default
        narration_bits = []

        # Exclude: Description (already captured as 'lead'), Date column, and Ref column
        exclude = set()
        if idx_desc is not None and idx_desc < len(cells):
            lead = _clean_text(cells[idx_desc])
            if lead:
                narration_bits.append(lead)
            exclude.add(idx_desc)

        if idx_date is not None:
            exclude.add(idx_date)
        # if idx_ref is not None:
        #     exclude.add(idx_ref)

        # Collect only text before the first amount-like column, skipping date/ref cells
        narration_bits.extend(_collect_text_bits(cells, cutoff_idx=cutoff, exclude_cols=exclude))
    
        j = i + 1
        while j < n:
            nxt = data.iloc[j]
            nxt_cells = [nxt.get(f"c{t}", "") for t in range(df.shape[1])]
            nxt_date_raw = nxt_cells[idx_date] if idx_date is not None and idx_date < len(nxt_cells) else ""
            # Hard stop if we hit the summary/footer area on HDFC pages
            nxt_text = " ".join(str(x) for x in nxt_cells if x is not None)
            if HDFC_SUMMARY_START_RX.search(nxt_text) or HDFC_SUMMARY_INLINE_RX.search(nxt_text):
                break

            # 1) normal date boundary
            # 1) normal date boundary
            if _is_date(nxt_date_raw):
                break

             # 2) HDFC quirk: a row without date but with an amount + a "txn head" should start a new txn
            nxt_has_amount = any(
                (_to_number(nxt_cells[col]) not in (None, 0.0))
                for col in (idx_debit, idx_credit, idx_amount) if (col is not None and col < len(nxt_cells))
            )
            nxt_desc_txt = _clean_text(nxt_cells[idx_desc]) if (idx_desc is not None and idx_desc < len(nxt_cells)) else ""
            nxt_ref_txt  = _clean_text(nxt_cells[idx_ref])  if (idx_ref  is not None and idx_ref  < len(nxt_cells)) else ""
            if nxt_has_amount and (TXN_HEAD_RX.search(nxt_desc_txt) or re.search(r"[A-Za-z]", nxt_ref_txt)):
                break
           # otherwise, treat as a wrapped/continuation line and collect its text
            narration_bits.extend(
                _collect_text_bits(
                    nxt_cells,
                    cutoff_idx=cutoff_default,
                    exclude_cols={c for c in [idx_date] if c is not None}  # don't exclude idx_ref here
                )
            )
            j += 1
        ref_txt = ""
        if idx_ref is not None and idx_ref < len(cells):
            ref_txt = _clean_text(cells[idx_ref])
            # Ignore empty or all-zero refs like "000000"
            if ref_txt and not re.fullmatch(r"0+", ref_txt):
                # Keep as a separate piece of info; don't push into narration_bits here.
                pass
            else:
                ref_txt = ""

        # de-duplicate repeated wrapped fragments
        seen = set()
        narration_bits = [b for b in narration_bits if b and (b not in seen and not seen.add(b))]

        full_narr = " ".join(narration_bits)
        # strip inline date-y fragments
        full_narr = DATE_RX.sub("", full_narr)
        full_narr = HEAD_DATE_SHARD_RX.sub("", full_narr) 
        full_narr = re.sub(r"\s{2,}", " ", full_narr).strip(" /-")

        n1, n2 = _pack_narration(
            lead_desc=lead if 'lead' in locals() else "",
            other_bits=[b for b in narration_bits if b != (lead if 'lead' in locals() else "")],
            ref_txt=ref_txt or None
        )
        row_text = f"{n1} {n2}".strip()
        # --- BOM: drop page header/summary junk rows ---
        if BOM_NOISE_RX.search(row_text):
            i = j
            continue

        # Skip OPENING BALANCE row but seed last_bal from its balance cell
        if OPENING_BAL_RX.search(row_text):
            if idx_balance is not None:
                ob = _to_number(cells[idx_balance])
                if ob is not None:
                    last_bal = ob
            i = j
            continue

        # Skip CLOSING BALANCE line
        if CLOSING_BAL_RX.search(row_text):
            i = j
            continue

        # --- read amounts from columns on the START row ---
        debit = credit = None
        if idx_debit is not None and idx_debit < len(cells):
            debit = _to_number(cells[idx_debit])
        if idx_credit is not None and idx_credit < len(cells):
            credit = _to_number(cells[idx_credit])

    
        # Single "Amount + DR/CR" style (strict mapping only)
        if (debit in (None, 0.0)) and (credit in (None, 0.0)) and idx_amount is not None and idx_amount < len(cells):
            amt = _to_number(cells[idx_amount])
            tag = str(cells[idx_drcr] or "")
            if amt is not None:
                if DR_RX.search(tag): debit, credit = amt, 0.0
                elif CR_RX.search(tag): debit, credit = 0.0, amt
                # else: leave both 0.0 (do not guess)

        # bal = _to_number(cells[idx_balance]) if idx_balance is not None else None
        bal = _to_number(cells[idx_balance]) if idx_balance is not None else None

        # grab the rightmost numeric value to the right of all amount-like columns.
        if (bal is None) or (bal == 0.0):
            last_amount_col = max([c for c in [idx_debit, idx_credit, idx_amount, idx_drcr] if c is not None] + [-1])
            right_cells = cells[last_amount_col + 1:]
            for v in reversed(right_cells):
                num = _to_number(v)
                if num is None:
                    continue
                # Skip if it's literally the debit/credit again
                if (idx_debit is not None and _to_number(cells[idx_debit]) is not None and
                    abs(num - float(_to_number(cells[idx_debit]) or 0.0)) < 0.01):
                    continue
                if (idx_credit is not None and _to_number(cells[idx_credit]) is not None and
                    abs(num - float(_to_number(cells[idx_credit]) or 0.0)) < 0.01):
                    continue
                bal = num
                break

        # If still no balance but we know last balance and at least one amount, derive it
        if bal is None and last_bal is not None and ((debit or 0) != 0 or (credit or 0) != 0):
            # running balance = last_bal - withdrawal + deposit
            bal = round(last_bal - float(debit or 0.0) + float(credit or 0.0), 2)

          # --- HDFC/right-edge balance rescue ---
        if bal is None:
            # Find the rightmost numeric cell after the last amount-like column.
            last_amount_col = max([c for c in [idx_debit, idx_credit, idx_amount, idx_drcr] if c is not None], default=-1)
            right_cells = cells[last_amount_col + 1 : ]  # everything to the right

            # scan from right to left and pick the first numeric that isn't the debit/credit again
            for v in reversed(right_cells):
                num = _to_number(v)
                if num is None:
                    continue
                # skip if this number equals the debit/credit on this row (within tolerance)
                if (debit is not None and abs(num - float(debit)) < 0.01) or \
                   (credit is not None and abs(num - float(credit)) < 0.01):
                    continue
                bal = num
                break
        
        # --- peek-ahead into the first continuation row for balance (HDFC page-wrap quirk) ---
        if bal is None and j < n:
            nxt2 = data.iloc[j]
            nxt2_cells = [nxt2.get(f"c{t}", "") for t in range(df.shape[1])]
            last_amount_col = max([c for c in [idx_debit, idx_credit, idx_amount, idx_drcr] if c is not None], default=-1)
            # look to the far-right of the next line
            for v in reversed(nxt2_cells[last_amount_col + 1:]):
                num = _to_number(v)
                if num is None:
                    continue
                # avoid reusing this row's debit/credit values
                if (debit is not None and abs(num - float(debit)) < 0.01) or \
                (credit is not None and abs(num - float(credit)) < 0.01):
                    continue
                bal = num
                break

        # --- DR/CR hint from narration ---
        tag_text = (n1 + " " + n2)
        has_dr = bool(DR_RX.search(tag_text))
        has_cr = bool(CR_RX.search(tag_text))
        # If exactly one side has value=0, use the hint to place the non-zero on the correct side
        if has_dr and not has_cr and (credit or 0) > 0 and (debit in (None, 0)):
            debit, credit = credit, 0.0
        elif has_cr and not has_dr and (debit or 0) > 0 and (credit in (None, 0)):
            credit, debit = debit, 0.0

        # --- reconcile using balance delta whenever we have it ---
        if bal is not None and last_bal is not None:
            delta = round(bal - last_bal, 2)  # +ve => net deposit, -ve => net withdrawal
            w = float(debit or 0.0)
            d = float(credit or 0.0)

            # If only one side has a value and it contradicts delta, swap.
            if delta > 0 and w > 0 and d == 0:
                d, w = w, 0.0
            elif delta < 0 and d > 0 and w == 0:
                w, d = d, 0.0

            # If both sides are zero but balance changed, synthesize
            if w == 0 and d == 0 and abs(delta) > TOL:
                if delta > 0:
                    d = abs(delta)
                else:
                    w = abs(delta)

            debit, credit = w, d

        # write row
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

        # jump over continuation lines
        i = j

    df_out = pd.DataFrame(out, columns=["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"])

    if not df_out.empty:
        try:
            df_out["__d"] = pd.to_datetime(df_out["DATE"], dayfirst=True, errors="coerce")
            # stable sort → ties keep the original read order (page order)
            df_out = df_out.sort_values(["__d"], kind="mergesort").drop(columns="__d")
        except Exception:
            pass
    
        # --- HDFC: backfill missing CL. BALANCE at the top using the next known balance ---
        b = pd.to_numeric(df_out["CL. BALANCE"], errors="coerce")           # may have NaNs *or zeros*
        w = pd.to_numeric(df_out["WITHDRAWAL"], errors="coerce").fillna(0)  # withdrawals (Dr)
        d = pd.to_numeric(df_out["DEPOSIT"],   errors="coerce").fillna(0)   # deposits   (Cr)

        # (1) Treat *leading* zeros as missing — common in HDFC page-1 extracts
        if b.notna().any() and (b != 0).any():
            # index of the first non-zero/non-NaN balance
            first_nz_idx = b.index[((b != 0) & (~b.isna()))][0]
            # convert any zeros above it to NaN so backfill will compute them
            head = b.iloc[:first_nz_idx]
            b.iloc[:first_nz_idx] = head.mask(head == 0)

        first_known = b.first_valid_index()  # index of first non-NaN balance
        if first_known is not None:
            # 1) Backfill upwards (for the first few rows that are blank/zero)
            bal = float(b.iloc[first_known])
            for r in range(first_known - 1, -1, -1):
                # Going backward: bal_prev = bal_next + withdrawal - deposit
                bal = round(bal + float(w.iloc[r]) - float(d.iloc[r]), 2)
                b.iloc[r] = bal

            # 2) Forward-fill gaps (rare) — also treat zeros as gaps
            bal = float(b.iloc[first_known])
            for r in range(first_known + 1, len(b)):
                if pd.isna(b.iloc[r]) or b.iloc[r] == 0:
                    # Going forward: bal_next = bal_prev - withdrawal + deposit
                    bal = round(bal - float(w.iloc[r]) + float(d.iloc[r]), 2)
                    b.iloc[r] = bal
                else:
                    bal = float(b.iloc[r])

            df_out["CL. BALANCE"] = b

    # the local balance delta, fix it (covers first txn after Opening Balance).
    prev_bal = None
    for r in range(len(df_out)):
        bal = df_out.at[r, "CL. BALANCE"]
        bal = None if bal == "" else float(bal)
        if prev_bal is not None and bal is not None:
            delta = round(bal - prev_bal, 2)
            w = float(df_out.at[r, "WITHDRAWAL"] or 0.0)
            d = float(df_out.at[r, "DEPOSIT"] or 0.0)
            if delta > 0 and w > 0 and d == 0:
                df_out.at[r, "WITHDRAWAL"], df_out.at[r, "DEPOSIT"] = 0.0, w
            elif delta < 0 and d > 0 and w == 0:
                df_out.at[r, "WITHDRAWAL"], df_out.at[r, "DEPOSIT"] = d, 0.0
        if bal is not None:
            prev_bal = bal

    return df_out

def _pack_narration(lead_desc: str, other_bits: list[str], ref_txt: str | None = None):
    lead = _clean_text(lead_desc or "")
    # keep only non-pure numbers in other bits (we’ll handle ref-ish separately)
    other_bits = [b for b in other_bits if not NUM_RX.fullmatch(b or "")]
    tail_parts = [b for b in other_bits if b]
    if ref_txt:
        tail_parts.append(_clean_text(ref_txt))

    tail = " ".join(tail_parts).strip()

    if not lead:
        return tail, ""  # everything into N1 if there is no lead

    # ➊ split if tail looks like a reference/id blob (digits, /, -, spaces; no letters)
    if tail and REFISH_TAIL_RX.fullmatch(tail):
        return lead, tail

    # ➋ split if tail has explicit markers (chq/ref/upi/imps/neft/utr)
    if tail and re.search(r"\b(chq|cheque|ref|utr|upi|imps|neft)\b", tail, re.I):
        return lead, tail

    # ➌ otherwise, merge into a single narration (keeps most banks tidy)
    merged = (f"{lead} {tail}".strip() if tail else lead)
    return merged, ""

def generic_auto(pdf_paths, passwords):
    all_rows = []
    bank = BANK_UNKNOWN
    acct = ""
    start = end = ""

    for path in pdf_paths:
        opened = False
        for pwd in (passwords or []) + [None]:
            try:
                with pdfplumber.open(path, password=pwd) as pdf:
                    if not pdf.pages:
                        continue

                    # --- read page-1 text FIRST (fix #1) ---
                    txt = pdf.pages[0].extract_text() or ""
                    # --- Try PNB column boxes FIRST (no heuristic gate) ---
                    pnb_boxes = None
                    for _pg in pdf.pages[:3]:
                        pnb_boxes = _pnb_column_boxes(_pg)
                        if pnb_boxes:
                            break
                    if pnb_boxes:
                        tx = _pnb_extract_with_boxes(pdf, pnb_boxes)
                        if not tx.empty:
                            all_rows.append(tx)
                            opened = True
                            break  # STOP so we don't fall back to the generic splitter

                    # naive bank/account gleaning from page 1 text
                    m = re.search(r"(Bank|Co\-?op|Credit Union|Sahakari).{0,40}", txt, re.I)
                    if m:
                        bank = (m.group(0) or BANK_UNKNOWN).strip()[:30]
                    m = re.search(r"(Account\s*(No\.?|Number)\s*[:\-]?\s*)(\d{6,18})", txt, re.I)
                    if m:
                        acct = m.group(3)
                    m = re.search(r"from\s+([0-9A-Za-z/.\-]+)\s+to\s+([0-9A-Za-z/.\-]+)", txt, re.I)
                    if m:
                        start = _parse_date(m.group(1))
                        end   = _parse_date(m.group(2))

                    # --- Canara special path (after txt is ready) ---
                    if _looks_canara(txt):
                        tx = _canara_extract(pdf)
                        if not tx.empty:
                            all_rows.append(tx)
                            opened = True
                        if opened:
                            break
                    # --- FORCE PNB path first (before any generic paths) ---
                    if _looks_pnb(txt):
                        # find boxes on first 3 pages
                        pnb_boxes = None
                        for _pg in pdf.pages[:3]:
                            pnb_boxes = _pnb_column_boxes(_pg)
                            if pnb_boxes:
                                break
                        # run the box extractor (will also work with base_boxes=None per page)
                        tx = _pnb_extract_with_boxes(pdf, pnb_boxes or {})
                        if not tx.empty:
                            all_rows.append(tx)
                            opened = True
                            # IMPORTANT: stop here so nothing later splits narration or modifies balance
                            break

                     # --- Try Union by column boxes FIRST (even if no textual hint) ---
                    union_boxes = None
                    for _pg in pdf.pages[:3]:
                        union_boxes = _union_column_boxes(_pg)
                        if union_boxes:
                            break
                    if union_boxes:
                        tx = _union_extract(pdf)
                        if not tx.empty:
                            all_rows.append(tx)
                            opened = True
                            break

                    # --- Or via textual heuristic ---
                    if not opened and _looks_union(txt):
                        tx = _union_extract(pdf)
                        if not tx.empty:
                            all_rows.append(tx)
                            opened = True
                            break


                    if opened:
                        # already handled by Canara path
                        pass
                    else:
                        added_any = False
                        for pg in pdf.pages:
                            page_cands = _extract_tables_with_variants(pg)
                            best_tbl = _pick_transaction_table(page_cands)   # choose a single candidate for THIS page
                            if not best_tbl:
                                continue

                            df = _ensure_dataframe(best_tbl)
                            if df.empty:
                                continue

                            header_idx, cats = _pick_header(df.values.tolist())
                            if header_idx is None:
                                header_idx = 0
                                cats = [_classify_header_cell(c) for c in df.iloc[0].tolist()]

                            tx = _normalize_rows(df, header_idx, cats)
                            if not tx.empty:
                                all_rows.append(tx)
                                added_any = True

                        if added_any:
                            opened = True

                        # ---- Fallback: text parse across pages ----
                        if not opened:
                            rows = []
                            for pg in pdf.pages:
                                rows.extend(_rows_from_text(pg))
                            if rows:
                                all_rows.append(pd.DataFrame(
                                    rows,
                                    columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"]
                                ))
                                opened = True

                # break the password loop once we parsed this file
                if opened:
                    break

            except Exception:
                continue

    if not all_rows:
        out = pd.DataFrame(columns=["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"])
    else:
        out = pd.concat(all_rows, ignore_index=True)
         # --- keep only txns within the statement date window (BOM fix) ---
        if out.shape[0] and start and end:
            try:
                s = pd.to_datetime(start, dayfirst=True, errors="coerce")
                e = pd.to_datetime(end,   dayfirst=True, errors="coerce")
                out["__d"] = pd.to_datetime(out["DATE"], dayfirst=True, errors="coerce")
                out = out[(out["__d"] >= s) & (out["__d"] <= e)].drop(columns="__d")
            except Exception:
                pass

      
        # --- final cleanup: remove ghost/summary rows ---
        if not out.empty:
            # stable sort by date so balance deltas are meaningful
            try:
                out["__d"] = pd.to_datetime(out["DATE"], dayfirst=True, errors="coerce")
                out = out.sort_values(["__d"], kind="mergesort").drop(columns="__d")
            except Exception:
                pass

            # drop all-zero amount rows (empty variant tables)
            out["__amt"] = out["WITHDRAWAL"].fillna(0).abs() + out["DEPOSIT"].fillna(0).abs()
            out = out[out["__amt"] > 0]

            # drop summary totals (amount present, no narration, no balance movement)
            out["__nlen"] = out["NARRATION 1"].astype(str).str.len() + out["NARRATION 2"].astype(str).str.len()
            prev = pd.to_numeric(out["CL. BALANCE"], errors="coerce").shift()
            curr = pd.to_numeric(out["CL. BALANCE"], errors="coerce")
            delta = (curr - prev).abs().fillna(0)
            out = out[~((out["__nlen"] < 3) & (out["__amt"] > 0) & (delta < 0.01))]

            out = out.drop(columns=["__amt", "__nlen"])

    account_row = [bank, acct, "", "", "", ""]
    headers     = ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"]

    if not out.empty:
        # capture current scan/page order (after your earlier mergesort)
        out["__seq"] = range(len(out))

        # prefer the version with more narration text
        out["__len"] = (
            out["NARRATION 1"].astype(str).str.len()
            + out["NARRATION 2"].astype(str).str.len()
        )

        # pick longest narration per unique txn, but keep original page order on ties
        out = (
            out.sort_values(["__len", "__seq"], ascending=[False, True])
            .drop_duplicates(
                subset=["DATE", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"],
                keep="first"
            )
        )

        # final stable chronological order; within the same day keep page order
        out["__d"] = pd.to_datetime(out["DATE"], dayfirst=True, errors="coerce")
        out = (
            out.sort_values(["__d", "__seq"], kind="mergesort")
            .drop(columns=["__len", "__seq", "__d"])
            .reset_index(drop=True)
        )

    result = [account_row, headers] + out.fillna("").values.tolist()
    return result


