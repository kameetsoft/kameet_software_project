# import pdfplumber
# from tabulate import tabulate
# import re
# from datetime import datetime



# days_pattern = r'([0-2][0-9]|(3)[0-1])'
# months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
# years_pattern = r'(20[0-9][0-9])'
# date_pattern = f'{days_pattern}-{months_pattern}-{years_pattern}'
# bank_name='SPCB'
# AMOUNT_RX = re.compile(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+\.\d+')


# def _to_number(raw: str | None) -> float:
#     """Pick the last well-formed amount from the string and convert to float.
#     Returns 0.0 if none found."""
#     if not raw:
#         return 0.0
#     s = str(raw)
#     # grab all number-like tokens (keeps commas inside thousands)
#     hits = AMOUNT_RX.findall(s.replace('\xa0', ' ').replace('\u200b', ''))
#     if not hits:
#         return 0.0
#     val = hits[-1].replace(',', '')
#     try:
#         return float(val)
#     except Exception:
#         return 0.0



# def spcb_1(pdf_paths, passwords):
#     # Initialize an empty list to store all rows
#     data_table = []


#     for pdf_path in pdf_paths:
#         all_data = []

#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     account_number=''
#                     if not pdf.pages:
#                         return {'error': 'PDF file is empty'}
                    
#                     # Extract Account Number
#                     accNo = pdf.pages[0].search(r'account\s*(?:number|no)\s*([\d]+)', regex=True, case=False)
#                     account_number = accNo[0]['groups'][0] if accNo else None
                

#                     #print(pdf_path)
#                     f_page = pdf.pages[0]  # First page
#                     words = f_page.extract_words(x_tolerance=1)
                    
#                     # Find header row containing key columns
#                     for i, word in enumerate(words):
#                         #print(f"{word['text']}: {word['x0']}")
#                         if word['text'].lower() == "withdrawals":
#                             withdrawals= word['x0']

#                         if word['text'].lower() == "deposits":
#                             deposits=word['x0']

#                         if word['text'].lower().find('balan')>-1:
#                             balance=word['x0']

#                         if word['text'].lower() == "particulars":
#                             if re.match(r"\b[0-3][0-9]-", words[i+4]['text']) and not re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
#                                 particulars=words[i+5]['x0']
#                             elif re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
#                                 particulars=words[i+6]['x0']
#                             else:
#                                 particulars=words[i+4]['x0']

#                     column_width = [
#                         ("Date", 1, particulars-5),
#                         ("Particulars", particulars-5, withdrawals),
#                         ("Withdrawals", withdrawals, deposits),
#                         ("Deposits", deposits, balance),
#                         ("Balance", balance, 2000)
#                     ]
                    
                    
#                     # Process each page
#                     for i, page in enumerate(pdf.pages):

#                         # Extract all text as words with their coordinates
#                         words = page.extract_words(x_tolerance=1)
                    
#                         # if i == 0:
#                         #     im = page.to_image(resolution=300)
#                         #     im.draw_rects(page.extract_words())
#                         #     for _, x0, x1 in column_width:
#                         #         im.draw_vlines([x0, x1], stroke="blue", stroke_width=2)
#                         #     im.save("debug_image_page2.png")
#                             #im.show()
                        
                        
#                         # Group words by their vertical position (y-coordinate)
#                         rows = {}
#                         for word in words:
                            
#                             y_pos = round(word['top'] / 10) * 4
#                             if y_pos not in rows:
#                                 rows[y_pos] = []
#                             rows[y_pos].append({
#                                 'text': word['text'],
#                                 'x0': word['x0'],
#                                 'x1': word['x1']
#                             })
                        
#                         # Process each row
#                         for y_pos in sorted(rows.keys()):
#                             row_words = rows[y_pos]
#                             row_data = {col_name: '' for col_name, _, _ in column_width}
                            
#                             for word in row_words:
#                                 word_center = (word['x0'] + word['x1']) / 2
#                                 for col_name, start, end in column_width:
#                                     if start <= word_center <= end:
#                                         if row_data[col_name]:
#                                             row_data[col_name] += ' ' + word['text']
#                                         else:
#                                             row_data[col_name] = word['text']
#                                         break
                            
#                             if any(row_data.values()):
#                                 cleaned_row = [re.sub(r"Page \d+ of \d+", "", value) for value in row_data.values()]
#                                 # Append cleaned values to all_data
#                                 all_data.append(cleaned_row)

#                 break
#             except Exception as e:
#                 # If password fails, continue to next password
#                 continue

#         date = None
#         for i in range(len(all_data)):
#             # Check for full date pattern
#             #print(all_data[i])
#             if re.search(date_pattern, str(all_data[i][0])):
#                 date = 'full_date'
#                 break
#             # Check for split date pattern
#             elif i + 2 < len(all_data) and re.search(r"\b[0-3][0-9]-", str(all_data[i][0])):
#                 date = 'split_date'
#                 break

#         #print(all_data)
#         i = 0
#         final_data = []
#         if date=='full_date':
#             while i < len(all_data):
#                 #print(all_data[i])
#                 row = []
#                 if re.search(date_pattern, str(all_data[i][0])):
#                     if (i > 0 and all_data[i - 1][0].lower()!='date'
#                         and not (re.search(date_pattern, str(all_data[i - 2][0]))
#                               or re.search(date_pattern, str(all_data[i - 1][0])))):
#                         prev_row = all_data[i - 1]
#                     else:
#                         prev_row = ['', '', '', '', '']
                        
#                     if (i + 1 < len(all_data) 
#                         and not re.search(date_pattern, str(all_data[i + 1][0])) 
#                         and not re.search(r"==========", str(all_data[i + 1][1]))):
#                         next_row = all_data[i + 1]
#                     else:
#                         next_row = ['', '', '', '', ''] 

#                     row = ["".join(x) for x in zip(prev_row, all_data[i], next_row)]

#                     #print(row)
#                     final_data.append(row)
#                 i += 1

#         if date=='split_date':
#             while i < len(all_data):
#                 x = i
#                 y = i

#                 # Find the first matching row for the day pattern
#                 for x in range(x, min(x+10, len(all_data))):
#                     if re.search(f"{days_pattern}-", str(all_data[x][0])):
#                         f_row = x
#                         break
#                 else:
#                     i += 1  # Skip to the next iteration if no match is found
#                     continue

#                 # Find the first matching row for the year pattern
#                 for y in range(y, min(y+10, len(all_data))):
#                     if re.search(years_pattern, str(all_data[y][0])):
#                         l_row = y
#                         break
#                 else:
#                     i += 1  # Skip to the next iteration if no match is found
#                     continue

