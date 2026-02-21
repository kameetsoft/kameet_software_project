import pdfplumber
import re
from dateutil import parser

bank_name = "BANDHAN"

# HEADERS = ["DATE", "NARRATION", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
# HEADERS = ["Date", "Narration", "Withdrawals", "Deposits", "Balance"]

HEADERS = [
    "Date",
    "Narration1",
    "Narration2",
    "Withdrawals",
    "Deposits",
    "Balance"
]


# DATE_RX = re.compile(r'[A-Za-z]+\s+\d{1,2},\s*\d{4}')
DATE_RX = re.compile(
    r'[A-Za-z]+\s*\d{1,2},\s*\d{4}'
)
AMOUNT_RX = re.compile(r'INR\s*([\d,]+\.\d{2})', re.I)
DRCR_RX   = re.compile(r'\b(DR|CR)\b', re.I)

ACC_RX = re.compile(
    r'(?:Account\s*(?:Number|No\.?|#)|A/C\s*No\.?)\s*[:\-]?\s*(\d{8,20})',
    re.I
)
AMT_RX = re.compile(
    r'INR\s*([\d,]+\.\d{2})\s*(Dr|Cr)\s*INR\s*([\d,]+\.\d{2})',
    re.I
)
STOP_RX = re.compile(
    r'(statement summary|opening balance|total credits|total debits|'
    r'closing balance|statement generated|insurance|customer care|'
    r'complimentary insurance|end of statement)',
    re.I
)




# def bandhan_1(pdf_paths, passwords):
#     data_table = []

#     for pdf_path in pdf_paths:

#         # ------------------ OPEN PDF ------------------
#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     lines = []
#                     for p in pdf.pages:
#                         lines.extend((p.extract_text() or "").splitlines())
#                 break
#             except Exception:
#                 continue
#         else:
#             return {"error": "Passwords failed"}

#         full_text = "\n".join(lines)

#         # ------------------ ACCOUNT NO ------------------
#         acc_match = ACC_RX.search(full_text)
#         account_number = acc_match.group(1) if acc_match else "UNKNOWN"

#         rows = []
#         buffer = []

#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue

#             buffer.append(line)

#             # 🔑 END OF ONE TRANSACTION
#             # if re.search(r'INR\s*[\d,]+\.\d{2}\s+(Dr|Cr)\s+INR[\d,]+\.\d{2}', line, re.I):
#             if re.search(r'INR\s*[\d,]+\.\d{2}\s*(Dr|Cr)\s*INR\s*[\d,]+\.\d{2}', line, re.I):

#                 block = " ".join(buffer)
#                 buffer = []

#                 # ---------------- DATE ----------------
#                 # date_match = re.search(r'[A-Za-z]+\s+\d{1,2},\s*\d{4}', block)
#                 date_match = re.search(r'[A-Za-z]+\s*\d{1,2},\s*\d{4}', block)

#                 if not date_match:
#                     continue

#                 txn_date = parser.parse(date_match.group(), fuzzy=True).strftime("%d-%m-%Y")

#                 # ---------------- AMOUNTS ----------------
#                 amounts = re.findall(r'INR\s*([\d,]+\.\d{2})', block)
#                 if len(amounts) < 2:
#                     continue

#                 amount = float(amounts[0].replace(",", ""))
#                 balance = float(amounts[-1].replace(",", ""))

#                 # drcr = "DR" if re.search(r'\bDr\b', block, re.I) else "CR"
#                 drcr = "DR" if re.search(r'\bDr\b', block, re.I) else (
#                         "CR" if re.search(r'\bCr\b', block, re.I) else ""
#                 )


#                 withdrawal = amount if drcr == "DR" else 0.0
#                 deposit = amount if drcr == "CR" else 0.0

#                 # ---------------- NARRATION ----------------
#                 narration = re.sub(r'INR\s*[\d,]+\.\d{2}', '', block)
#                 narration = re.sub(r'\bDr\b|\bCr\b', '', narration, flags=re.I)
#                 narration = narration.replace(date_match.group(), "")
#                 narration = narration.strip(" -/:")

#                 rows.append([
#                     txn_date,
#                     narration[:250],   # safety trim
#                     withdrawal,
#                     deposit,
#                     balance
#                 ])

#         # ------------------ FINAL TABLE ------------------
#         account_row = [bank_name, account_number, "", "", "", ""]
#         data_table.append([account_row, HEADERS] + rows)

#     return data_table


# def bandhan_1(pdf_paths, passwords):
#     data_table = []

#     for pdf_path in pdf_paths:

#         # ---------- OPEN PDF ----------
#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     lines = []
#                     for p in pdf.pages:
#                         lines.extend((p.extract_text() or "").splitlines())
#                 break
#             except Exception:
#                 continue
#         else:
#             return {"error": "Passwords failed"}

#         full_text = "\n".join(lines)

#         # ---------- ACCOUNT NO ----------
#         acc_match = ACC_RX.search(full_text)
#         account_number = acc_match.group(1) if acc_match else "UNKNOWN"

#         rows = []
#         buffer = []
#         in_txn_section = False

#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue

#             # 🔑 Start reading ONLY after table header
#             if "Transaction Date" in line:
#                 in_txn_section = True
#                 continue
#             if not in_txn_section:
#                 continue

