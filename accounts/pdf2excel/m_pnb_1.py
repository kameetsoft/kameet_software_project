# # pdf2excel/m_pnb_1.py
# # -*- coding: utf-8 -*-
# """
# PNB extractor module with BOB-like API.

# Usage:
#     from pdf2excel.m_pnb_1 import pnb_1
#     tables = pnb_1([r"C:\path\to\PNB.pdf"], ["password1", "password2"])
#     # tables = [ [ [bank_name, account_no, "", "", "", ""],
#     #              ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#     #              [rows...]
#     #            ],
#     #            ... (one table per account number in all input PDFs)
#     #          ]
# """

# import re
# from typing import List, Tuple, Dict, Optional
# import pdfplumber
# from dateutil import parser as dtparse
# from dateutil.parser import ParserError

# bank_name = "PNB"


# # NEW (accepts dd-mm-yyyy, dd/mm/yyyy, dd MMM yyyy)
# DATE_ANCHOR_RX = re.compile(
#     r"\b([0-3]?\d)[-/\s](?:([0-1]?\d)|([A-Za-z]{3}))[-/\s]((?:19|20)?\d{2})\b"
# )

# # Support BOTH western (12,345,678) and Indian (12,34,56,789) groupings
# # and optional .decimals
# MONEY_RX = re.compile(
#     r'(?:\d{1,3}(?:,\d{3})+'           # western: 12,345 or 12,345,678
#     r'|\d{1,3}(?:,\d{2})+,\d{3}'       # Indian: 1,20,000 or 12,34,56,789
#     r'|\d+)'                           # plain integer
#     r'(?:\.\d{2})?'                    # optional .00
# )

# # Stricter version for BALANCE: must have comma-grouping OR decimals
# MONEY_BAL_RX = re.compile(
#     r'(?:\d{1,3}(?:,\d{3})+|\d{1,3}(?:,\d{2})+,\d{3}|\d+\.\d{2})'
# )



# # Allow us to ignore page headers/footers and table noise
# PAGE_TITLE_RX = re.compile(r"^\s*Account\s+Statement\b.*$", re.I)
# # PAGE_NO_RX = re.compile(r"^\s*Page\s+No\b", re.I)

# # Better (matches: "Page No", "PageNo", "Page : No.", with or without punctuation)
# PAGE_NO_RX = re.compile(r"\bPage\s*No\b|\bPage\s*:\s*No\b|\bPageNo\b", re.I)

# FOOTER_DROP_RX = re.compile(
#     r"(?:^|\s)(?:COMPUTER\s+GENERATED|AUTHENTICATION|PLEASE\s+MAINTAIN\s+MINIMUM|Abbreviations\s+are\s+as\s+under|Ret:|POSP:|QAB:)",
#     re.I,
# )

# # Short “BY CASH/TO SELF” rows sometimes stand alone without amounts; we merge them
# KEY_CASH_SELF_RX = re.compile(r"\b(?:BY\s+CASH|TO\s+SELF)\b", re.I)
# # 1) put this near the other regexes at the top of the file
# KEYWORD_PREFIX_RX = re.compile(
#     r"\b(?:NEFT(?:_IN|_OUT)?|UPI|IMPS|ATM|B01/|BY\s+CASH|TO\s+SELF|SMS\s+CHRG)\b",
#     re.I,
# )

# # Drop/trim common PNB footer/disclaimer lines
# FOOTER_DROP_RX = re.compile(
#     r"(?:^|\s)(?:COMPUTER\s+GENERATED|AUTHENTICATION|PLEASE\s+MAINTAIN\s+MINIMUM"
#     r"|Abbreviations\s+are\s+as\s+under|Ret:|POSP:|QAB:|LF\s*Chg|Stk\s*Stmt|POINT\s+OF\s+SALE)",
#     re.I,
# )


# # ignore words near bottom of page when building narration (footer band)
# FOOTER_BAND_FRAC = 0.925  # bottom 7.5% ignored for narration

# ROW_TOP_GUARD_PX = 12.0  
# DRCR_RX = re.compile(r'^(?:CR?|DR?)\.?$', re.I) # CR/DR tokens
# # Header cells to ignore if they slip into the first band
# HEADER_CELL_RX = re.compile(
#     r'^(?:TXN\.?\s*NO\.?|TXN\s*NO|TXN\s*DATE|DESCRIPTION|BRANCH\s*NAME|'
#     r'DR\.?\s*AMOUNT|DEBIT\s*AMOUNT|CR\.?\s*AMOUNT|CREDIT\s*AMOUNT|'
#     r'BALANCE|REMARKS)\s*$', re.I
# )

# FOOTER_START_RX = re.compile(
#     r"(Unless\s+constituent\s+notifies\s+the\s+bank"
#     r"|bank\s+immediately\s+of\s+any\s+discrepancy"   # ← add this
#     r"|ENT(?:ER)?IES\s+SHOWN\s+IN\s+THE\s+STATEMENT\s+OF\s+ACCOUNT"
#     r"|OFFICIAL\.?\s*PLEASE\s+DO\s+NOT\s+ACCEPT\s+STATEMENT\s+OF\s+ACCOUNT"
#     r"|OWN\s+INTEREST\s+NOT\s+TO\s+ISSUE"
#     r"|AVERAGE\s+BALANCE"
#     r"|TO\s+AVOID\s+LEVY\s+OF\s+CHARGES"
#     r"|QMS\s+forms"
#     r"|terms\s+and\s+conditions"
#     r"|Clg:\s*Clearing|ISO:|LF\s*Chg"
#     r"|PLEASE\s+DO\s+NOT\s+ACCEPT\s+ANY\s+MANUAL\s+ENTRY"
#     r"|PLEASE\s+ENSURE\s+THAT\s+ALL\s+THE\s+CHEQUE\s+LEAVES"
#     r"|CUSTOMERS\s+ARE\s+REQUESTED"
#     r"|Page\s*No)",
#     re.I
# )



# # Clean the 'NEFT_IN:null//' artifact
# # NEFT_NULL_RX = re.compile(r"\b(NEFT(?:_IN)?):\s*null\s*/+", re.I)
# NEFT_NULL_RX = re.compile(r"\b(NEFT(?:_IN)?):\s*null\s*/+", re.I)



# # ---------------- utility ----------------
# def _to_number(tok: str) -> Optional[float]:
#     if not tok:
#         return None
#     t = re.sub(r"[,\s]", "", str(tok))
#     try:
#         return float(t)
#     except Exception:
#         return None
    

# #

# def _fix_pnb_splits(s: str) -> str:
#     # If you want 100% fidelity, keep it truly no-op (except space collapse).
#     # If you still want the NEFT null fix, uncomment the next line.
#     # s = re.sub(r'\bNEFT(?:_IN)?\s*:\s*null\s*/+', 'NEFT_IN:', s, flags=re.I)
#     return re.sub(r'\s{2,}', ' ', s).strip()



# def _parse_date(s: str) -> str:
#     s = (s or "").strip()
#     if not s:
#         return ""
#     try:
#         d = dtparse.parse(s, dayfirst=True, fuzzy=True)
#         return d.strftime("%d-%m-%Y")
#     except (ParserError, ValueError, TypeError):
#         return s  # keep original if we can’t parse

