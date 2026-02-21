# import pdfplumber
# import re
# from datetime import datetime

# BANK_NAME = "SBI"

# HEADERS = [
#     "Txn Date",
#     "Value Date",
#     "Description",
#     "Ref No / Cheque No",
#     "Debit",
#     "Credit",
#     "Balance",
# ]

# DATE_RX = re.compile(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}")
# AMT_RX = re.compile(r"[\d,]+\.\d{2}")

# def sbi_3(pdf_path, password):
#     rows = []

#     with pdfplumber.open(pdf_path, password=password) as pdf:
#         for page in pdf.pages:
#             text = page.extract_text() or ""
#             text = text.replace("\u200b", " ").replace("\xa0", " ")

#             lines = [l.strip() for l in text.splitlines() if l.strip()]

#             i = 0
#             while i < len(lines):
#                 line = lines[i]

#                 # Row starts with Txn Date + Value Date
#                 if DATE_RX.match(line):
#                     parts = line.split()
#                     txn_date = " ".join(parts[:3])
#                     value_date = " ".join(parts[3:6])

#                     desc_lines = []
#                     ref = debit = credit = balance = ""

#                     j = i + 1
#                     while j < len(lines):
#                         if AMT_RX.search(lines[j]):
#                             nums = AMT_RX.findall(lines[j])

#                             # SBI logic: Debit OR Credit, Balance always last
#                             if len(nums) == 2:
#                                 credit = nums[0]
#                                 balance = nums[1]
#                             elif len(nums) == 3:
#                                 debit = nums[0]
#                                 credit = nums[1]
#                                 balance = nums[2]

#                             ref = lines[j - 1]
#                             break
#                         else:
#                             desc_lines.append(lines[j])
#                         j += 1

#                     description = " ".join(desc_lines)

#                     rows.append([
#                         txn_date,
#                         value_date,
#                         description,
#                         ref,
#                         debit,
#                         credit,
#                         balance,
#                     ])

#                     i = j + 1
#                 else:
#                     i += 1

#     return {
#         "bank": BANK_NAME,
#         "headers": HEADERS,
#         "rows": rows,
#     }



import pdfplumber
import re

BANK_NAME = "SBI"

HEADERS = [
    "Txn Date",
    "Description",
    "Ref No / Cheque No",
    "Debit",
    "Credit",
    "Balance",
]
DATE_FULL_RX = re.compile(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}")
DATE_PART_RX = re.compile(r"\d{1,2}\s+[A-Za-z]{3}$")
YEAR_RX = re.compile(r"^\d{4}$")
DATE_NOYEAR_RX = re.compile(
    r"^(?P<d>\d{1,2}\s+[A-Za-z]{3})\s+(?P<vd>\d{1,2}\s+[A-Za-z]{3})\s+(?P<rest>.+)$"
)
YEARPAIR_RX = re.compile(r"^(20\d{2})\s+(20\d{2})\s+")
def _detect_stmt_year(pdf):
    for page in pdf.pages[:2]:
        t = page.extract_text() or ""
        m = re.search(r"Account Statement from .*?(\d{4}).*?to .*?(\d{4})", t)
        if m:
            return int(m.group(2))
    return None

def _clean_amount(val):
    if not val:
        return ""
    return val.replace(",", "")

def _is_noise_line(line):
    return (
        "Txn Date" in line
        or "Value Date" in line
        or "Debit Credit Balance" in line
        or "computer generated" in line.lower()
        or "Please do not share your ATM" in line
    )
REF_RX = re.compile(r"(UPI/(CR|DR)/\d+)")