#                 # Process and store the data
#                 row = ["".join(row[0] for row in all_data[f_row:l_row+1])] + \
#                     ["".join(col) for col in zip(*all_data[f_row:l_row+1])][1:]  

#                 #print(row)
#                 final_data.append(row)

#                 # Move `i` forward to skip processed rows
#                 i = l_row + 1

#         #print_tables(final_data)
#         #  format
#         # for row in final_data:
#         #     row.insert(2, "")
#         #     date_obj = datetime.strptime(row[0], "%d-%b-%Y")
#         #     row[0] = date_obj.strftime("%d-%m-%Y")
#         #     narration=row[1]
#         #     row[1] = narration[:90]
#         #     row[2] = narration[90:]
#         #     row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] is not None else 0.0
#         #     row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] is not None else 0.0
            
#         #     value = row[5].upper()
#         #     number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
#         #     if "DR" in value and "-" not in number:  # Only make negative if not already negative

#         #         row[5] = -float(number) if '.' in number else -int(number)
#         #     else:
#         #         row[5] = float(number) if '.' in number else int(number)
#         for row in final_data:
#             # ensure narration split column exists
#             row.insert(2, "")

#             # date -> dd-mm-YYYY
#             try:
#                 date_obj = datetime.strptime(row[0].strip(), "%d-%b-%Y")
#                 row[0] = date_obj.strftime("%d-%m-%Y")
#             except Exception:
#                 # if already in dd-mm-YYYY or something else, leave as-is
#                 pass

#             # narration split (safe on short rows)
#             narration = (row[1] or "").strip()
#             row[1] = narration[:90]
#             row[2] = narration[90:]

#             # numbers
#             debit_raw   = str(row[3]) if len(row) > 3 else ""
#             credit_raw  = str(row[4]) if len(row) > 4 else ""
#             balance_raw = str(row[5]) if len(row) > 5 else ""

#             row[3] = _to_number(debit_raw)      # WITHDRAWAL
#             row[4] = _to_number(credit_raw)     # DEPOSIT

#             bal = _to_number(balance_raw)
#             # make balance negative if it has DR (but don’t double-negate)
#             if re.search(r'\bDR\b', balance_raw, re.IGNORECASE) and bal > 0:
#                 bal = -bal
#             row[5] = bal


#         data_table.extend(final_data)
#         # Add account number as the first row in the table
#     account_row = [bank_name, account_number, "", "", "", ""]
#     headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
#     data_table.insert(0, headers )
#     data_table.insert(0, account_row)

#     #print_tables(data_table)
#     return data_table
    

# def is_date(date):
#     pattern = r"^([0-2][0-9]|(3)[0-1])-(0[1-9]|1[0-2])-\d{4}$"
#     return bool(re.search(pattern, date))

# def print_tables(table):
#     # for i, table in enumerate(tables):
#     #     print(f"\nTable {i + 1}:\n")
#         print(tabulate(table, headers="firstrow", tablefmt="grid"))


# # Run the extraction
# if __name__ == "__main__":
#     # Your specific parameters
#     pdf_file = [r"Z:\Temp\23.pdf"]
#     pdf_password = ["252889483"]
#     try:
#         spcb_1(pdf_file, pdf_password )
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")


# # m_spcb_1.py
# # -*- coding: utf-8 -*-
# """
# SPCB extractor (Particulars / Withdrawals / Deposits / Balance layout)

# API:
#     from pdf2excel.m_spcb_1 import spcb_1
#     tables = spcb_1([r"...\file.pdf"], ["pwd1", "pwd2"])
#     -> [
#          [
#            ["SPCB", "<account_no>", "", "", "", ""],
#            ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"],
#            ["05-04-2024","By Transfer ...", "", 0.0, 250.0, 66.04],
#            ...
#          ]
#        ]
# """

# import pdfplumber
# from tabulate import tabulate
# import re
# from datetime import datetime

# # ----------------- config / regex -----------------
# bank_name = "SPCB"

# days_pattern   = r'([0-2][0-9]|(3)[0-1])'
# months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
# years_pattern  = r'(20[0-9][0-9])'
# date_pattern   = f'{days_pattern}-{months_pattern}-{years_pattern}'

# # AMOUNT_RX = re.compile(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+\.\d+')
# FOOTER_RX = re.compile(r'Page\s+\d+\s+of\s+\d+', re.I)

# # Safety margins / binning
# GUTTER  = 2.0    # px margin kept inside each column to avoid boundary bleed
# ROW_BIN = 1.5    # finer row grouping than the previous coarse bucketing

# # Accept comma-grouped (with optional decimals), decimals, or plain integers (>=1 digit)
# AMOUNT_RX = re.compile(r'-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+|-?\d+')

# def _num(s: str) -> float:
#     if not s: return 0.0
#     try: return float(s.replace(',', ''))
#     except: return 0.0

# def _to_number(raw: str | None) -> float:
#     if not raw: return 0.0
#     hits = AMOUNT_RX.findall(str(raw).replace('\xa0',' ').replace('\u200b',''))
#     return _num(hits[-1]) if hits else 0.0

# def _unsplit_numbers(s: str) -> str:
#     s = (s or "").replace('\xa0',' ').replace('\u200b',' ')
#     prev = None
#     while prev != s:
#         prev = s
#         # join "<1-4 digits> <1-3 digits>.<2 digits>" -> one amount
#         s = re.sub(r'(\d{1,4})\s+(\d{1,3}\.\d{2})\b', r'\1\2', s)
#     return s

# def _amount_tokens(s: str) -> list[str]:
#     return AMOUNT_RX.findall(_unsplit_numbers(s or ""))

# def _last_amount(text: str) -> float:
#     toks = _amount_tokens(text)
#     return float(toks[-1].replace(',', '')) if toks else 0.0
# def _last_amount_in_row(cells: list[str]) -> float:
#     """Rightmost numeric token on the WHOLE row (after healing splits) = balance."""
#     joined = " ".join(str(x or "") for x in cells[:6])
#     hits = _amount_tokens(joined)
#     return _num(hits[-1]) if hits else 0.0

# def _second_last_amount_in_row(cells: list[str]) -> float:
#     """Second-rightmost = transaction amount (Deposit/Withdrawal)."""
#     joined = " ".join(str(x or "") for x in cells[:6])
#     hits = _amount_tokens(joined)
#     return _num(hits[-2]) if len(hits) >= 2 else 0.0