# def _find_account_number(text: str) -> Optional[str]:
#     """
#     Sample header line in your PDF:
#       'Account Statement for Account Number 5989002100002291'
#     """
#     m = re.search(r"Account\s+Number\s+(\d{12,20})", text or "", re.I)
#     return m.group(1) if m else None

# # ------------- column detection for PNB -------------
# def _pnb_column_boxes(page) -> Dict[str, Tuple[float, float]]:
#     """
#     Detect columns via header centers:
#       Txn Date | Description | Dr Amount | Cr Amount | Balance
#     Return dict { 'date':(L,R), 'desc':(L,R), 'dr':(L,R), 'cr':(L,R), 'bal':(L,R) }
#     """
#     words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

#     # group by y
#     lines: Dict[float, list] = {}
#     for w in words:
#         y = round(w["top"], 1)
#         lines.setdefault(y, []).append(w)
#     for y in lines:
#         lines[y].sort(key=lambda z: z["x0"])

#     centers: Dict[str, float] = {}

#     def mark(name: str, ws: List[dict]):
#         if not ws:
#             return
#         xm = sum((w["x0"] + w["x1"]) / 2.0 for w in ws) / len(ws)
#         centers[name] = xm

#     for _, ws in lines.items():
#         low = [(i, (w["text"] or "").strip().lower()) for i, w in enumerate(ws)]
#         for i, t in low:
#             # "Txn Date"
#             if t == "txn" and i + 1 < len(low) and low[i + 1][1].startswith("date"):
#                 mark("date", [ws[i], ws[i + 1]])
#             # "Description"
#             if "description" in t:
#                 mark("desc", [ws[i]])
#             # "Balance"
#             if "balance" in t:
#                 mark("bal", [ws[i]])
#             # "Dr Amount"/"Cr Amount" or "Debit Amount"/"Credit Amount"
#             if t in ("dr", "debit") and i + 1 < len(low) and "amount" in low[i + 1][1]:
#                 mark("dr", [ws[i], ws[i + 1]])
#             if t in ("cr", "credit") and i + 1 < len(low) and "amount" in low[i + 1][1]:
#                 mark("cr", [ws[i], ws[i + 1]])

#     required = {"date", "desc", "bal"}
#     if not required.issubset(centers.keys()):
#         return {}

#     cols_sorted = sorted(centers.items(), key=lambda kv: kv[1])
#     xs = [0.0] + [(a[1] + b[1]) / 2.0 for a, b in zip(cols_sorted, cols_sorted[1:])] + [page.width]

#     boxes: Dict[str, Tuple[float, float]] = {}
#     for (name, xm), L, R in zip(cols_sorted, xs, xs[1:]):
#         boxes[name] = (L, R)

#     # If DR/CR missing, split between DESC and BAL
#     if "dr" not in boxes or "cr" not in boxes:
#         L = boxes.get("desc", (0, 0))[1]
#         R = boxes.get("bal", (page.width, page.width))[0]
#         if R > L:
#             mid = (L + R) / 2.0
#             boxes["dr"] = (L, mid)
#             boxes["cr"] = (mid, R)

#     return boxes

# def _last_num_in_col(colname: str, band: List[dict]) -> Optional[float]:
#     from collections import defaultdict

#     lines = defaultdict(list)
#     for w in band:
#         if w.get("col") != colname:
#             continue
#         txt = (w.get("text") or "")
#         # DROP page/header/footer noise
#         if PAGE_TITLE_RX.search(txt) or PAGE_NO_RX.search(txt) or FOOTER_DROP_RX.search(txt) or HEADER_CELL_RX.search(txt):
#             continue
#         lines[round(w["top"], 1)].append(txt)

#     picked = None
#     for y in sorted(lines.keys()):
#         line = " ".join(lines[y])
#         # Strip any DR/CR label tokens
#         line = re.sub(r"\b(?:CR?|DR?)\.?/?\b", "", line, flags=re.I)

#         # If a Page No slips through at line level, skip this line entirely
#         if PAGE_NO_RX.search(line):
#             continue

#         nums = [m.group(0) for m in MONEY_RX.finditer(line)]
#         if nums:
#             tok = nums[-1]
#             # accept only money-like tokens (comma or decimal) to avoid page counts etc.
#             if ("," in tok) or ("." in tok):
#                 picked = _to_number(tok)
#     return picked


# # --- smart join to keep '/', '//' and hyphen-wraps intact ---
# def _smart_join(tokens):
#     out = []
#     for i, t in enumerate(tokens):
#         if not t:
#             continue
#         if not out:
#             out.append(t)
#             continue
#         prev = out[-1]

#         # join around '/' or '//' without spaces
#         if prev.endswith(("/", "//")) or t.startswith(("/", "//")):
#             out[-1] = prev + t
#             continue

#         # hyphenation fix: "LIMI" "F"  -> "LIMIF" (we’ll normalize later)
#         if prev.endswith(("-", "—", "–")):
#             out[-1] = prev.rstrip("-—–") + t
#             continue

#         out.append(" " + t)

#     s = "".join(out)

#     # # known split/glue cleanups seen in PNB PDFs
#     # s = re.sub(r"\bPRIVAT\s*E\s+LI\b", "PRIVATE LIMITED", s, flags=re.I)
#     # s = re.sub(r"\bPRIVAT\s*E\b", "PRIVATE", s, flags=re.I)
#     # s = re.sub(r"\bLIMI\s*F\b", "LIMITED", s, flags=re.I)

#     # normalize NEFT_IN:null// -> NEFT_IN:
#     s = re.sub(r"\bNEFT(?:_IN)?\s*:\s*null\s*/+", "NEFT_IN:", s, flags=re.I)

#     # compact multiple spaces
#     s = re.sub(r"\s{2,}", " ", s).strip()
#     return s

# def _amountish_token(t: str) -> bool:
#     t = (t or "").strip()
#     return bool(DRCR_RX.fullmatch(t) or MONEY_RX.fullmatch(t))
# def _join_as_pdf(tokens):
#     """Join tokens exactly as they appear on the page (preserve // joins)."""
#     out = []
#     for t in (tok.strip() for tok in tokens):
#         if not t:
#             continue
#         if out and (out[-1].endswith(("/", "//")) or t.startswith(("/", "//"))):
#             out[-1] = out[-1] + t          # keep slashes tight
#         else:
#             out.append(t if not out else " " + t)
#     return "".join(out).strip()


# def _balance_text_value_sign(band: List[dict]) -> Tuple[Optional[str], Optional[float], int]:
#     """
#     Return (printed_text_numeric, numeric_value, sign)
#     Sign is -1 if 'Dr' label exists in the Balance column tokens, else +1.
#     """
#     from collections import defaultdict

#     col_words = [
#         (round(w["top"], 1), (w.get("text") or ""))
#         for w in band
#         if w.get("col") == "bal"
#     ]
#     if not col_words:
#         return None, None, +1

#     lines = defaultdict(list)
#     for y, txt in col_words:
#         # DROP page/header/footer noise in BALANCE as well
#         if PAGE_TITLE_RX.search(txt) or PAGE_NO_RX.search(txt) or FOOTER_DROP_RX.search(txt) or HEADER_CELL_RX.search(txt):
#             continue
#         lines[y].append(txt)

#     printed = None
#     seen_dr = False
#     seen_cr = False

#     for y in sorted(lines.keys()):
#         line = " ".join(lines[y]).strip()

#         # If this balance line contains a Page No footer/header, ignore this line
#         if PAGE_NO_RX.search(line):
#             continue

