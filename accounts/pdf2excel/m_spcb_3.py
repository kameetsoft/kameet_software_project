# # accounts/pdf2excel/m_spcb_3_fixed.py
# import pdfplumber, re
# from datetime import datetime

# bank_name = "SPCB"
# DATE_RX = re.compile(r'^\d{2}/\d{2}/\d{2}$')
# TXN_START_RX = re.compile(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{2}/\d{2}')

# def _num(s):
#     s = re.sub(r'[^\d.-]', '', s)
#     try:
#         return float(s)
#     except:
#         return 0.0

# def _parse_date(text):
#     try:
#         return datetime.strptime(text.strip(), "%d/%m/%y").strftime("%d-%m-%Y")
#     except:
#         return text.strip()

# def spcb_3(pdf_paths, passwords):
#     data = []
#     acc_no = ""

#     for path in pdf_paths:
#         for pw in passwords + [None]:
#             try:
#                 with pdfplumber.open(path, password=pw) as pdf:
#                     txt = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
#                     m = re.search(r'Account No\s*([\d ]{9,18})', txt)
#                     if m:
#                         acc_no = m.group(1).strip()
#                     lines = txt.splitlines()

#                     blocks, buf = [], []
#                     for ln in lines:
#                         if TXN_START_RX.match(ln):
#                             if buf:
#                                 blocks.append("\n".join(buf))
#                             buf = [ln]
#                         else:
#                             if buf:
#                                 buf.append(ln)
#                     if buf:
#                         blocks.append("\n".join(buf))

#                     # for blk in blocks:
#                     #     blk = blk.replace("\xa0", " ").strip()
#                     #     if not blk:
#                     #         continue
#                     for blk in blocks:
#                         blk = blk.replace("\xa0", " ").strip()
#                         if not blk:
#                             continue

#                         # 🧹 Clean trailing summary lines (fix for last entry)
#                         # blk = re.sub(r"(CARRIED\s+FORWARD:|Statement\s+Summary.*)", "", blk, flags=re.I).strip()
#                         # blk = re.sub(r"(Dr\.\s*Count\s*\d+.*Cr\.\s*Count\s*\d+.*)", "", blk, flags=re.I).strip()

#                         # 🧹 Clean trailing carried-forward/summary noise
#                         blk = re.sub(
#                             r"(CARRIED\s+FORWARD:.*|Statement\s+Summary.*|Dr\.\s*Count\s*\d+.*Cr\.\s*Count\s*\d+.*)",
#                             "",
#                             blk,
#                             flags=re.I | re.S,
#                         ).strip()

#                         if not blk:
#                             continue

#                         parts = blk.split()
#                         if len(parts) < 2:
#                             continue

#                         post_dt = _parse_date(parts[0])
#                         val_dt = _parse_date(parts[1])

#                         # capture all numeric + Cr/Dr pairs
#                         m_amt = re.findall(r'(\d[\d,]*\.\d{2})\s*(Cr|Dr|CR|DR)?', blk)
#                         if not m_amt:
#                             continue

#                         # last number = balance, second last = txn amt
#                         bal_raw, *rest = m_amt[::-1]
#                         bal = _num(bal_raw[0])
#                         bal_tag = (bal_raw[1] or "").lower()
#                         bal_sign = -1 if bal_tag == "dr" else 1

#                         debit = credit = 0.0
#                         others = m_amt[:-1]

#                         if others:
#                             val, tag = others[-1]  # 2nd last number = txn amount
#                             amt = _num(val)
#                             tag = (tag or "").lower()