# def _pick_dc_from_cells(narr: str, debit_raw: str, credit_raw: str) -> tuple[float,float]:
#     """Prefer what’s inside the cells. If both empty, decide via narration keywords."""
#     d = _to_number(debit_raw)
#     c = _to_number(credit_raw)
#     if d and not c: return d, 0.0
#     if c and not d: return 0.0, c
#     if d and c:     # both populated (rare) – keep the larger and zero other
#         return (d, 0.0) if d >= c else (0.0, c)
#     # both empty: infer using narration
#     if re.search(r'\b(WDL|DEBIT|ATM|POS|CHG)\b', narr, re.I):
#         return _second_last_amount_in_row([narr,debit_raw,credit_raw]), 0.0
#     # default treat as credit (e.g., “By / NEFT / UPI / TRF / RTGS”)
#     return 0.0, _second_last_amount_in_row([narr,debit_raw,credit_raw])


# def _pick_dc(debit_raw: str, credit_raw: str) -> tuple[float, float]:
#     """Decide which side (debit/credit) to keep to avoid double-filling."""
#     d_hits = AMOUNT_RX.findall(debit_raw or "")
#     c_hits = AMOUNT_RX.findall(credit_raw or "")

#     if d_hits and not c_hits:
#         return _to_number(debit_raw), 0.0
#     if c_hits and not d_hits:
#         return 0.0, _to_number(credit_raw)
#     if d_hits and c_hits:
#         # Prefer semantic hints if present
#         if re.search(r'\b(WDL|DEBIT|ATM|POS)\b', debit_raw, re.I):
#             return _to_number(debit_raw), 0.0
#         if re.search(r'\b(CR|BY|NEFT|UPI|RTGS|IMPS|DEP|TRANSFER IN)\b', credit_raw, re.I):
#             return 0.0, _to_number(credit_raw)
#         # fallback: take the larger magnitude as the txn, zero the other
#         d = _to_number(debit_raw)
#         c = _to_number(credit_raw)
#         return (d, 0.0) if d >= c else (0.0, c)
#     return 0.0, 0.0


# def _is_separator_row(row_like: list[str]) -> bool:
#     text = " ".join([str(x or "") for x in row_like])
#     return bool(re.search(r'=+', text)) or bool(FOOTER_RX.search(text))


# def _safe_date_to_ddmmyyyy(s: str) -> str:
#     s = (s or "").strip()
#     # SPCB header usually is dd-MMM-YYYY
#     try:
#         return datetime.strptime(s, "%d-%b-%Y").strftime("%d-%m-%Y")
#     except Exception:
#         # if already dd-mm-YYYY or other, just return as-is
#         return s


# def print_tables(table):
#     print(tabulate(table, headers="firstrow", tablefmt="grid"))


# # ----------------- main -----------------
# def spcb_1(pdf_paths, passwords):
#     data_table = []          # final table rows (after formatting)
#     account_number_last = "" # keep the last seen account number

#     for pdf_path in pdf_paths:
#         all_data = []  # raw rows per page: ["Date","Particulars","Withdrawals","Deposits","Balance"]

#         # try passwords in order (+ None for no password)
#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     if not pdf.pages:
#                         continue

#                     # ------------ account number (best-effort) ------------
#                     account_number = ""
#                     try:
#                         accNo = pdf.pages[0].search(
#                             r'account\s*(?:number|no)\s*([\d]+)', regex=True, case=False
#                         )
#                         account_number = accNo[0]['groups'][0] if accNo else ""
#                     except Exception:
#                         account_number = ""
#                     if account_number:
#                         account_number_last = account_number

#                     # ------------ detect columns on first page ------------
#                     f_page = pdf.pages[0]
#                     words = f_page.extract_words(x_tolerance=1)

#                     withdrawals_x = deposits_x = balance_x = particulars_x = None
#                     for i, w in enumerate(words):
#                         t = (w['text'] or '').strip().lower()
#                         if t == "withdrawals":
#                             withdrawals_x = w['x0']
#                         elif t == "deposits":
#                             deposits_x = w['x0']
#                         elif "balan" in t:
#                             balance_x = w['x0']
#                         elif t == "particulars":
#                             # handle possible split date under header
#                             try:
#                                 if (re.match(r"\b[0-3][0-9]-", words[i+4]['text']) and
#                                    not re.match(r"\b[A-Za-z]{3}-", words[i+5]['text'])):
#                                     particulars_x = words[i+5]['x0']
#                                 elif re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
#                                     particulars_x = words[i+6]['x0']
#                                 else:
#                                     particulars_x = words[i+4]['x0']
#                             except Exception:
#                                 particulars_x = w['x0'] + 60  # fallback offset

#                     # minimal fallbacks if header detection failed
#                     if particulars_x is None: particulars_x = 150
#                     if withdrawals_x is None: withdrawals_x = particulars_x + 260
#                     if deposits_x   is None: deposits_x   = withdrawals_x + 120
#                     if balance_x    is None: balance_x    = deposits_x + 120

#                     # Use midpoints between header x's so one number doesn't straddle boundaries
#                     sep1 = (particulars_x + withdrawals_x) / 2.0
#                     sep2 = (withdrawals_x + deposits_x) / 2.0
#                     sep3 = (deposits_x   + balance_x)    / 2.0

#                     column_width = [
#                         ("Date",         1,          particulars_x - 5),
#                         ("Particulars",  particulars_x - 5,  sep1),
#                         ("Withdrawals",  sep1,              sep2),
#                         ("Deposits",     sep2,              sep3),
#                         ("Balance",      sep3,              2000),
#                     ]

#                     # ------------ iterate pages ------------
#                     for page in pdf.pages:
#                         words = page.extract_words(x_tolerance=1)
#                         # group by fine Y bins
#                         rows = {}
#                         for w in words:
#                             y_pos = round(w['top'] / ROW_BIN) * ROW_BIN
#                             rows.setdefault(y_pos, []).append({'text': w['text'], 'x0': w['x0'], 'x1': w['x1']})

#                         # build row cells using guttered bounds
#                         for y in sorted(rows.keys()):
#                             row_words = rows[y]
#                             row_data = {col: '' for col, _, _ in column_width}

#                             for w in row_words:
#                                 cx = (w['x0'] + w['x1']) / 2.0
#                                 for col_name, start, end in column_width:
#                                     if (start + GUTTER) <= cx < (end - GUTTER):
#                                         row_data[col_name] = (row_data[col_name] + ' ' + w['text']).strip()
#                                         break