#         if re.search(r"\bDr\.?\b", line, re.I):
#             seen_dr = True
#         if re.search(r"\bCr\.?\b", line, re.I):
#             seen_cr = True

#         # remove DR/CR label to read numeric
#         line_clean = re.sub(r"\b(Cr|Dr)\.?\b", "", line, flags=re.I)

#         # Only consider tokens that look like money (comma or decimal)
#         # nums = [m.group(0) for m in MONEY_RX.finditer(line_clean)]
#         nums = [m.group(0) for m in MONEY_BAL_RX.finditer(line_clean)]

#         nums = [t for t in nums if ("," in t) or ("." in t)]  # <- drop plain integers like "5"
#         if nums:
#             printed = nums[-1]

#     if printed is None:
#         return None, None, +1

#     val = _to_number(printed)
#     sign = -1 if (seen_dr and not seen_cr) else +1
#     return printed, (None if val is None else sign * val), sign



# def _extract_rows_from_page(page, last_balance: Optional[float], base_boxes: Optional[Dict[str, Tuple[float, float]]] = None) -> Tuple[List[list], Optional[float]]:
#     """
#     Build rows: [DATE, N1, N2, WITHDRAWAL, DEPOSIT, CL BALANCE]
#     Uses header boxes from this page or falls back to base_boxes.
#     """
#     boxes = _pnb_column_boxes(page) or base_boxes
#     if not boxes:
#         return [], last_balance

#     words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

#     # tag words with detected column
#     for w in words:
#         xm = (w["x0"] + w["x1"]) / 2.0
#         w["col"] = None
#         for name, (L, R) in boxes.items():
#             if L <= xm <= R:
#                 w["col"] = name
#                 break

#     # date anchors
#     anchors = [w for w in words if w.get("col") == "date" and DATE_ANCHOR_RX.search(w.get("text") or "")]
#     anchors.sort(key=lambda w: w["top"])
#     if not anchors:
#         return [], last_balance

#     # vertical bands between midpoints
#     cuts = [0.0] + [(anchors[i]["top"] + anchors[i + 1]["top"]) / 2.0 for i in range(len(anchors) - 1)] + [page.height + 1]

#     out_rows: List[list] = []
#     prev_balance = last_balance

#     for idx, a in enumerate(anchors):
#         y_top = cuts[idx]
#         y_bot = cuts[idx + 1]
#         band = [w for w in words if y_top <= w["top"] < y_bot]
#         row_top_guard = max(0.0, a["top"] - ROW_TOP_GUARD_PX)

#         # ------ DATE ------
#         date_txt = None
#         for w in sorted([w for w in band if w.get("col") == "date"], key=lambda z: z["x0"]):
#             m = DATE_ANCHOR_RX.search(w.get("text") or "")
#             if m:
#                 date_txt = m.group(0)
#                 break
#         date_out = _parse_date(date_txt or "")
    
#         # ------ NARRATION (Description column) ------
#         # Use EXACT Description column window and keep only those tokens.
#         desc_L, desc_R = boxes["desc"]
#         top_guard = max(y_top, a["top"] - ROW_TOP_GUARD_PX)
#         is_last_band_on_page = (idx == len(anchors) - 1)
#         bottom_cut = min(page.height * FOOTER_BAND_FRAC, y_bot - 1.0)

#         def _in_desc_span(w):
#             xm = (w["x0"] + w["x1"]) / 2.0
#             return desc_L <= xm <= desc_R

#         # Accept ONLY description-column words (plus untagged words inside the span)
#         cand = [
#             w for w in band
#             if (w.get("col") == "desc" or (w.get("col") is None and _in_desc_span(w)))
#             and top_guard <= w["top"] < bottom_cut
#         ]
#         cand = sorted(cand, key=lambda z: (round(z["top"], 1), z["x0"]))

#         parts = []
#         for w in cand:
#             t = (w.get("text") or "").strip()
#             if not t or t in {"-", "–", "—"}:
#                 continue
#             # Drop obvious header/footer/header-cell leakage only
#             if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_RX.search(t) or HEADER_CELL_RX.search(t):
#                 continue
#             parts.append(t)

#         narration = _join_as_pdf(parts)

#         # Last row on page: hard-clip if a footer paragraph still sneaks in
#         if is_last_band_on_page:
#             m = FOOTER_START_RX.search(narration)
#             if m:
#                 narration = narration[:m.start()].rstrip(" -–—•·")


#         parts = []
#         for w in cand:
#             t = (w.get("text") or "").strip()
#             if not t or t in {"-", "–", "—"}:
#                 continue
#             # keep within our vertical guard
#             if w["top"] > bottom_cut:
#                 continue
#             # drop headers/footers/noise
#             if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_RX.search(t) or HEADER_CELL_RX.search(t):
#                 continue

#             # drop DR/CR labels and any money-like token *anywhere*
#             if DRCR_RX.fullmatch(t) or MONEY_BAL_RX.fullmatch(t):
#                 continue

#             # drop pure date-looking tokens that leaked from the Date col
#             if DATE_ANCHOR_RX.fullmatch(t):
#                 continue

#             parts.append(t)

#         # 1) smart join preserves "/", "//" and fixes hyphen wraps
#         narration = _smart_join(parts)

#         # strip leading bullet/dash
#         narration = re.sub(r"^\s*[-–—•·]+\s*", "", narration)

#         # safety drops
#         narration = PAGE_TITLE_RX.sub("", narration)

#         # 2) targeted PNB glue/cleanup
#         narration = _fix_pnb_splits(narration)
#         # clip any footer phrase if it sneaks in
#         if is_last_band_on_page:
#             m = FOOTER_START_RX.search(narration)
#             if m:
#                 narration = narration[:m.start()].rstrip(" -–—•·")

#         # ---- INSERT HERE ----
#         # (existing stricter prefix safety block) ...
#         if (
#             narration
#             and not KEYWORD_PREFIX_RX.search(narration)
#             and not re.match(r"^(?:TO\s+SELF|BY\s+CASH)\b", narration, re.I)
#         ):
#             pref = []
#             for w in sorted(band, key=lambda z: (round(z["top"], 1), z["x0"])):
#                 t = (w.get("text") or "").strip()
#                 if not t:
#                     continue
#                 if w.get("col") in ("dr", "cr", "bal", "date"):
#                     continue
#                 if not _in_desc_span(w):
#                     continue
#                 if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_RX.search(t) or HEADER_CELL_RX.search(t):
#                     continue
#                 if KEYWORD_PREFIX_RX.search(t):
#                     pref.append(t)
#             if pref:
#                 narration = _smart_join(pref + [narration])
#                 narration = _fix_pnb_splits(narration)
#         # ---- INSERT ENDS ----

#         # ------ AMOUNTS ------
#         dr = _last_num_in_col("dr", band) or 0.0

  

#         # 3) Word glue for common splits across wraps (PNB PDFs)
#                # more glue / cleanups seen in your samples
#         narration = re.sub(r"\bPRIVAT\s*E\s+LI\b", "PRIVATE LIMITED", narration, flags=re.I)
#         narration = re.sub(r"\bPRIVAT\s*E\b", "PRIVATE", narration, flags=re.I)  # fallback
#         narration = re.sub(r"\bNEFT\s*[_-]?\s*IN\s*:", "NEFT_IN:", narration, flags=re.I)