#                             # ---------------- classification ----------------
#                             if tag == "dr":
#                                 debit = amt
#                             elif tag == "cr" or re.search(r"Cr\.for", blk, re.I):
#                                 credit = amt
#                             else:
#                                 # keyword inference
#                                 if re.search(r"REGENCY|WITHDRAWAL|ATM|SELF|TRANSFER|PAYMENT|BILL", blk, re.I):
#                                     debit = amt
#                                 elif re.search(r"/CR\b|Cr\.for|GOOGLEINDI|UTIB|IMPS/|NEFT/|BY|FROM|CREDIT|RECEIVED|DEPOSIT|RTGS", blk, re.I):
#                                     credit = amt
#                                 else:
#                                     if re.search(r"\bDr\b", blk, re.I):
#                                         debit = amt
#                                     elif re.search(r"\bCr\b", blk, re.I):
#                                         credit = amt
#                                     else:
#                                         if re.search(r"REGENCY|PHONEPE|AMAZON|BILL|PAYMENT|TRANSFER", blk, re.I):
#                                             debit = amt
#                                         else:
#                                             credit = amt

#                         # --- Fix 1: Opening balance detection ---
#                         if re.search(r"BALANCE\s+(TRANSFER|BROUGHT\s+FORWARD)", blk, re.I):
#                             debit = 0.0
#                             credit = _num(m_amt[0][0])  # take first numeric as credit

#                         # --- Fix 2: Handle IMPS/CR trailing pattern correctly ---
#                         if re.search(r"/CR\b", blk, re.I) and credit == 0.0 and others:
#                             credit = _num(others[-1][0])
#                             debit = 0.0

#                         narr = re.sub(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{2}/\d{2}\s*', '', blk)
#                         narr = re.sub(r'\d[\d,]*\.\d{2}\s*(Cr|Dr|CR|DR)?$', '', narr).strip()

#                         data.append([
#                             post_dt,
#                             narr[:85],
#                             narr[85:],
#                             round(debit, 2),
#                             round(credit, 2),
#                             round(bal * bal_sign, 2),
#                         ])
#                 break
#             except Exception:
#                 continue

#     headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
#     account_row = [bank_name, acc_no or "", "", "", "", ""]
#     return [account_row, headers] + data


# if __name__ == "__main__":
#     tbl = spcb_3([r"/mnt/data/REGENCY SURAT PEOPLES.pdf"], [])
#     from tabulate import tabulate
#     print(tabulate(tbl, headers="firstrow", tablefmt="grid"))



# accounts/pdf2excel/m_spcb_3_fixed.py
import pdfplumber, re
from datetime import datetime