def _parse_sbi_block(text):
    text = re.sub(r"\s+", " ", text).strip()

    # m = re.match(r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(.*)", text)
    m = re.match(
        r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(.*)",
        text
    )

    if not m:
        return None

    # txn_date = m.group(1)
    # rest = m.group(2)
    # txn_date  = m.group(1)   # ignore
    value_date = m.group(2)    # ✅ THIS is what we want
    rest       = m.group(3)


    rest = re.sub(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+", "", rest)

    amounts = re.findall(
        r"\b(?:\d{1,3}(?:,\d{2})+(?:,\d{3})|\d{1,3}(?:,\d{3})*|\d+)\.\d{2}\b",
        rest
    )
    if not amounts:
        return None

    balance = amounts[-1]
    debit = credit = ""

    if len(amounts) >= 2:
        txn_amt = amounts[-2]
        if rest.startswith("TO") or "/DR/" in rest:
            debit = txn_amt
        else:
            credit = txn_amt

    # remove amounts
    desc = rest
    for a in amounts:
        desc = desc.replace(a, "")

    # extract ref no
    ref_no = ""
    mref = REF_RX.search(desc)
    if mref:
        ref_no = mref.group(1)
        desc = desc.replace(ref_no, "").strip()

    return [
        value_date,
        desc,                     # Narration1 (clean)
        ref_no,                   # Narration2 (Ref No)
        _clean_amount(debit),
        _clean_amount(credit),
        _clean_amount(balance),
    ]

def _parse_single_pdf(pdf_path, password):
    rows = []

    with pdfplumber.open(pdf_path, password=password) as pdf:
        stmt_year = _detect_stmt_year(pdf) or 2025  # fallback

        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if not text:
                continue

            raw_lines = [l for l in text.split("\n") if l.strip()]
            lines = []

            for l in raw_lines:
                l = l.replace("\u00a0", " ").replace("\ufeff", " ")
                l = re.sub(r"\s+", " ", l).strip()

                # ✅ remove leading "2025 2025 " from continuation lines
                l = YEARPAIR_RX.sub("", l)

                if l:
                    lines.append(l)

            buffer = ""
            pending_date = None

            for line in lines:

                # ✅ extra footer noise (this PDF breaks footer into multiple lines)
                if _is_noise_line(line) or "Bank never asks" in line or "with anyone over mail" in line or "(cid:" in line:
                    continue

                # ✅ Case A: "10 Apr 10 Apr ..." (no year shown)
                mny = DATE_NOYEAR_RX.match(line)
                if mny:
                    if buffer:
                        row = _parse_sbi_block(buffer)
                        if row:
                            rows.append(row)

                    d  = mny.group("d")
                    vd = mny.group("vd")
                    rest = mny.group("rest")

                    # build full dates so _parse_sbi_block can remove value date
                    buffer = f"{d} {stmt_year} {vd} {stmt_year} {rest}"
                    pending_date = None
                    continue

                # ✅ Case B: full date present
                if DATE_FULL_RX.match(line):
                    if buffer:
                        row = _parse_sbi_block(buffer)
                        if row:
                            rows.append(row)
                    buffer = line
                    pending_date = None
                    continue

                # ✅ Case C: date split (10 Apr) then (2025)
                if DATE_PART_RX.match(line):
                    pending_date = line
                    continue

                if pending_date and YEAR_RX.match(line):
                    full_date = f"{pending_date} {line}"
                    if buffer:
                        row = _parse_sbi_block(buffer)
                        if row:
                            rows.append(row)
                    buffer = full_date
                    pending_date = None
                    continue

                # ignore stray year-only lines (sometimes appear as separate table column)
                if YEAR_RX.match(line) and not pending_date:
                    continue

                buffer += " " + line

            if buffer:
                row = _parse_sbi_block(buffer)
                if row:
                    rows.append(row)

    print(f"✅ SBI-3 rows parsed: {len(rows)}")
    return rows


# ─────────────────────────────────────────────
# ENTRY POINT CALLED BY YOUR SYSTEM
# ─────────────────────────────────────────────
def sbi_3(file_paths, passwords):
    all_rows = []

    for pdf_path in file_paths:
        parsed_rows = None

        for pw in passwords + [None]:
            try:
                parsed_rows = _parse_single_pdf(pdf_path, pw)
                if parsed_rows:
                    break
            except Exception as e:
                print(f"⚠️ Password failed for {pdf_path}: {e}")
                continue

        if not parsed_rows:
            print(f"❌ SBI-3: no rows found in {pdf_path}")
            continue

        all_rows.extend(parsed_rows)

    print(f"🎯 TOTAL ROWS ACROSS FILES: {len(all_rows)}")

    return {
        "bank": BANK_NAME,
        "headers": HEADERS,
        "rows": all_rows,
    }