#         # ensure we remove the 'NEFT_IN:null//' artifact robustly
#         narration = re.sub(r"\bNEFT(?:_IN)?\s*:\s*null\s*/+", "NEFT_IN:", narration, flags=re.I)

#         # re-normalize whitespace
#         narration = re.sub(r"\s{2,}", " ", narration).strip()


#         # ------ AMOUNTS ------
#         # dr = _last_num_in_col("dr", band) or 0.0
#         cr = _last_num_in_col("cr", band) or 0.0
#         if dr and cr:
#             # If both present (rare), prefer the larger and zero the other
#             if abs(dr) >= abs(cr):
#                 cr = 0.0
#             else:
#                 dr = 0.0

#         # ------ BALANCE ------
#         bal_txt, bal_val, bal_sign = _balance_text_value_sign(band)

#         # Synthesize balance if missing but we have previous balance
#         if bal_val is None and prev_balance is not None:
#             bal_val = round(prev_balance - float(dr or 0.0) + float(cr or 0.0), 2)

#         # If no explicit DR/CR in row but balance changed, infer side from delta
#         if (not dr and not cr) and (bal_val is not None) and (prev_balance is not None):
#             delta = round(bal_val - prev_balance, 2)
#             if delta > 0:
#                 cr = abs(delta)
#             elif delta < 0:
#                 dr = abs(delta)

#         # Update prev balance if computable
#         if bal_val is not None:
#             prev_balance = float(bal_val)

#         out_rows.append([
#             date_out,
#             narration,
#             "",
#             float(dr or 0.0),
#             float(cr or 0.0),
#             float(bal_val) if bal_val is not None else ""
#         ])

   
#         # POST: merge isolated BY CASH/TO SELF rows without amounts into the neighbor
#     merged: List[list] = []
#     i = 0
#     while i < len(out_rows):
#         date, n1, n2, wdl, dep, bal = out_rows[i]
#         has_amt = bool((wdl and float(wdl) != 0.0) or (dep and float(dep) != 0.0))

#         if KEY_CASH_SELF_RX.search(str(n1 or "")) and not has_amt:
#             # Prefer merging FORWARD if the next row has the actual details/amounts (very common in PNB)
#             can_merge_forward = False
#             if i + 1 < len(out_rows):
#                 d2, n1b, n2b, wdl2, dep2, bal2 = out_rows[i + 1]
#                 has_amt_next = bool((wdl2 and float(wdl2) != 0.0) or (dep2 and float(dep2) != 0.0))
#                 # same date or blank date in one of them → treat as a paired line
#                 same_day = (str(d2).strip() == str(date).strip()) or (not str(d2).strip()) or (not str(date).strip())
#                 if has_amt_next and same_day:
#                     # merge "TO SELF" text into the next row's narration
#                     out_rows[i + 1][1] = (str(n1).strip() + " " + str(n1b).strip()).strip()
#                     # if current row shows a balance but next doesn't, carry it
#                     if bal != "" and out_rows[i + 1][5] == "":
#                         out_rows[i + 1][5] = bal
#                     can_merge_forward = True

#             if can_merge_forward:
#                 i += 1  # skip current; the next row now contains the merged narration
#                 continue

#             # Otherwise, if there is a previous merged row with amounts, merge backward
#             if merged:
#                 prev = merged[-1]
#                 has_amt_prev = bool((prev[3] and float(prev[3]) != 0.0) or (prev[4] and float(prev[4]) != 0.0))
#                 if has_amt_prev:
#                     prev[1] = (str(prev[1]).strip() + " " + str(n1).strip()).strip()
#                     if bal != "":
#                         prev[5] = bal
#                     i += 1
#                     continue

#             # If we can’t confidently merge, keep the row as-is
#             merged.append(out_rows[i])
#             i += 1
#             continue

#         # normal row → keep
#         merged.append(out_rows[i])
#         i += 1

#     out_rows = merged


#     return merged, prev_balance


# def _extract_pnb(pdf: pdfplumber.PDF) -> List[list]:
#     rows: List[list] = []
#     last_balance = None

#     base_boxes: Optional[Dict[str, Tuple[float, float]]] = None
#     # try to capture boxes from the first page that has headers
#     for p in pdf.pages:
#         base_boxes = _pnb_column_boxes(p)
#         if base_boxes:
#             break

#     for page in pdf.pages:
#         page_rows, last_balance = _extract_rows_from_page(page, last_balance, base_boxes)
#         rows.extend(page_rows)

#     return rows


# # ------------- public API (BOB-like) -------------
# def pnb_1(pdf_paths: List[str], passwords: List[str]) -> List[List[List]]:
#     """
#     Parameters
#     ----------
#     pdf_paths : list[str]
#         One or more PNB statement PDFs.
#     passwords : list[str]
#         Candidate passwords to try (filename, phone, etc.). None will also be tried.

#     Returns
#     -------
#     data_table : list
#         One entry per (bank, account) with:
#           [
#             [bank_name, account_number, "", "", "", ""],
#             ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
#             [rows...]
#           ]
#     """
#     data_table: List[List[List]] = []

#     for pdf_path in pdf_paths:
#         account_tables: List[List[List]] = []
#         account_numbers: List[str] = []
#         extracted_rows: Optional[List[list]] = None
#         acc_in_this_pdf: Optional[str] = None

#         # try passwords + None
#         for pwd in (passwords or []) + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=pwd) as pdf:
#                     if not pdf.pages:
#                         break

#                     # detect account number anywhere (first page preferred)
#                     first_text = pdf.pages[0].extract_text() or ""
#                     acc_in_this_pdf = _find_account_number(first_text)
#                     if not acc_in_this_pdf:
#                         # fallback: search whole doc text (rare)
#                         whole = "\n".join([(p.extract_text() or "") for p in pdf.pages[:3]])
#                         acc_in_this_pdf = _find_account_number(whole)

#                     # extract rows
#                     extracted_rows = _extract_pnb(pdf)
#                 break  # success
#             except Exception:
#                 continue

#         if not extracted_rows:
#             # either password failed or pdf empty — skip gracefully
#             continue

#         # format rows like your BOB module
#         table_rows: List[List] = []
#         for r in extracted_rows:
#             date, n1, n2, wdl, dep, bal = r

#             # normalize date
#             date = _parse_date(date)

#             # clean narration: drop accidental page-title fragments
#             n1 = PAGE_TITLE_RX.sub("", str(n1 or "")).strip()

#             # numeric enforcement (like your BOB formatter)
#             wdl = float(wdl or 0.0)
#             dep = float(dep or 0.0)

#             # balance already numeric or "", keep numeric for consistency
#             if bal == "":
#                 bal_out = ""
#             else:
#                 try:
#                     bal_out = float(bal)
#                 except Exception:
#                     num = _to_number(str(bal))
#                     bal_out = float(num) if num is not None else ""

#             table_rows.append([date, n1, n2, wdl, dep, bal_out])

#         # account grouping (one account per PNB file in practice)
#         account_no = acc_in_this_pdf or "UNKNOWN"
#         account_header = [bank_name, account_no, "", "", "", ""]
#         headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

#         # Merge into existing table for same account across multiple PDFs
#         placed = False
#         for idx, existing_table in enumerate(data_table):
#             if existing_table and existing_table[0][1] == account_no:
#                 data_table[idx].extend(table_rows)
#                 placed = True
#                 break

#         if not placed:
#             data_table.append([account_header, headers] + table_rows)