bank_name = "SPCB"
DATE_RX = re.compile(r'^\d{2}/\d{2}/\d{2}$')
TXN_START_RX = re.compile(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{2}/\d{2}')

def _num(s):
    s = re.sub(r'[^\d.-]', '', s)
    try:
        return float(s)
    except:
        return 0.0

def _parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%d/%m/%y").strftime("%d-%m-%Y")
    except:
        return text.strip()

def spcb_3(pdf_paths, passwords):
    data = []
    acc_no = ""
    prev_bal = None  # ← track signed previous closing balance

    for path in pdf_paths:
        for pw in passwords + [None]:
            try:
                with pdfplumber.open(path, password=pw) as pdf:
                    txt = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                    m = re.search(r'Account No\s*([\d ]{9,18})', txt)
                    if m:
                        acc_no = m.group(1).strip()
                    lines = txt.splitlines()

                    blocks, buf = [], []
                    for ln in lines:
                        if TXN_START_RX.match(ln):
                            if buf:
                                blocks.append("\n".join(buf))
                            buf = [ln]
                        else:
                            if buf:
                                buf.append(ln)
                    if buf:
                        blocks.append("\n".join(buf))

                    for blk in blocks:
                        blk = blk.replace("\xa0", " ").strip()
                        if not blk:
                            continue

                        # 🧹 drop carried-forward / summary noise that sometimes sticks to last txn
                        blk = re.sub(
                            r"(CARRIED\s+FORWARD:.*|Statement\s+Summary.*|Dr\.\s*Count\s*\d+.*Cr\.\s*Count\s*\d+.*)",
                            "",
                            blk,
                            flags=re.I | re.S,
                        ).strip()
                        if not blk:
                            continue

                        parts = blk.split()
                        if len(parts) < 2:
                            continue

                        post_dt = _parse_date(parts[0])
                        val_dt = _parse_date(parts[1])

                        # capture every "amount [Cr|Dr]" pattern; statement uses "5,80,534.73 Cr" style
                        m_amt = re.findall(r'(\d[\d,]*\.\d{2})\s*(Cr|Dr|CR|DR)?', blk)
                        if not m_amt:
                            continue

                        # last numeric = closing balance; second-last = txn amount
                        bal_raw, *rest_rev = m_amt[::-1]
                        bal = _num(bal_raw[0])
                        bal_tag = (bal_raw[1] or "").lower()
                        bal_sign = -1 if bal_tag == "dr" else 1
                        signed_bal = round(bal * bal_sign, 2)

                        debit = credit = 0.0
                        amt = 0.0
                        tag = ""

                        others = m_amt[:-1]
                        if others:
                            txn_val, txn_tag = others[-1]
                            amt = _num(txn_val)
                            tag = (txn_tag or "").lower()

                        # ---------- strong explicit cases first ----------
                        # Opening / brought forward
                        if re.search(r"BALANCE\s+(TRANSFER|BROUGHT\s+FORWARD)", blk, re.I):
                            debit = 0.0
                            credit = amt if amt else (others and _num(others[-1][0]) or 0.0)
                            prev_bal = signed_bal
                        # Trailing "/CR" style IMPS credit lines
                        elif re.search(r"/CR\b", blk, re.I) and credit == 0.0 and others:
                            credit = _num(others[-1][0])
                            debit = 0.0
                        else:
                            # If txn explicitly tagged Cr/Dr next to txn amount, obey it
                            if tag in ("cr", "dr"):
                                if tag == "cr":
                                    credit = amt
                                else:
                                    debit = amt
                            else:
                                # ---------- preferred: infer from balance delta ----------
                                decided = False
                                if prev_bal is not None and amt > 0:
                                    delta = round(signed_bal - prev_bal, 2)
                                    # tolerate small rounding: 0.00–0.02
                                    if abs(abs(delta) - amt) <= 0.02:
                                        if delta > 0:
                                            credit = amt
                                        elif delta < 0:
                                            debit = amt
                                        else:
                                            # no change: keep zeros
                                            pass
                                        decided = True

                                # ---------- fallback: gentle keyword hints ----------
                                if not decided and amt > 0:
                                    # phrases that almost always mean inward credit
                                    if re.search(r"(NEFT|RTGS|IMPS|BY|FROM|RECEIVED|CREDIT|DEPOSIT)\b", blk, re.I):
                                        credit = amt
                                    # phrases that almost always mean outward debit
                                    elif re.search(r"(WITHDRAWAL|ATM|BILL|PAYMENT|CHG|CHARGES|TRANSFER\s+TO)\b", re.I):
                                        debit = amt
                                    else:
                                        # last resort: treat as credit (most unlabeled lines here are inward)
                                        credit = amt

                        narr = re.sub(r'^\d{2}/\d{2}/\d{2}\s+\d{2}/\d{2}/\d{2}\s*', '', blk)
                        narr = re.sub(r'\d[\d,]*\.\d{2}\s*(Cr|Dr|CR|DR)?$', '', narr).strip()

                        data.append([
                            post_dt,
                            narr[:85],
                            narr[85:],
                            round(debit, 2),
                            round(credit, 2),
                            signed_bal,
                        ])

                        # advance prev balance tracker
                        prev_bal = signed_bal
                break
            except Exception:
                continue

    headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
    account_row = [bank_name, acc_no or "", "", "", "", ""]
    return [account_row, headers] + data

if __name__ == "__main__":
    tbl = spcb_3([r"/mnt/data/REGENCY SURAT PEOPLES.pdf"], [])
    from tabulate import tabulate
    print(tabulate(tbl, headers="firstrow", tablefmt="grid"))