#                             # Skip empty/garbage rows
#                             vals = list(row_data.values())
#                             if not any(vals):
#                                 continue
#                             if _is_separator_row(vals):
#                                 continue
#                             if vals[0].strip().lower() in ("date",) or vals[1].strip().lower() in ("particulars",):
#                                 continue

#                             cleaned = [FOOTER_RX.sub("", v or "").strip() for v in vals]
#                             all_data.append(cleaned)

#                 # if we reach here, the password worked
#                 break
#             except Exception:
#                 # try next password
#                 continue

#         # ------------ stitch rows into transactions ------------
#         # detect date style
#         mode = None   # 'full_date' or 'split_date'
#         for i in range(len(all_data)):
#             if re.search(date_pattern, str(all_data[i][0])):
#                 mode = 'full_date'
#                 break
#             elif i + 2 < len(all_data) and re.search(r"\b[0-3][0-9]-", str(all_data[i][0])):
#                 mode = 'split_date'
#                 break

#         final_data = []
#         i = 0
#         if mode == 'full_date':
#             while i < len(all_data):
#                 row_now = all_data[i]
#                 if re.search(date_pattern, str(row_now[0])):
#                     # try to glue previous/next lines of same transaction if they’re not date-lines
#                     prev_row = ['', '', '', '', '']
#                     next_row = ['', '', '', '', '']

#                     if i > 0:
#                         a = all_data[i-1]
#                         if (a[0].lower() != 'date' and
#                             not re.search(date_pattern, str(a[0])) and
#                             not re.search(r"=+", str(a[1]))):
#                             prev_row = a

#                     if i + 1 < len(all_data):
#                         b = all_data[i+1]
#                         if (not re.search(date_pattern, str(b[0])) and
#                             not re.search(r"=+", str(b[1]))):
#                             next_row = b

#                     glued = ["".join(x) for x in zip(prev_row, row_now, next_row)]
#                     final_data.append(glued)
#                 i += 1

#         elif mode == 'split_date':
#             while i < len(all_data):
#                 x = i
#                 y = i

#                 # find first 'dd-' row in vicinity
#                 found = False
#                 for x in range(x, min(x+10, len(all_data))):
#                     if re.search(f"{days_pattern}-", str(all_data[x][0])):
#                         f_row = x
#                         found = True
#                         break
#                 if not found:
#                     i += 1
#                     continue

#                 # find first 'YYYY' row in vicinity (end of split date)
#                 found = False
#                 for y in range(y, min(y+10, len(all_data))):
#                     if re.search(years_pattern, str(all_data[y][0])):
#                         l_row = y
#                         found = True
#                         break
#                 if not found:
#                     i += 1
#                     continue

#                 # stitch split-date block
#                 row = ["".join(r[0] for r in all_data[f_row:l_row+1])] + \
#                       ["".join(col) for col in zip(*all_data[f_row:l_row+1])][1:]
#                 final_data.append(row)
#                 i = l_row + 1

#         # ------------ normalize / format rows ------------
#         for row in final_data:
#             # ensure narration2 exists
#             if len(row) < 6:
#                 # pad to [Date, Particulars, W, D, B] first
#                 row += [''] * (5 - len(row))
#             # insert narration-2
#             row.insert(2, "")

#             # date
#             row[0] = _safe_date_to_ddmmyyyy(row[0])

#             # narration split
#             narration = (row[1] or "").strip()
#             row[1] = narration[:90]
#             row[2] = narration[90:]
            
#             # numbers (robust)
#             # ---- amounts: use only amount cells, then fix by narration if needed ----
#             debit_raw   = str(row[3]) if len(row) > 3 else ""
#             credit_raw  = str(row[4]) if len(row) > 4 else ""
#             balance_raw = str(row[5]) if len(row) > 5 else ""
#             narr_all    = (row[1] + " " + row[2]).strip().lower()

#             # read each cell independently
#             d_val = _last_amount(debit_raw)
#             c_val = _last_amount(credit_raw)
#             bal   = _last_amount(balance_raw)

#             # fallback for balance (if the balance cell was missed)
#             if not bal:
#                 bal = _last_amount(" ".join([debit_raw, credit_raw, balance_raw]))

#             # classify by narration keywords (used for tie-breaks or when numbers
#             # slipped into the wrong side)
#             creditish = (
#                 "trf fr" in narr_all or
#                 re.search(r'\b(by|neft|upi|imps|credit|cr\s*int|by\s+cash|by\s+clearing|refund|reversal|cemtex\s*dep|interest)\b', narr_all, re.I)
#             )
#             debitish = (
#                 "trf to" in narr_all or
#                 re.search(r'\b(wdl|debit|pos|atm|charge|charges|sms|dr\s*thru\s*chq|to\s+clearing)\b', narr_all, re.I)
#             )

#             # if number is on the "wrong" side, flip using narration cues
#             if d_val and not c_val and creditish:
#                 c_val, d_val = d_val, 0.0
#             elif c_val and not d_val and debitish:
#                 d_val, c_val = c_val, 0.0
#             elif d_val and c_val:
#                 # both filled (rare). Prefer narration, else keep the larger and zero the other
#                 if debitish and not creditish:
#                     c_val = 0.0
#                 elif creditish and not debitish:
#                     d_val = 0.0
#                 else:
#                     if d_val >= c_val:
#                         c_val = 0.0
#                     else:
#                         d_val = 0.0

#             # DR suffix on balance → negative
#             if re.search(r'\bDR\b', balance_raw, re.I) and bal > 0:
#                 bal = -bal

#             row[3], row[4], row[5] = d_val, c_val, bal

#         # accumulate for this pdf
#         data_table.extend(final_data)

#     # ------------ header + account row ------------
#     account_row = [bank_name, account_number_last or "", "", "", "", ""]
#     headers     = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
#     data_table.insert(0, headers)
#     data_table.insert(0, account_row)

#     return data_table


# # quick manual run
# if __name__ == "__main__":
#     pdf_file = [r"Z:\Temp\23.pdf"]
#     pdf_password = ["252889483"]
#     try:
#         tbl = spcb_1(pdf_file, pdf_password)
#         print_tables(tbl)
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")



# m_spcb_1.py
# -*- coding: utf-8 -*-
"""
SPCB extractor (Particulars / Withdrawals / Deposits / Balance layout)

API:
    from pdf2excel.m_spcb_1 import spcb_1
    tables = spcb_1([r"...\file.pdf"], ["pwd1", "pwd2"])
    -> [
         [
           ["SPCB", "<account_no>", "", "", "", ""],
           ["DATE","NARRATION 1","NARRATION 2","WITHDRAWAL","DEPOSIT","CL. BALANCE"],
           ["05-04-2024","By Transfer ...", "", 0.0, 250.0, 66.04],
           ...
         ]
       ]
"""