#     return data_table


# # Optional quick CLI test (adjust paths/passwords)
# if __name__ == "__main__":
#     demo_files = [r"E:\PDFs\PNB\sample.pdf"]  # change me
#     demo_pwds = ["1234", "password"]
#     out = pnb_1(demo_files, demo_pwds)
#     for t in out:
#         print(f"Account: {t[0][1]}  Rows: {max(0, len(t)-2)}")



# pdf2excel/m_pnb_1.py
# -*- coding: utf-8 -*-
"""
PNB extractor module with BOB-like API.

Usage:
    from pdf2excel.m_pnb_1 import pnb_1
    tables = pnb_1([r"C:\path\to\PNB.pdf"], ["password1", "password2"])
    -> [
         [
           ["PNB", "5989002100002291", "", "", "", ""],
           ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
           ["23-06-2025","NEFT_IN:05YESPH5 1740024014YESB0001//YESBN120250 62300138726/PHONEPE PRIVATE LIMI F","", "0.00","6752.76","31,581.72"],
           ...
         ]
       ]
"""

import re
from typing import List, Tuple, Dict, Optional
import pdfplumber
from dateutil import parser as dtparse
from dateutil.parser import ParserError

bank_name = "PNB"

# ---------------- regex helpers (from your common code, adapted) ----------------
# HEAD_SCAN_PX = 18.0

# HEAD_SCAN_PX = 36.0          # was 18.0; ordinary rows
HEAD_SCAN_PX = 72.0
HEAD_SCAN_PX_FIRST = 80.0  
BAD_INLINE_RX = re.compile(r"(?i)^\s*B\d{1,3}/YESBN\d+.*")

# date in dd-mm-yyyy / dd/mm/yyyy / dd MMM yyyy
DATE_ANCHOR_RX = re.compile(r"\b([0-3]?\d)[-/\s](?:([0-1]?\d)|([A-Za-z]{3}))[-/\s]((?:19|20)?\d{2})\b")

# Accept ONLY tokens that look like money (have comma grouping or decimal point)
# AMT_ONLY_RX = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+\.\d{2}|\d{1,3}(?:,\d{2})+,\d{3})")
AMT_ONLY_RX = re.compile(r'''(?x)
    (?:\d{1,3}(?:,(?:\d{3}|\d{2}))+(?:\.\d{2})?  # 8,606 or 1,35,519 or with .00
    | \d+\.\d{2})                                # 158.00, 24.78 (no commas)
''')
# a row that is only a channel prefix (noise if it has no amounts)
BARE_PREFIX_RX = re.compile(
    r"^(?:NEFT(?:\s*[_-]?\s*IN)?|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER):?$",
    re.I
)
# Tail anchors we want to keep when a line collapses to a bare prefix
TAIL_ANCHOR_RX = re.compile(r"""(?xi)
    (?:NEFT/\S.*)                              # explicit NEFT/...
  | (?:YESBN\d+\S.*)                           # YES Bank UTR chunk
  | (?:UTIBN\d+\S.*|ICICN\d+\S.*|HDFCN\d+\S.*) # other bank codes occasionally seen
  | (?:[A-Z]{3,}\d{6,}\S.*)                    # generic CODE+digits fallback
""")

# Page chrome / header / footer lines
PAGE_TITLE_RX = re.compile(r"^\s*Account\s+Statement\b.*$", re.I)
PAGE_NO_RX    = re.compile(r"\bPage\s*No\b|\bPage\s*:\s*No\b|\bPageNo\b|\bPage\s+\d+(?:\s*of\s*\d+)?\b", re.I)

# Description-band header noise that sometimes leaks (loose)
DESC_HEADER_LINE_RX = re.compile(r"""(?xi)
    ^\s*(account\s+statement|statement\s+period|customer\s+details|branch\s+name|
         description\s+branch\s+name|txn\.?\s*no\.?|kims\s*remarks|cheque\s*no\.?)\b
""")

# Multi-word footer lines to drop if they sneak in
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

# Very light, known footer paragraph starter detection (for last row on page)
# FOOTER_START_RX = re.compile(
#     r"(Unless\s+constituent\s+notifies|customers\s+are\s+requested|computer\s+generated|terms\s+and\s+conditions|Page\s*No)",
#     re.I
# )
# Replace your FOOTER_START_RX with this wider version
FOOTER_START_RX = re.compile(r"""(?xi)
    (?:Unless \s+ constituent \s+ notifies) |
    (?:customers \s+ are \s+ requested) |
    (?:computer \s+ generated) |
    (?:terms \s+ and \s+ conditions) |
    (?:Page \s* No) |
    (?:GENERATED \s+ (?:STATEMENT|ENTERI?ES) \s+ SHOWN) |
    (?:DO \s+ NOT \s+ REQUIRE \s+ ANY \s+ INITIAL) |
    (?:PLEASE \s+ DO \s+ NOT \s+ ACCEPT \s+ ANY \s+ MANUAL \s+ ENTRY) |
    (?:MINIMUM \s+ AVERAGE \s+ BALANCE) |
    (?:CHEQUES \s+ CAN \s+ BE \s+ RETURNED) |
    (?:the \s+ bank \s+ immediately)        # catches "the bank immediately of any discrepancy ..."
""")

CHEQUE_NO_RX = re.compile(r"^\d{5,9}$")
# Short rows we sometimes merge
KEY_CASH_SELF_RX = re.compile(r"\b(?:BY\s+CASH|TO\s+SELF)\b", re.I)

# Fix known artifact: NEFT_IN:null//
NEFT_NULL_RX = re.compile(r"\b(NEFT(?:_IN)?):\s*null\s*/+", re.I)
# Single header cells that sometimes leak into the first row of a page
HEADER_CELL_RX = re.compile(r"""(?ix)
^(?:txn\.?|date|description|branch|name|cheque|no\.?|dr|cr|debit|credit|amount|balance|kims|remarks)$
""")

# DR/CR labels
DRCR_RX = re.compile(r"^(?:CR?|DR?)\.?/?$", re.I)

# PREFIX_START_RX = re.compile(r"^(NEFT(?:[_-]?IN)?|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER|BY|TO)\b", re.I)
PREFIX_START_RX = re.compile(
    r"^(?:NEFT(?:\s*[_-]?\s*IN)?|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER|TO\s+SELF|BY\s+CASH)\b",
    re.I
)

# add this near the other globals (used later for scanning inside a string)
PFX_TOKEN_RX = re.compile(
    r"(?:NEFT(?:\s*[_-]?\s*IN)?|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER|TO\s+SELF|BY\s+CASH)",
    re.I
)
TXNNO_RX = re.compile(r"^[Ss]\d{6,}$")

