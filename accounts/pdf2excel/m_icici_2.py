# import pdfplumber
# import re

# bank_name = "ICICI Bank"

# HEADERS = ["Date", "Narration1", "Narration2", "Withdrawals", "Deposits", "Balance"]

# # ✅ Capture:
# # date date
# # narration (MULTI-LINE)
# # withdraw deposit balance
# LINE_RX = re.compile(
#     r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
#     r"\d{2}/\d{2}/\d{4}\s+"
#     r"(?P<body>.*?)"
#     r"\s+(?P<withdraw>[\d,]+\.\d{2})\s+"
#     r"(?P<deposit>[\d,]+\.\d{2})\s+"
#     r"(?P<balance>[\d,]+\.\d{2})",
#     re.DOTALL
# )

# def _to_float(val):
#     if not val:
#         return 0.0
#     return float(re.sub(r"[^\d.]", "", val))

# def _clean_narration(text: str) -> tuple[str, str]:
#     """
#     Splits narration into 2 columns safely
#     """
#     lines = [l.strip() for l in text.splitlines() if l.strip()]

#     if not lines:
#         return "", ""

#     narration1 = lines[0]
#     narration2 = " ".join(lines[1:]) if len(lines) > 1 else ""

#     return narration1, narration2

# def icici_2(pdf_paths, passwords):
#     data_table = []

#     for pdf_path in pdf_paths:
#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     rows = []

#                     for page in pdf.pages:
#                         text = page.extract_text() or ""
#                         text = text.replace("\u200b", "").replace("\xa0", " ")

#                         for m in LINE_RX.finditer(text):
#                             narration1, narration2 = _clean_narration(
#                                 m.group("body")
#                             )

#                             rows.append([
#                                 m.group("date"),
#                                 narration1,
#                                 narration2,
#                                 _to_float(m.group("withdraw")),
#                                 _to_float(m.group("deposit")),
#                                 _to_float(m.group("balance")),
#                             ])

#                     if rows:
#                         account_row = [bank_name, "", "", "", "", ""]
#                         data_table.append([account_row, HEADERS] + rows)
#                         return data_table

#             except Exception:
#                 continue

#     return data_table



import pdfplumber
import re


bank_name = "ICICI Bank"

HEADERS = ["Date", "Narration1", "Narration2", "Withdrawals", "Deposits", "Balance"]

STOP_NARRATION_RX = re.compile(
    r"""
    ^\d+\.\s*[A-Z]{2,}      |  # 1. INFT / 2. BPAY etc
    \bCAPTIONS\b            |
    \bINFT\b                |
    \bBPAY\b                |
    \bBBPS\b                |
    \bNEFT\b                |
    \bIMPS\b                |
    \bRTGS\b                |
    \bUPI\b\s*-\s*          |
    \bICICI\b               |
    \bTRANSACTION\s+TYPE\b  |
    \bSERVICE\b             |
    \bCHARGES\b
    """,
    re.I | re.X
)

ROW_START_RX = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})\s+"
    r"\d{2}/\d{2}/\d{4}\s+"
    r"(?P<narration>.+?)\s+"
    r"(?P<withdraw>[\d,]+\.\d{2})\s+"
    r"(?P<deposit>[\d,]+\.\d{2})\s+"
    # r"(?P<balance>[\d,]+\.\d{2})"
    r"(?P<balance>-?[\d,]+\.\d{2})"
)

def _to_float(v):
    if not v:
        return 0.0
    return float(re.sub(r"[^\d.]", "", v))

def icici_2(pdf_paths, passwords):
    data_table = []

    for pdf_path in pdf_paths:
        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    rows = []
                    current_row = None

                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        text = text.replace("\u200b", "").replace("\xa0", " ")

                        for line in text.splitlines():
                            line = line.strip()
                            if not line:
                                continue

                            m = ROW_START_RX.search(line)

                            if m:
                                # ✅ Start of new transaction
                                if current_row:
                                    rows.append(current_row)

                                # current_row = [
                                #     m.group("date"),
                                #     m.group("narration").strip(),
                                #     _to_float(m.group("withdraw")),
                                #     _to_float(m.group("deposit")),
                                #     _to_float(m.group("balance")),
                                # ]
                                current_row = [
                                    m.group("date"),
                                    m.group("narration").strip(),  # Narration1
                                    "",                             # Narration2 (EMPTY)
                                    _to_float(m.group("withdraw")),
                                    _to_float(m.group("deposit")),
                                    _to_float(m.group("balance")),
                                ]

                            else:
                                # ✅ Continuation of narration
                                # if current_row and not re.search(r"\d+\.\d{2}", line):
                                #     current_row[1] += " " + line
                                if current_row:
                                    # STOP narration when legend / captions start
                                    if STOP_NARRATION_RX.search(line):
                                        rows.append(current_row)
                                        current_row = None
                                        continue

                                    # normal continuation line
                                    if not re.search(r"\d+\.\d{2}", line):
                                        current_row[1] += " " + line


                    # append last row
                    if current_row:
                        rows.append(current_row)

                    if rows:
                        account_row = [bank_name, "", "", "", "", ""]
                        data_table.append([account_row, HEADERS] + rows)
                        return data_table

            except Exception as e:
                continue

    return data_table