import pdfplumber
from tabulate import tabulate
import re
from datetime import datetime

# ----------------- config / regex -----------------
bank_name = "SPCB"

days_pattern   = r'([0-2][0-9]|(3)[0-1])'
months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
years_pattern  = r'(20[0-9][0-9])'
date_pattern   = f'{days_pattern}-{months_pattern}-{years_pattern}'

FOOTER_RX = re.compile(r'Page\s+\d+\s+of\s+\d+', re.I)

# Safety margins / binning
# GUTTER  = 2.0    # px margin kept inside each column to avoid boundary bleed
# ROW_BIN = 1.5    # finer row grouping

GUTTER  = 3.0   # was 2.0
ROW_BIN = 1.0   # was 1.5, a bit tighter row grouping

# Amounts:
#  1) comma-grouped: 1,234 or 1,234.56
#  2) decimals: 12.34
#  3) short plain integers: up to 6 digits (avoid 12-digit UPI refs)
AMOUNT_RX = re.compile(r'-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d{1,2}|-?\d{1,6}\b')
AMOUNT_STANDALONE_RX = re.compile(
    r'(?<![A-Za-z@._/-])(?:' + AMOUNT_RX.pattern + r')(?![A-Za-z@._/-])'
)

NON_AMT_CHARS_RX = re.compile(r'[A-Za-z@._/-]')  # anything that looks like text/symbols

REF_LIKE_WORDS_RX = re.compile(r'\b(neft|upi|imps|rtgs|chq|cheque|rtgs|ecs|n[eE]ft|qr|pos|atm)\b', re.I)

def _looks_like_reference_row(narr: str) -> bool:
    """Row has payment/ref keywords -> integers like 191101 are probably refs, not amounts."""
    return bool(REF_LIKE_WORDS_RX.search(narr or ""))

def _pick_amount_from_cell(cell_text: str, narr_all: str) -> float:
    """
    Choose the most plausible monetary value from a single cell.
    Preference order:
      1) tokens with decimal (e.g., 264.26)
      2) tokens with thousands separators (e.g., 936,900)
      3) small plain integers (<= 4 digits) like 3000
    Rejection:
      - 5–6 digit plain integers in 'reference-like' rows (NEFT/UPI/CHQ/RTGS) are ignored.
    """
    txt = _unsplit_numbers(cell_text or "")
    toks = AMOUNT_RX.findall(txt)

    if not toks:
        return 0.0

    # Normalize
    def norm(tok: str) -> str: return tok.replace(',', '')
    has_decimal = [t for t in toks if '.' in t]
    has_commas  = [t for t in toks if ',' in t and '.' not in t]
    plain_ints  = [t for t in toks if '.' not in t and ',' not in t]

    # 1) decimals – choose the rightmost decimal token
    if has_decimal:
        return _num(norm(has_decimal[-1]))

    # 2) comma-grouped – choose rightmost
    if has_commas:
        return _num(norm(has_commas[-1]))

    # 3) plain ints – filter out ref-like 5–6 digit ids if row looks like a reference
    if plain_ints:
        ints = [t for t in plain_ints]
        # prefer small (≤4 digits) first (e.g., 3000)
        small = [t for t in ints if 1 <= len(t.replace('-', '')) <= 4]
        if small:
            return _num(norm(small[-1]))

        # otherwise, if row doesn’t look like a reference, allow 5–6 digit ints
        if not _looks_like_reference_row(narr_all):
            mid = [t for t in ints if 5 <= len(t.replace('-', '')) <= 6]
            if mid:
                return _num(norm(mid[-1]))

        # else, as a last resort, take the rightmost plain int (may still be a ref)
        return _num(norm(ints[-1]))

    return 0.0

def _rescue_amount_from_narration(narr_text: str) -> float:
    """
    Try to pull the last plausible money value from narration text.
    Rules:
      - prefer a decimal (…xx.yy),
      - otherwise allow small integers (<=4 digits) like 1500/3000,
      - ignore long plain integers (likely refs).
    """
    txt = _unsplit_numbers(narr_text or "")
    toks = AMOUNT_RX.findall(txt)
    if not toks:
        return 0.0
    # prefer decimals at the end
    decs = [t for t in toks if "." in t]
    if decs:
        return _num(decs[-1].replace(",", ""))
    # then small ints (<=4 digits)
    small = [t for t in toks if "." not in t and "," not in t and len(t) <= 4]
    if small:
        return _num(small[-1])
    return 0.0

# def _non_amount_text(s: str) -> str:
#     """Return only the non-numeric content from a cell (keeps words, drops pure amounts)."""
#     s = _unsplit_numbers(s or "")
#     # remove standalone amounts
#     s = AMOUNT_RX.sub(" ", s)
#     # collapse spaces
#     s = re.sub(r'\s{2,}', ' ', s).strip()
#     return s

def _non_amount_text(s: str) -> str:
    s = _unsplit_numbers(s or "")
    # remove only stand-alone amounts; keep digits that belong to IDs/handles/emails
    s = AMOUNT_STANDALONE_RX.sub(" ", s)
    return re.sub(r'\s{2,}', ' ', s).strip()

def _merge_spill_into_particulars(particulars: str, w_cell: str, d_cell: str) -> str:
    """
    If Withdrawals/Deposits cells contain any non-amount text (UPI ids, NEFT refs, bank codes),
    append that back into the narration so we don't lose it.
    """
    extras = []
    for side in (w_cell, d_cell):
        if NON_AMT_CHARS_RX.search(side or ""):
            t = _non_amount_text(side or "")
            if t:
                extras.append(t)
    if extras:
        return (particulars or "").strip() + " " + " ".join(extras)
    return particulars

def _num(s: str) -> float:
    if not s: return 0.0
    try: return float(s.replace(',', ''))
    except: return 0.0

# def _unsplit_numbers(s: str) -> str:
#     """Heal numbers that got split by stray spaces inside the same token."""
#     s = (s or "").replace('\xa0',' ').replace('\u200b',' ')
#     prev = None
#     while prev != s:
#         prev = s
#         # join "<1-4 digits> <1-3 digits>.<2 digits>" -> one amount
#         s = re.sub(r'(\d{1,4})\s+(\d{1,3}\.\d{2})\b', r'\1\2', s)
#         # join comma groups like "1 , 234 . 56"
#         s = re.sub(r'(\d)\s*,\s*(\d{3})', r'\1,\2', s)
#         s = re.sub(r'(\d)\s*\.\s*(\d{2})\b', r'\1.\2', s)
#     return s