def _normalize_narration(n: str) -> str:
    if not n:
        return ""
    n = re.sub(r"\s+", " ", n).strip()

    # strip any leading run of header cells that slipped in
    n = re.sub(
        r"(?i)^(?:txn\.?|date|description|branch|name|cheque|no\.?|dr|cr|debit|credit|amount|balance|kims|remarks)"
        r"(?:\s+(?:txn\.?|date|description|branch|name|cheque|no\.?|dr|cr|debit|credit|amount|balance|kims|remarks))*\s+",
        "",
        n,
    )

    # --- SAFE two-prefix handling ---
    # Keep valid "NEFT_IN: NEFT/..." lines intact (also tolerates 'NEFT IN' or 'NEFT-IN').
    hits = list(PFX_TOKEN_RX.finditer(n))
    if len(hits) >= 2:
        first_part  = n[:hits[1].start()]
        # n = n[:hits[1].start()].rstrip()
        second_part = n[hits[1].start():]
        F = first_part.upper()
        S = second_part.upper().lstrip()
        neft_in_first = re.search(r"NEFT\s*[_-]?\s*IN", F) is not None
        starts_with_neft_slash = S.startswith("NEFT/")
        if not (neft_in_first and starts_with_neft_slash):
            # in all other cases, cut at the second prefix
            n = first_part.rstrip()

    # drop a long leading number that bled from previous row (only for CASH/SELF)
    n = re.sub(r"^\d{6,}\s+(?=\b(?:BY\s+CASH|TO\s+SELF)\b)", "", n, flags=re.I)

    # BY CASH -> keep only BY CASH
    if re.search(r"\bBY\s+CASH\b", n, flags=re.I):
        return "BY CASH"

    # TO SELF -> keep 'TO SELF' (+ optional short id)
    m = re.search(r"(?i)\bTO\s+SELF\b(?:\s*[-:]\s*(\d{5,9}))?", n)
    if m:
        return "TO SELF" + (f" - {m.group(1)}" if m.group(1) else "")

    return n

def _to_number(tok: str) -> Optional[float]:
    if not tok:
        return None
    t = re.sub(r"[,\s]", "", str(tok))
    try:
        return float(t)
    except Exception:
        return None

def _parse_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        d = dtparse.parse(s, dayfirst=True, fuzzy=True)
        return d.strftime("%d-%m-%Y")
    except (ParserError, ValueError, TypeError):
        return s

def _find_account_number(text: str) -> Optional[str]:
    m = re.search(r"Account\s+Number\s+(\d{12,20})", text or "", re.I)
    return m.group(1) if m else None

def _join_as_pdf(tokens: List[str]) -> str:
    """
    Join tokens with PDF-like rules: keep '/' and '//' tight, otherwise single space.
    """
    out: List[str] = []
    for t in (tok.strip() for tok in tokens):
        if not t:
            continue
        if out and (out[-1].endswith(("/", "//")) or t.startswith(("/", "//"))):
            out[-1] = out[-1] + t
        else:
            out.append(t if not out else " " + t)
    return "".join(out).strip()

def _scan_tail_from_band(band: list, narr_L: float, bal_left: float) -> str:
    """
    Build a loose, line-like text from the row band and extract a 'tail'
    that typically follows NEFT_IN:. Keeps slashes tight and ignores amounts/dates.
    """
    # collect tokens broadly from description corridor (and a bit left for wraps)
    tokens = []
    for w in band:
        if (w["x1"] > (narr_L - 200.0)) and (w["x0"] < bal_left - 1.0):
            t = (w.get("text") or "").strip()
            if not t:
                continue
            if AMT_ONLY_RX.fullmatch(t.replace(" ", "")):  # ignore pure numbers of money
                continue
            if DATE_ANCHOR_RX.fullmatch(t) or DRCR_RX.fullmatch(t) or TXNNO_RX.fullmatch(t):
                continue
            if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_LINE_RX.search(t) or DESC_HEADER_LINE_RX.search(t):
                continue
            tokens.append(t)
    line = _join_as_pdf(tokens)
    # common cleanup: collapse "NEFT_IN:null//" -> "NEFT_IN:" but keep what follows
    line = NEFT_NULL_RX.sub(r"\1:", line)
    m = TAIL_ANCHOR_RX.search(line)
    return m.group(0).strip() if m else ""

# ---------------- column detection (your robust header-finder) ----------------

def _pnb_column_boxes(page) -> Dict[str, Tuple[float, float]]:
    """
    Find PNB columns by the header band that contains:
      Txn Date | Description | Dr Amount | Cr Amount | Balance
    Returns {name: (xL, xR)} or {}.
    """
    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

    # collect by y lines
    lines: Dict[float, list] = {}
    for w in words:
        y = round(w["top"], 1)
        lines.setdefault(y, []).append(w)
    for y in lines:
        lines[y].sort(key=lambda z: z["x0"])

    centers: Dict[str, float] = {}

    def mark(name: str, ws: List[dict]):
        if not ws:
            return
        xm = sum((w["x0"] + w["x1"]) / 2.0 for w in ws) / len(ws)
        centers[name] = xm

    for _, ws in lines.items():
        low = [(i, (w["text"] or "").strip().lower()) for i, w in enumerate(ws)]
        for i, t in low:
            if t == "txn" and i + 1 < len(low) and low[i + 1][1].startswith("date"):
                mark("date", [ws[i], ws[i + 1]])
            if "description" in t:
                mark("desc", [ws[i]])
            if "balance" in t:
                mark("bal", [ws[i]])
            if t == "dr" and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("dr", [ws[i], ws[i + 1]])
            if t == "cr" and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("cr", [ws[i], ws[i + 1]])
            if "debit" in t and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("dr", [ws[i], ws[i + 1]])
            if "credit" in t and i + 1 < len(low) and "amount" in low[i + 1][1]:
                mark("cr", [ws[i], ws[i + 1]])

    required = {"date", "desc", "bal"}
    if not required.issubset(centers.keys()):
        return {}

    cols_sorted = sorted(centers.items(), key=lambda kv: kv[1])
    xs = [0.0] + [(a[1] + b[1]) / 2.0 for a, b in zip(cols_sorted, cols_sorted[1:])] + [page.width]

    boxes: Dict[str, Tuple[float, float]] = {}
    for (name, xm), L, R in zip(cols_sorted, xs, xs[1:]):
        boxes[name] = (L, R)

    # if dr/cr are missing, split the gap between desc and balance
    if "dr" not in boxes or "cr" not in boxes:
        L = boxes.get("desc", (0, 0))[1]
        R = boxes.get("bal", (page.width, page.width))[0]
        if R > L:
            mid = (L + R) / 2.0
            boxes["dr"] = (L, mid)
            boxes["cr"] = (mid, R)

    return boxes


# ---------------- per-row helpers ----------------

def _last_num_in_col(colname: str, band: List[dict]) -> Optional[float]:
    """
    Return the LAST money-like token from a named column inside this row band.
    Only accepts tokens with commas or a decimal point.
    """
    from collections import defaultdict
    lines = defaultdict(list)
    for w in band:
        if w.get("col") != colname:
            continue
        txt = (w.get("text") or "")
        if PAGE_TITLE_RX.search(txt) or PAGE_NO_RX.search(txt) or FOOTER_DROP_LINE_RX.search(txt):
            continue
        lines[round(w["top"], 1)].append(txt)

    for y in sorted(lines.keys()):
        line = " ".join(lines[y])
        # strip DR/CR then look for numbers
        line = re.sub(r"\b(CR?|DR?)\.?/?\b", "", line, flags=re.I)
        nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
        if nums:
            val = _to_number(nums[-1])
            if val is not None:
                return val
    return None