#             buffer.append(line)

#             # 🔑 End of transaction
#             amt_match = AMT_RX.search(line)
#             if not amt_match:
#                 continue

#             block = " ".join(buffer)
#             buffer = []

#             # ---------- DATE ----------
#             date_match = DATE_RX.search(block)
#             if not date_match:
#                 continue

#             txn_date = parser.parse(
#                 date_match.group(), fuzzy=True
#             ).strftime("%d-%m-%Y")

#             # ---------- AMOUNTS ----------
#             amount = float(amt_match.group(1).replace(",", ""))
#             drcr   = amt_match.group(2).upper()
#             balance = float(amt_match.group(3).replace(",", ""))

#             withdrawal = amount if drcr == "DR" else 0.0
#             deposit    = amount if drcr == "CR" else 0.0

#             # ---------- NARRATION CLEAN ----------
#             narration = block

#             # remove both dates
#             narration = DATE_RX.sub("", narration)

#             # remove amount line
#             narration = AMT_RX.sub("", narration)

#             # normalize spaces
#             narration = re.sub(r"\s+", " ", narration).strip(" -:/")

#             # ---------- SPLIT NARRATION ----------
#             if len(narration) > 120:
#                 narration1 = narration[:120]
#                 narration2 = narration[120:240]
#             else:
#                 narration1 = narration
#                 narration2 = ""

#             rows.append([
#                 txn_date,
#                 narration1,
#                 narration2,
#                 withdrawal,
#                 deposit,
#                 balance
#             ])

#         # ---------- FINAL TABLE ----------
#         account_row = [bank_name, account_number, "", "", "", ""]
#         data_table.append([account_row, HEADERS] + rows)

#     return data_table


def bandhan_1(pdf_paths, passwords):
    data_table = []

    for pdf_path in pdf_paths:

        # ---------- OPEN PDF ----------
        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    lines = []
                    for p in pdf.pages:
                        lines.extend((p.extract_text() or "").splitlines())
                break
            except Exception:
                continue
        else:
            return {"error": "Passwords failed"}

        full_text = "\n".join(lines)

        # ---------- ACCOUNT NO ----------
        acc_match = ACC_RX.search(full_text)
        account_number = acc_match.group(1) if acc_match else "UNKNOWN"

        rows = []

        current_block = []
        current_date = None

        # for line in lines:
        #     line = line.strip()
        #     if not line:
        #         continue

        #     date_match = DATE_RX.search(line)

        #     # 🔑 NEW TRANSACTION START
        #     if date_match:
        #         # finalize previous transaction
        #         if current_block:
        #             block = " ".join(current_block)
        #             rows.append(parse_bandhan_block(block))
        #             current_block = []

        #         current_date = date_match.group()

        #     if current_date:
        #         current_block.append(line)


        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 🛑 HARD STOP if footer text starts
            # if STOP_RX.search(line):
            #     break

            date_match = DATE_RX.search(line)

            # 🔑 NEW TRANSACTION START
            if date_match:
                if current_block:
                    block = " ".join(current_block)
                    row = parse_bandhan_block(block)
                    if row:
                        rows.append(row)
                    current_block = []

                current_date = date_match.group()

            if current_date:
                current_block.append(line)

        # finalize last transaction
        if current_block:
            block = " ".join(current_block)
            rows.append(parse_bandhan_block(block))


        # 🔥 FIX ONLY LAST ROW NARRATION (DO NOT AFFECT OTHERS)
        if rows:
            last_row = rows[-1]

            narration = last_row[1]   # Narration column

            # Remove footer / summary junk ONLY from last row
            narration = STOP_RX.split(narration)[0]

            # Clean again
            narration = re.sub(r"\s+", " ", narration).strip(" -:/")

            # Safety limit
            if len(narration) > 180:
                narration = narration[:180]

            last_row[1] = narration

        # ---------- FINAL TABLE ----------
        account_row = [bank_name, account_number, "", "", "", ""]
        data_table.append([account_row, HEADERS] + rows)

    return data_table


def parse_bandhan_block(block):
    # ---------- DATE ----------
    date_match = DATE_RX.search(block)
    txn_date = parser.parse(
        date_match.group(), fuzzy=True
    ).strftime("%d-%m-%Y") if date_match else ""

    # ---------- AMOUNT ----------
    amt_match = AMT_RX.search(block)
    if not amt_match:
        return None

    amount = float(amt_match.group(1).replace(",", ""))
    drcr = amt_match.group(2).upper()
    balance = float(amt_match.group(3).replace(",", ""))

    withdrawal = amount if drcr == "DR" else 0.0
    deposit    = amount if drcr == "CR" else 0.0

    # ---------- CLEAN NARRATION ----------
    narration = block
    narration = DATE_RX.sub("", narration)
    narration = AMT_RX.sub("", narration)
    # narration = re.sub(r"\s+", " ", narration).strip(" -:/")
    narration = re.sub(r"\s+", " ", narration).strip(" -:/")

    # 🛑 HARD LENGTH SAFETY (Bandhan narration is NEVER huge)
    if len(narration) > 180:
        narration = narration[:180]

    return [
        txn_date,
        narration,      # FULL narration in ONE column
        "",              # narration2 not needed now
        withdrawal,
        deposit,
        balance
    ]