def _unsplit_numbers(s: str) -> str:
    """Heal numbers that got split by stray spaces *inside the same token*,
    without gluing refs like '...0002 64.26'."""
    s = (s or "").replace('\xa0',' ').replace('\u200b',' ')
    prev = None
    while prev != s:
        prev = s
        # SAFER: join "12 345.67" but NOT "...0002 64.26"
        s = re.sub(r'(?<!\d)(\d{1,3})\s+(\d{1,3}\.\d{2})(?!\d)', r'\1\2', s)
        # keep existing healing for "1 , 234" and "123 . 45"
        s = re.sub(r'(\d)\s*,\s*(\d{3})', r'\1,\2', s)
        s = re.sub(r'(\d)\s*\.\s*(\d{2})\b', r'\1.\2', s)
    return s

def _amount_tokens(s: str) -> list[str]:
    return AMOUNT_RX.findall(_unsplit_numbers(s or ""))

def _last_amount(text: str) -> float:
    toks = _amount_tokens(text)
    return float(toks[-1].replace(',', '')) if toks else 0.0

def _last_amount_in_row(cells: list[str]) -> float:
    joined = " ".join(str(x or "") for x in cells[:6])
    hits = _amount_tokens(joined)
    return _num(hits[-1]) if hits else 0.0

def _second_last_amount_in_row(cells: list[str]) -> float:
    joined = " ".join(str(x or "") for x in cells[:6])
    hits = _amount_tokens(joined)
    return _num(hits[-2]) if len(hits) >= 2 else 0.0

def _is_separator_row(row_like: list[str]) -> bool:
    text = " ".join([str(x or "") for x in row_like])
    return bool(re.search(r'=+', text)) or bool(FOOTER_RX.search(text))

def _safe_date_to_ddmmyyyy(s: str) -> str:
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%d-%b-%Y").strftime("%d-%m-%Y")
    except Exception:
        return s
def _clean_spaces(s: str) -> str:
    return re.sub(r'[ \t]{2,}', ' ', (s or '').replace('\xa0', ' ')).strip()

def _split_narration_words(text: str, max_len: int = 110):
    text = text or ""
    if len(text) <= max_len:
        return text, ""
    cut = text.rfind(" ", 0, max_len)
    if cut < int(max_len * 0.6):
        cut = max_len
    return text[:cut].strip(), text[cut:].strip()

def print_tables(table):
    print(tabulate(table, headers="firstrow", tablefmt="grid"))