def _balance_text_and_val(band: List[dict]) -> Tuple[Optional[str], Optional[float]]:
    """
    Read numeric text from Balance column (ignore Dr/Cr label), return (printed, value).
    """
    from collections import defaultdict
    col_words = [(round(w["top"], 1), (w.get("text") or "")) for w in band if w.get("col") == "bal"]
    if not col_words:
        return None, None

    lines = defaultdict(list)
    for y, txt in col_words:
        if PAGE_TITLE_RX.search(txt) or PAGE_NO_RX.search(txt) or FOOTER_DROP_LINE_RX.search(txt):
            continue
        lines[y].append(txt)

    printed = None
    for y in sorted(lines.keys()):
        line = " ".join(lines[y]).strip()
        line = re.sub(r"\b(Cr|Dr)\.?\b", "", line, flags=re.I)
        nums = [m.group(0) for m in AMT_ONLY_RX.finditer(line)]
        if nums:
            printed = nums[-1]
    if printed is None:
        return None, None
    return printed, _to_number(printed)

def _extract_rows_from_page(
    page,
    last_balance: Optional[float],
    base_boxes: Optional[Dict[str, Tuple[float, float]]] = None
) -> Tuple[List[list], Optional[float]]:

    boxes = _pnb_column_boxes(page) or base_boxes
    if not boxes:
        return [], last_balance

    words = page.extract_words(x_tolerance=2.0, y_tolerance=2.0, keep_blank_chars=False)

    # Tag each word with a detected column (by center x)
    for w in words:
        xm = (w["x0"] + w["x1"]) / 2.0
        w["col"] = None
        for name, (L, R) in boxes.items():
            if L <= xm <= R:
                w["col"] = name
                break

    # Date anchors
    anchors = [w for w in words if w.get("col") == "date" and DATE_ANCHOR_RX.search(w.get("text") or "")]
    anchors.sort(key=lambda w: w["top"])
    if not anchors:
        return [], last_balance

    cuts = [0.0] + [(anchors[i]["top"] + anchors[i + 1]["top"]) / 2.0 for i in range(len(anchors) - 1)] + [page.height + 1]

    rows: List[list] = []
    prev_bal = last_balance
    carry_prefix: Optional[str] = None

    for idx, a in enumerate(anchors):
        y_top = cuts[idx]
        y_bot = cuts[idx + 1]
        head_top = max(y_top, a["top"] - HEAD_SCAN_PX)
        band = [w for w in words if head_top <= w["top"] < y_bot]

        # ---- DATE ----
        date_txt = None
        for w in sorted([w for w in band if w.get("col") == "date"], key=lambda z: z["x0"]):
            m = DATE_ANCHOR_RX.search(w.get("text") or "")
            if m:
                date_txt = m.group(0)
                break
        date_out = _parse_date(date_txt or "")

        # ---- NARRATION (robust) ----
        date_L, date_R = boxes["date"]
        desc_L_hdr, _ = boxes["desc"]
        bal_left = boxes["bal"][0]

        # IMPORTANT CHANGE 1: right guard is *only* Balance (ignore dr/cr guesses)
        # narr_L = max(0.0, min(desc_L_hdr - 40.0, date_R - 24.0))
        # narr_R = bal_left - 2.0
        narr_L = max(0.0, min(desc_L_hdr - 60.0, date_R - 24.0))  # a touch wider left
        narr_R = bal_left - 2.0
        def _overlaps_span(w):
            return (w["x1"] > narr_L) and (w["x0"] < narr_R)

        # IMPORTANT CHANGE 2: include ANY token overlapping the band (even if tagged dr/cr),
        # we'll filter amounts by regex later.
        in_band = [w for w in band if _overlaps_span(w)]
        in_desc = [w for w in band if w.get("col") == "desc"]

        # Do we already have a prefix inside the band? If yes, disable rescue.
        has_prefix_in_band = any(PREFIX_START_RX.match((w.get("text") or "").strip()) for w in in_band)

        # Rescue zone: left of narr_L, but only near this row's header line to avoid next-row bleed
        rescued = []
        if not has_prefix_in_band:
            y_next_top = anchors[idx + 1]["top"] if (idx + 1) < len(anchors) else page.height + 1
            # res_top = a["top"] - 6.0
            # res_bot = min((a["top"] + y_next_top) / 2.0 - 1.0, a["top"] + 42.0)
            # rescue_L = max(0.0, narr_L - 120.0)
            res_top = a["top"] - 14.0
            res_bot = min((a["top"] + y_next_top) / 2.0 - 1.0, a["top"] + 55.0)
            rescue_L = max(0.0, narr_L - 180.0)
            for w in band:
                if (w["x1"] > rescue_L) and (w["x0"] < narr_L) and (res_top <= w["top"] <= res_bot):
                    t = (w.get("text") or "").strip()
                    if PREFIX_START_RX.match(t):
                        rescued.append(w)

        cand = {id(w): w for w in (rescued + in_band + in_desc)}
        desc_words = sorted(cand.values(), key=lambda z: (round(z["top"], 1), z["x0"]))

        parts: List[str] = []
        for w in desc_words:
            t = (w.get("text") or "").strip()
            if not t or t in {"-", "–", "—"}:
                continue
            if CHEQUE_NO_RX.fullmatch(t):
                continue
            if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_LINE_RX.search(t) or DESC_HEADER_LINE_RX.search(t):
                continue
            if TXNNO_RX.fullmatch(t):
                continue
            if AMT_ONLY_RX.fullmatch(t.replace(" ", "")):
                continue
            if DATE_ANCHOR_RX.fullmatch(t):
                continue
            if DRCR_RX.fullmatch(t):
                continue
            if HEADER_CELL_RX.fullmatch(t):
                continue
            # drop header-ish "B01/YESBN........" fragments
            # if BAD_INLINE_RX.match(t):
            #     continue
            parts.append(t)

        narration = _join_as_pdf(parts)
        narration = re.sub(r"^\s*[-–—•·]+\s*", "", narration)
        narration = NEFT_NULL_RX.sub(r"\1:", narration)

        # If previous row donated a prefix, prepend it when our row doesn't start with one
        if carry_prefix and not PREFIX_START_RX.match(narration):
            narration = f"{carry_prefix} {narration}"
            carry_prefix = None

        # If two prefixes live inside, split here and carry the 2nd to next row
        # If two prefixes live inside, split only when the 2nd really starts a NEXT row.
        hits = list(PFX_TOKEN_RX.finditer(narration))
        if len(hits) >= 2:
            second_slice = narration[hits[1].start():]
            first_slice  = narration[:hits[1].start()]
            s2u, s1u = second_slice.upper(), first_slice.upper()

            # GUARD: rows like "NEFT_IN:NEFT/0005//YESBN..." are valid and must NOT be split
            if s2u.startswith("NEFT/") and ("NEFT_IN" in s1u):
                pass  # keep whole narration
            else:
                carry_prefix = hits[1].group(0).strip()
                narration = narration[:hits[1].start()].rstrip()
        if re.fullmatch(r"(?:NEFT(?:\s*[_-]?\s*IN)?|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER|TO\s+SELF|BY\s+CASH):?", narration, flags=re.I):
            salvage_words = []
            for w in band:
                # allow a little more left than narr_L for wrapped "NEFT/..." starters
                if (w["x1"] > (narr_L - 200.0)) and (w["x0"] < bal_left - 1.0):
                    t = (w.get("text") or "").strip()
                    if not t or t in {"-", "–", "—"}:
                        continue
                    if AMT_ONLY_RX.fullmatch(t.replace(" ", "")):
                        continue
                    if DATE_ANCHOR_RX.fullmatch(t) or DRCR_RX.fullmatch(t) or TXNNO_RX.fullmatch(t):
                        continue
                    if PAGE_TITLE_RX.search(t) or PAGE_NO_RX.search(t) or FOOTER_DROP_LINE_RX.search(t) or DESC_HEADER_LINE_RX.search(t):
                        continue
                    salvage_words.append(w)

            salvage_words.sort(key=lambda z: (round(z["top"], 1), z["x0"]))
            narration = _join_as_pdf([(w.get("text") or "").strip() for w in salvage_words])
            narration = NEFT_NULL_RX.sub(r"\1:", narration)
            if re.fullmatch(r"(?:NEFT(?:\s*[_-]?\s*IN)?|NEFT|UPI|IMPS|RTGS|NACH|ACH|TRF|TRANSFER):?", narration, flags=re.I):
                tail = _scan_tail_from_band(band, narr_L, bal_left)
                if tail:
                    # ensure we end with a single colon before adding tail
                    narration = re.sub(r":?$", ":", narration.strip()) + " " + tail
        # last row on page: clip only if a real footer phrase intrudes
        if idx == len(anchors) - 1:
            m = FOOTER_START_RX.search(narration)
            if m:
                narration = narration[:m.start()].rstrip(" -–—•·")
        narration = _normalize_narration(narration)

        # ---- AMOUNTS ----
        dr = _last_num_in_col("dr", band) or 0.0
        cr = _last_num_in_col("cr", band) or 0.0
        if dr and cr:
            if abs(dr) >= abs(cr):
                cr = 0.0
            else:
                dr = 0.0

        # ---- BALANCE ----
        bal_txt, bal_val = _balance_text_and_val(band)
        if bal_val is None and prev_bal is not None:
            bal_val = round(prev_bal - float(dr or 0.0) + float(cr or 0.0), 2)
            bal_txt = f"{bal_val:,.2f}"

        # If no DR/CR printed but balance changed, infer side from delta
        if (not dr and not cr) and (bal_val is not None) and (prev_bal is not None):
            delta = round(bal_val - prev_bal, 2)
            if delta > 0:
                cr = abs(delta)
            elif delta < 0:
                dr = abs(delta)
        if BARE_PREFIX_RX.fullmatch(narration) and (not dr and not cr):
            # do NOT touch prev_bal; just ignore this fake row
            continue
        if bal_val is not None:
            prev_bal = bal_val

        rows.append([date_out, narration, "", float(dr or 0.0), float(cr or 0.0), bal_txt or ""])

    # Merge orphan “BY CASH / TO SELF” without amounts into neighbors
    merged: List[list] = []
    i = 0
    while i < len(rows):
        date, n1, n2, wdl, dep, baltxt = rows[i]
        has_amt = bool((wdl and float(wdl) != 0.0) or (dep and float(dep) != 0.0))
        if KEY_CASH_SELF_RX.search(str(n1 or "")) and not has_amt:
            if merged:
                prev = merged[-1]
                prev[1] = (str(prev[1]).strip() + " " + str(n1).strip()).strip()
                prev[2] = (str(prev[2]).strip() + " " + str(n2).strip()).strip()
                if baltxt and not prev[5]:
                    prev[5] = baltxt
                if (not prev[3] or float(prev[3]) == 0.0) and wdl:
                    prev[3] = wdl
                if (not prev[4] or float(prev[4]) == 0.0) and dep:
                    prev[4] = dep
                i += 1
                continue
            if i + 1 < len(rows):
                nxt = rows[i + 1]
                nxt[1] = (str(n1).strip() + " " + str(nxt[1]).strip()).strip()
                nxt[2] = (str(n2).strip() + " " + str(nxt[2]).strip()).strip()
                if (not nxt[3] or float(nxt[3]) == 0.0) and wdl:
                    nxt[3] = wdl
                if (not nxt[4] or float(nxt[4]) == 0.0) and dep:
                    nxt[4] = dep
                if baltxt and not nxt[5]:
                    nxt[5] = baltxt
                i += 1
                continue
        merged.append(rows[i])
        i += 1

    return merged, prev_bal