# ----------------- main -----------------
def spcb_1(pdf_paths, passwords):
    data_table = []
    account_number_last = ""

    for pdf_path in pdf_paths:
        all_data = []  # raw rows: ["Date","Particulars","Withdrawals","Deposits","Balance"]

        # try passwords in order (+ None)
        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        continue

                    # ---- account number (best-effort) ----
                    account_number = ""
                    try:
                        accNo = pdf.pages[0].search(
                            r'account\s*(?:number|no)\s*([\d]+)', regex=True, case=False
                        )
                        account_number = accNo[0]['groups'][0] if accNo else ""
                    except Exception:
                        pass
                    if account_number:
                        account_number_last = account_number

                    # ---- detect columns on first page ----
                    f_page = pdf.pages[0]
                    words = f_page.extract_words(x_tolerance=1)

                    # ---- detect columns (robust to singular/plural/case) ----
                    withdrawals_x = deposits_x = balance_x = particulars_x = None
                    for i, w in enumerate(words):
                        t = (w["text"] or "").strip().lower()

                        # match "withdrawal" or "withdrawals" (any casing, even WithDrawal)
                        # if re.fullmatch(r"with\s*drawals?", t):
                        #     withdrawals_x = w["x0"]
                        if re.fullmatch(r"withdrawals?", t):
                            withdrawals_x = w["x0"]

                        # match "deposit" or "deposits"
                        elif re.fullmatch(r"deposits?", t):
                            deposits_x = w["x0"]

                        # match "balance" (allow partial like "balan")
                        elif re.match(r"balan", t):
                            balance_x = w["x0"]

                        # robust "particulars" anchor (your existing special-case kept)
                        elif t == "particulars":
                            try:
                                if (re.match(r"\b[0-3][0-9]-", words[i+4]['text'])
                                    and not re.match(r"\b[A-Za-z]{3}-", words[i+5]['text'])):
                                    particulars_x = words[i+5]['x0']
                                elif re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
                                    particulars_x = words[i+6]['x0']
                                else:
                                    particulars_x = words[i+4]['x0']
                            except Exception:
                                particulars_x = w['x0'] + 60  # fallback


                    # withdrawals_x = deposits_x = balance_x = particulars_x = None
                    # for i, w in enumerate(words):
                    #     t = (w['text'] or '').strip().lower()
                    #     if t == "withdrawals":
                    #         withdrawals_x = w['x0']
                    #     elif t == "deposits":
                    #         deposits_x = w['x0']
                    #     elif "balan" in t:
                    #         balance_x = w['x0']
                    #     elif t == "particulars":
                    #         try:
                    #             if (re.match(r"\b[0-3][0-9]-", words[i+4]['text']) and
                    #                not re.match(r"\b[A-Za-z]{3}-", words[i+5]['text'])):
                    #                 particulars_x = words[i+5]['x0']
                    #             elif re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
                    #                 particulars_x = words[i+6]['x0']
                    #             else:
                    #                 particulars_x = words[i+4]['x0']
                    #         except Exception:
                    #             particulars_x = w['x0'] + 60

                    if particulars_x is None: particulars_x = 150
                    if withdrawals_x is None: withdrawals_x = particulars_x + 260
                    if deposits_x   is None: deposits_x   = withdrawals_x + 120
                    if balance_x    is None: balance_x    = deposits_x + 120

                    # use midpoints between headers
                    sep1 = (particulars_x + withdrawals_x) / 2.0
                    sep2 = (withdrawals_x + deposits_x) / 2.0
                    sep3 = (deposits_x   + balance_x)    / 2.0

                    column_width = [
                        ("Date",         1,                 particulars_x - 5),
                        ("Particulars",  particulars_x - 5, sep1),
                        ("Withdrawals",  sep1,              sep2),
                        ("Deposits",     sep2,              sep3),
                        ("Balance",      sep3,              2000),
                    ]

                    # ---- iterate pages ----
                    def _detect_columns_on_page(pg):
                        words = pg.extract_words(x_tolerance=1)
                        w_x = d_x = b_x = p_x = None
                        for i, w in enumerate(words):
                            t = (w["text"] or "").strip().lower()
                            if re.fullmatch(r"withdrawals?", t):
                                w_x = w["x0"]
                            elif re.fullmatch(r"deposits?", t):
                                d_x = w["x0"]
                            elif re.match(r"balan", t):
                                b_x = w["x0"]
                            elif t == "particulars":
                                try:
                                    if (re.match(r"\b[0-3][0-9]-", words[i+4]['text'])
                                        and not re.match(r"\b[A-Za-z]{3}-", words[i+5]['text'])):
                                        p_x = words[i+5]['x0']
                                    elif re.match(r"\b[A-Za-z]{3}-", words[i+5]['text']):
                                        p_x = words[i+6]['x0']
                                    else:
                                        p_x = words[i+4]['x0']
                                except Exception:
                                    p_x = w['x0'] + 60
                        return p_x, w_x, d_x, b_x

                    for page in pdf.pages:
                        words = page.extract_words(x_tolerance=1)
                        rows = {}
                        for w in words:
                            y_pos = round(w['top'] / ROW_BIN) * ROW_BIN
                            rows.setdefault(y_pos, []).append({'text': w['text'], 'x0': w['x0'], 'x1': w['x1']})

                        for y in sorted(rows.keys()):
                            row_words = rows[y]
                            row_data = {col: '' for col, _, _ in column_width}

                            for w in row_words:
                                cx = (w['x0'] + w['x1']) / 2.0
                                for col_name, start, end in column_width:
                                    if (start + GUTTER) <= cx < (end - GUTTER):
                                        row_data[col_name] = (row_data[col_name] + ' ' + w['text']).strip()
                                        break

                            vals = list(row_data.values())
                            if not any(vals):
                                continue
                            if _is_separator_row(vals):
                                continue
                            if vals[0].strip().lower() in ("date",) or vals[1].strip().lower() in ("particulars",):
                                continue

                            cleaned = [FOOTER_RX.sub("", v or "").strip() for v in vals]
                            all_data.append(cleaned)

                # password worked
                break
            except Exception:
                continue

        # ---- stitch rows into transactions ----
        mode = None
        for i in range(len(all_data)):
            if re.search(date_pattern, str(all_data[i][0])):
                mode = 'full_date'
                break
            elif i + 2 < len(all_data) and re.search(r"\b[0-3][0-9]-", str(all_data[i][0])):
                mode = 'split_date'
                break

        final_data = []
        i = 0
        if mode == 'full_date':
            while i < len(all_data):
                row_now = all_data[i]
                if re.search(date_pattern, str(row_now[0])):
                    prev_row = ['','','','','']
                    next_row = ['','','','','']

                    if i > 0:
                        a = all_data[i-1]
                        if (a[0].lower() != 'date' and
                            not re.search(date_pattern, str(a[0])) and
                            not re.search(r"=+", str(a[1]))):
                            prev_row = a

                    if i + 1 < len(all_data):
                        b = all_data[i+1]
                        if (not re.search(date_pattern, str(b[0])) and
                            not re.search(r"=+", str(b[1]))):
                            next_row = b

                    # IMPORTANT: join with spaces (prevents number gluing!)
                    glued = [" ".join(x).strip() for x in zip(prev_row, row_now, next_row)]
                    final_data.append(glued)
                i += 1

        elif mode == 'split_date':
            while i < len(all_data):
                x = i
                y = i

                found = False
                for x in range(x, min(x+10, len(all_data))):
                    if re.search(f"{days_pattern}-", str(all_data[x][0])):
                        f_row = x
                        found = True
                        break
                if not found:
                    i += 1
                    continue

                found = False
                for y in range(y, min(y+10, len(all_data))):
                    if re.search(years_pattern, str(all_data[y][0])):
                        l_row = y
                        found = True
                        break
                if not found:
                    i += 1
                    continue

                # join with spaces
                row = [" ".join(r[0] for r in all_data[f_row:l_row+1]).strip()] + \
                      [" ".join(col).strip() for col in zip(*all_data[f_row:l_row+1])][1:]
                final_data.append(row)
                i = l_row + 1

        prev_balance = None

        # ---- normalize / format rows ----
        for row in final_data:
            if len(row) < 5:
                row += [''] * (5 - len(row))
            row.insert(2, "")  # narration-2

            row[0] = _safe_date_to_ddmmyyyy(row[0])

            # narration_full = (row[1] or "").strip()
            # row[1] = narration_full[:90]
            # row[2] = narration_full[90:]

            # debit_raw   = str(row[3]) if len(row) > 3 else ""
            # credit_raw  = str(row[4]) if len(row) > 4 else ""
            # balance_raw = str(row[5]) if len(row) > 5 else ""
            # pull any non-amount text that leaked into W/D cells back into narration
            debit_raw   = str(row[3]) if len(row) > 3 else ""
            credit_raw  = str(row[4]) if len(row) > 4 else ""
            balance_raw = str(row[5]) if len(row) > 5 else ""

            narration_full = _merge_spill_into_particulars((row[1] or "").strip(), debit_raw, credit_raw)

            # word-safe split into Narration1 / Narration2
            def _split_narration_words(text: str, max_len: int = 85):
                if len(text) <= max_len:
                    return text, ""
                cut = text.rfind(" ", 0, max_len)
                if cut < int(max_len * 0.7):
                    cut = max_len
                return text[:cut].strip(), text[cut:].strip()

            row[1], row[2] = _split_narration_words(narration_full, max_len=85)
            
            # Row-wide, lowercased narration used for heuristics
            # narr_all = (row[1] + " " + row[2]).lower()

            # # Strictly pick from each cell first
            # # d_val = _pick_amount_from_cell(debit_raw, narr_all)
            # # c_val = _pick_amount_from_cell(credit_raw, narr_all)

            # # # Only if cell is empty AND the other side is zero, try a guarded row-wide fallback
            # # if d_val == 0.0 and c_val == 0.0:
            # #     # try to rescue from the W/D cell texts concatenated (not the whole narration)
            # #     rescue_d = _pick_amount_from_cell(" ".join([debit_raw]), narr_all)
            # #     rescue_c = _pick_amount_from_cell(" ".join([credit_raw]), narr_all)
            # #     if rescue_d: d_val = rescue_d
            # #     if rescue_c: c_val = rescue_c
            
            # # Strictly pick from each cell first
            # d_val = _pick_amount_from_cell(debit_raw, narr_all)
            # c_val = _pick_amount_from_cell(credit_raw, narr_all)

            # # --- NEW guarded rescues from narration tail ---
            # # Case A: Withdrawal cell has no amount but row reads like a debit
            # if d_val == 0.0 and debitish:
            #     d_val = _rescue_amount_from_narration(" ".join([row[1], row[2]])) or d_val

            # # Case B: Deposit cell has no amount but row reads like a credit
            # if c_val == 0.0 and creditish:
            #     c_val = _rescue_amount_from_narration(" ".join([row[1], row[2]])) or c_val

            # # Balance: prefer balance cell; guarded fallback to the three amount cells
            # bal = _pick_amount_from_cell(balance_raw, narr_all)
            # if bal == 0.0:
            #     bal = _pick_amount_from_cell(" ".join([debit_raw, credit_raw, balance_raw]), narr_all)


            # # d_val = _last_amount(debit_raw)
            # # c_val = _last_amount(credit_raw)

            # # bal = _last_amount(balance_raw)
            # # if not bal:
            # #     bal = _last_amount(" ".join([debit_raw, credit_raw, balance_raw]))
            # # … your creditish/debitish flip logic … 
            # # DR handling …
            # # row[3], row[4], row[5] = d_val, c_val, bal
            # # if not bal:
            # #     bal = _last_amount_in_row([row[1], row[2], debit_raw, credit_raw, balance_raw])

            # # narr_all = (row[1] + " " + row[2]).lower()
            # narr_all = (row[1] + " " + row[2]).lower()

            # # credits: BY/NEFT IN/IMPS IN/RTGS IN/TRF FR/CR INT/refund/reversal/cash deposit/clearing
            # creditish = bool(re.search(
            #     r'\b('
            #     r'by(?!\s*tfr\s*to)'          # "By ..." but not "by tfr to"
            #     r'|neft\s*in'
            #     r'|imps\s*in'
            #     r'|rtgs\s*in'
            #     r'|trf\s*fr'
            #     r'|cr\s*int'
            #     r'|credit'
            #     r'|refund'
            #     r'|reversal'
            #     r'|cemtex\s*dep'
            #     r'|by\s+cash'
            #     r'|by\s+clearing'
            #     r')\b', narr_all))

            # # debits: WDL/TRF TO/DEBIT/POS/ATM/charges/clearing-to, etc.
            # debitish = bool(re.search(
            #     r'\b('
            #     r'wdl|withdrawal'
            #     r'|trf\s*to'
            #     r'|debit\b'
            #     r'|pos\b'
            #     r'|atm\b'
            #     r'|charge|charges|sms'
            #     r'|to\s+clearing'
            #     r')\b', narr_all))

            
            # # creditish = (
            # #     "trf fr" in narr_all or
            # #     re.search(r'\b(by|neft|upi|imps|credit|cr\s*int|by\s+cash|by\s+clearing|refund|reversal|interest)\b', narr_all, re.I)
            # # )
            # # debitish = (
            # #     "trf to" in narr_all or
            # #     re.search(r'\b(wdl|debit|pos|atm|charge|charges|sms|dr\s*thru\s*chq|to\s+clearing)\b', narr_all, re.I)
            # # )

            # if d_val and not c_val and creditish:
            #     c_val, d_val = d_val, 0.0
            # elif c_val and not d_val and debitish:
            #     d_val, c_val = c_val, 0.0
            # elif d_val and c_val:
            #     if debitish and not creditish:
            #         c_val = 0.0
            #     elif creditish and not debitish:
            #         d_val = 0.0
            #     else:
            #         if d_val >= c_val: c_val = 0.0
            #         else: d_val = 0.0

            # Row-wide, lowercased narration used for heuristics
            narr_all = (row[1] + " " + row[2]).lower()

            # --- define orientation flags *before* using them ---
            creditish = bool(re.search(
                r'\b('
                r'by(?!\s*tfr\s*to)'      # "By ..." but not "by tfr to"
                r'|neft\s*in'
                r'|imps\s*in'
                r'|rtgs\s*in'
                r'|trf\s*fr'
                r'|cr\s*int'
                r'|credit'
                r'|refund'
                r'|reversal'
                r'|cemtex\s*dep'
                r'|by\s+cash'
                r'|by\s+clearing'
                r')\b', narr_all))

            debitish = bool(re.search(
                r'\b('
                r'wdl|withdrawal'
                r'|trf\s*to'
                r'|debit\b'
                r'|pos\b'
                r'|atm\b'
                r'|charge|charges|sms'
                r'|to\s+clearing'
                r')\b', narr_all))

            # --- pick amounts from cells first ---
            d_val = _pick_amount_from_cell(debit_raw, narr_all)
            c_val = _pick_amount_from_cell(credit_raw, narr_all)

            # --- guarded rescue from narration tail when the cell is empty ---
            if d_val == 0.0 and debitish:
                d_val = _rescue_amount_from_narration(row[1] + " " + row[2]) or d_val
            if c_val == 0.0 and creditish:
                c_val = _rescue_amount_from_narration(row[1] + " " + row[2]) or c_val

            # --- balance (cell first, then guarded fallback) ---
            bal = _pick_amount_from_cell(balance_raw, narr_all)
            if bal == 0.0:
                bal = _pick_amount_from_cell(" ".join([debit_raw, credit_raw, balance_raw]), narr_all)

            # --- flip logic ---
            if d_val and not c_val and creditish:
                c_val, d_val = d_val, 0.0
            elif c_val and not d_val and debitish:
                d_val, c_val = c_val, 0.0
            elif d_val and c_val:
                if debitish and not creditish:
                    c_val = 0.0
                elif creditish and not debitish:
                    d_val = 0.0
                else:
                    if d_val >= c_val: c_val = 0.0
                    else: d_val = 0.0

            if re.search(r'\bDR\b', balance_raw, re.I) and bal > 0:
                bal = -bal

            row[3], row[4], row[5] = d_val, c_val, bal

        data_table.extend(final_data)

    # ---- header + account row ----
    account_row = [bank_name, account_number_last or "", "", "", "", ""]
    headers     = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
    data_table.insert(0, headers)
    data_table.insert(0, account_row)
    return data_table

# quick manual run
if __name__ == "__main__":
    pdf_file = [r"Z:\Temp\23.pdf"]
    pdf_password = ["252889483"]
    try:
        tbl = spcb_1(pdf_file, pdf_password)
        print_tables(tbl)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