# ---------------- document traversal ----------------

def _extract_pnb(pdf: pdfplumber.PDF) -> List[list]:
    all_rows: List[list] = []
    last_balance: Optional[float] = None

    # capture boxes from the first page with headers
    base_boxes: Optional[Dict[str, Tuple[float, float]]] = None
    for p in pdf.pages:
        base_boxes = _pnb_column_boxes(p)
        if base_boxes:
            break

    for page in pdf.pages:
        page_rows, last_balance = _extract_rows_from_page(page, last_balance, base_boxes)
        all_rows.extend(page_rows)

    return all_rows


# ---------------- public API (BOB-like) ----------------

def pnb_1(pdf_paths: List[str], passwords: List[str]) -> List[List[List]]:
    """
    Parameters
    ----------
    pdf_paths : list[str]
        One or more PNB statement PDFs.
    passwords : list[str]
        Candidate passwords to try (filename, phone, etc.). None will also be tried.

    Returns
    -------
    data_table : list
        One entry per (bank, account) with:
          [
            [bank_name, account_number, "", "", "", ""],
            ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL BALANCE"],
            [rows...]
          ]
    """
    data_table: List[List[List]] = []

    for pdf_path in pdf_paths:
        extracted_rows: Optional[List[list]] = None
        acc_in_this_pdf: Optional[str] = None

        # try candidate passwords + None
        for pwd in (passwords or []) + [None]:
            try:
                with pdfplumber.open(pdf_path, password=pwd) as pdf:
                    if not pdf.pages:
                        break

                    # detect account number (first page preferred)
                    first_text = pdf.pages[0].extract_text() or ""
                    acc_in_this_pdf = _find_account_number(first_text)
                    if not acc_in_this_pdf:
                        whole = "\n".join([(p.extract_text() or "") for p in pdf.pages[:3]])
                        acc_in_this_pdf = _find_account_number(whole)

                    extracted_rows = _extract_pnb(pdf)
                break
            except Exception:
                continue

        if not extracted_rows:
            continue

        # format for BOB-like API
        table_rows: List[List] = []
        for date, n1, n2, wdl, dep, baltxt in extracted_rows:
            # normalize date
            date = _parse_date(date)

            # clean accidental page-title fragments
            n1 = PAGE_TITLE_RX.sub("", str(n1 or "")).strip()

            # numeric enforcement
            wdl = float(wdl or 0.0)
            dep = float(dep or 0.0)

            # balance as float if parseable, else keep ""
            if baltxt == "" or baltxt is None:
                bal_out = ""
            else:
                num = _to_number(str(baltxt))
                bal_out = float(num) if num is not None else ""

            table_rows.append([date, n1, n2, wdl, dep, bal_out])

        account_no = acc_in_this_pdf or "UNKNOWN"
        account_header = [bank_name, account_no, "", "", "", ""]
        headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

        # If multiple PDFs for same account, append rows
        placed = False
        for idx, existing in enumerate(data_table):
            if existing and existing[0][1] == account_no:
                data_table[idx].extend(table_rows)
                placed = True
                break
        if not placed:
            data_table.append([account_header, headers] + table_rows)

    return data_table


# Optional quick CLI test
if __name__ == "__main__":
    demo_files = [r"E:\PDFs\PNB\sample.pdf"]  # change me
    demo_pwds = ["1234", "password"]
    out = pnb_1(demo_files, demo_pwds)
    for t in out:
        print(f"Account: {t[0][1]}  Rows: {max(0, len(t)-2)}")
