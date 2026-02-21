# from loguru import logger
# import pdfplumber
# from tabulate import tabulate
# import re
# from PIL import Image
# from dateutil import parser
# from dateutil.parser import parse
# from dateutil.parser import ParserError



# # Date pattern for DD/MM/YYYY format
# date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
# bank_name = 'SBI Bank'

# def sbi_1(pdf_paths, passwords):
#     logger.info("Starting PDF processing for SBI Bank.")
#     # Initialize an empty list to store all rows

#     data_table = []
#     for pdf_path in pdf_paths:
#         logger.info(f"Processing file: {pdf_path}")
#         account_tables = []
#         account_numbers = []
        
#         for password in passwords + [None]:
#             try:
#                 with pdfplumber.open(pdf_path, password=password) as pdf:
#                     if not pdf.pages:
#                         logger.error(f"PDF file {pdf_path} is empty.")
#                         return {'error': 'PDF file is empty'}

#                     all_data = []
#                     # Process each page
#                     for page in pdf.pages:
#                         logger.debug(f"Processing page {page.page_number} of {pdf_path}.")
#                         tables = page.extract_tables({
#                             "vertical_strategy": "lines",
#                             "horizontal_strategy": "lines",
#                             "intersection_tolerance": 3,
#                         })
#                         # for table in tables:
#                         #     for row in table:
#                         #         # print("\n")
#                         #         # print(row)
#                         #         all_data.append(row)



#                     #print_tables(all_data)

#                     # Extract account numbers and separate data
#                     current_account = None

#                         #print(combined_text)
#                     pattern = r"ACCOUNT\s*\n\s*(X{7}\d{4}"
#                     account_match = page.search(pattern, regex=True, case=False)    
#                     #account_match = re.search(r'\s*Account (\d+)', " ".join(row),re.IGNORECASE)
                    
#                     if account_match:
#                         current_account = account_match.group(1) #account_match.group(0).lower().replace("account", "").replace(" ", "")  # Changed to group(0) to capture the full match
#                         if current_account not in account_numbers:
#                             logger.info(f"Found new account number: {current_account}")
#                             account_numbers.append(current_account)
#                             account_tables.append([])
#                     elif current_account:
#                         acc_idx = account_numbers.index(current_account)
#                         account_tables[acc_idx].append(row)
#                 break
#             except Exception as e:
#                 logger.error(f"Error processing PDF file {pdf_path} with password '{password}': {str(e)}")
#                 continue

#         # Process each account's data

#         final_data = []
#         for acc_idx, account_number in enumerate(account_numbers):
#             logger.info(f"Processing data for account number: {account_number}")
#             table_data = []
#             account_data = account_tables[acc_idx]
#             i = 0
#             for i, row in enumerate(account_data):
#                 #print(row)
#                 f_row=i
#                 l_row=i

#                 if is_date(account_data[i][0]) and not ("Opening Balance" in account_data[i][1] or "Closing Balance" in account_data[i][1]):
#                     row = account_data[i]
              
#                     table_data.append(row)

#                     i =l_row+1


#             # Format the data
#             for row in table_data:
#                 #print(row)
#                 parsed_date = parser.parse(row[0], dayfirst=True)
#                 row[0] = parsed_date.strftime("%d-%m-%Y")

#                 narration1 = row[2].replace("\n", " ")
#                 narration2 = row[1].replace("\n", " ")
#                 row[1] = narration1[:90]
#                 row[2] = narration1[90:]+"  " + narration2

#                 deposit = row[3]
#                 withdrawal = row[4]
#                 row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(withdrawal))) and withdrawal is not None else 0.0
#                 row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(deposit))) and deposit is not None else 0.0

    
#                 value = row[5].upper()
#                 number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
#                 if "DR" in value and "-" not in number:  # Only make negative if not already negative
#                     row[5] = -float(number) if '.' in number else -int(number)
#                 else:
#                     row[5] = float(number) if '.' in number else int(number)

#                 #print(row)
#             # Add account number as the first row in the table
#             account_row = [bank_name, account_number, "", "", "", ""]
#             headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
        
#             # for row in table_data:
#             #     print(row)
#             # Check if the account number table already exists
#             account_exists = False
#             for idx, existing_table in enumerate(data_table):
#                 if existing_table[0][1] == account_number:  # Compare account numbers
#                     #print(f"Account Number: {account_number}, Appending to Table Index: {idx}")
#                     account_exists = True
#                     data_table[idx].extend(table_data)  # Append table_data to the existing table at this index
#                     break

#             if not account_exists:
#                 logger.info(f"Creating new table for account number: {account_number}")
#                 # If the account number table does not exist, create a new one
#                 data_table.append([account_row, headers] + table_data)
#     logger.info("Finished processing all PDFs.")
#         # Print tables with account number as part of the table
#         #print_tables(data_table)
#     return data_table

# def is_date(date_str):
#     try:
#         # Ensure the string has at least 3 parts (to enforce year, month, and day)
#         if len(re.findall(r'\d+', date_str)) < 3:
#             return False

#         parsed_date = parse(date_str, dayfirst=True, fuzzy=False)
        
#         return True  # Now we know it's a full date

#     except (ParserError, ValueError, TypeError):
#         logger.warning(f"Invalid date string encountered: {date_str}")
#         return False

# def print_tables(tables):
#     for table_data in tables:
#         if len(table_data) < 2:  # Ensure there are at least headers and data
#             account_number = table_data[0][1] if table_data else "Unknown"
#             logger.warning(f"Account {account_number} has insufficient data to display.")
#             continue
#         logger.info(f"Displaying table for account: {table_data[0][1]}")
#         print(tabulate(table_data, tablefmt="grid"))

# # Run the extraction
# if __name__ == "__main__":
#     logger.info("Starting the script.")
#     pdf_files = [r"E:\Python\PDF\SBI-1.pdf",
#                 #r"E:\Python\Pdf2Xls F\PDF\BOB\BOBC3.pdf",
#                  ]
#     logger.debug(f"PDF files to process: {pdf_files}")
#     pdf_password = ["sdfssffs", "1003021003651", "asfafdafaeee"]
#     try:
#         final_data = sbi_1(pdf_files, pdf_password)
#         logger.info("PDF processing completed successfully.")
#     except Exception as e:
#         logger.critical(f"An error occurred: {str(e)}")

from loguru import logger
import pdfplumber, re
from dateutil import parser
from dateutil.parser import ParserError

bank_name = "SBI Bank"
# accept 04-04-24 or 04/04/2024
DATE_RX = re.compile(r"\b\d{2}[-/]\d{2}[-/]\d{2,4}\b")
ACCOUNT_HDR_RX = re.compile(
    r"(SAVING ACCOUNT|CURRENT ACCOUNT)\s+(X{4,}\d{3,6})",
    re.IGNORECASE
)

def _to_float(x):
    s = re.sub(r"[^\d.-]", "", str(x or "")).strip()
    if s in ("", "-", "--", "."): 
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def sbi_1(pdf_paths, passwords):
    logger.info("Starting PDF processing for SBI Bank.")
    data_table = []

    for pdf_path in pdf_paths:
        logger.info(f"Processing file: {pdf_path}")
        account_numbers, account_tables = [], []

        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        logger.error(f"PDF file {pdf_path} is empty.")
                        return {"error": "PDF file is empty"}

                    current_account = None

                    for page in pdf.pages:
                        logger.debug(f"Processing page {page.page_number} of {pdf_path}.")

                        # --- find masked account number on page text ---
                        # text = page.extract_text() or ""
                        # examples: XXXXXXXX1234 / XXXXXXX1234 / XXXXX 1234
                        # m = re.search(r"X{4,}\s*\d{3,6}", text)
                        # if m:
                        #     acct = m.group(0).replace(" ", "")
                        #     if acct not in account_numbers:
                        #         account_numbers.append(acct)
                        #         account_tables.append([])
                        #     current_account = acct
                        text = page.extract_text() or ""

                        # 🔥 Detect account section header
                        m = ACCOUNT_HDR_RX.search(text)
                        if m:
                            acct_type = m.group(1).upper()
                            acct = m.group(2).replace(" ", "")
                            current_account = acct

                            if acct not in account_numbers:
                                account_numbers.append(acct)
                                account_tables.append([])

                        elif current_account is None:
                            # fallback to single "Unknown" account if none detected yet
                            current_account = "Unknown"
                            if not account_numbers:
                                account_numbers.append(current_account)
                                account_tables.append([])

                        # --- extract tables & push transaction rows ---
                        tables = page.extract_tables({
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "intersection_tolerance": 3,
                        }) or []

                        for tbl in tables:
                            for r in tbl:
                                if not r or not r[0]:
                                    continue
                                first = str(r[0]).strip()
                                if not DATE_RX.match(first):
                                    continue
                                # Normalize date
                                try:
                                    dt = parser.parse(first, dayfirst=True).strftime("%d-%m-%Y")
                                except (ParserError, ValueError):
                                    continue

                                # SBI columns: Date | Transaction Reference | Ref.No./Chq.No. | Credit | Debit | Balance
                                trans_ref = (r[1] or "").replace("\n", " ").strip()
                                ref_no    = (r[2] or "").replace("\n", " ").strip()
                                # credit    = _to_float(r[3] if len(r) > 3 else 0)   # deposit
                                # debit     = _to_float(r[4] if len(r) > 4 else 0)   # withdrawal
                                # balance   = _to_float(r[5] if len(r) > 5 else (r[-1] if len(r) else 0))
                                amounts = []

                                for cell in r:
                                    if not cell:
                                        continue
                                    cell = str(cell).strip()
                                    if cell in ("-", "—", ""):
                                        continue
                                    if re.search(r"\d", cell):
                                        val = _to_float(cell)
                                        if val != 0:
                                            amounts.append(val)

                                # SBI rule:
                                # last number = balance
                                # remaining one number = credit OR debit

                                credit = debit = 0.0
                                balance = amounts[-1] if amounts else 0.0

                                if len(amounts) >= 2:
                                    txn_amt = amounts[-2]

                                    # SBI logic:
                                    # if balance increased → credit
                                    # else → debit
                                    # prev_balance = account_tables[idx][-1][5] if account_tables[idx] else 0.0

                                    # if balance > prev_balance:
                                    #     credit = txn_amt
                                    # else:
                                    #     debit = txn_amt
                                    idx = account_numbers.index(current_account)

                                    prev_balance = (
                                        account_tables[idx][-1][5]
                                        if account_tables[idx] and len(account_tables[idx][-1]) >= 6
                                        else 0.0
                                    )

                                    if balance > prev_balance:
                                        credit = txn_amt
                                    else:
                                        debit = txn_amt

                                # Your output schema:
                                row_out = [dt, trans_ref[:90], (trans_ref[90:] + "  " + ref_no).strip(), debit, credit, balance]

                                idx = account_numbers.index(current_account)
                                account_tables[idx].append(row_out)

                break  # password worked
            except Exception as e:
                logger.error(f"Error processing PDF file {pdf_path} with password '{password}': {str(e)}")
                continue

        # assemble tables for this PDF
        for acct, rows in zip(account_numbers, account_tables):
            if not rows:
                continue
            account_row = [bank_name, acct, "", "", "", ""]
            headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]

            # if same account already present, append; else create new
            merged = False
            for existing in data_table:
                if existing and existing[0][1] == acct:
                    existing.extend(rows)
                    merged = True
                    break
            if not merged:
                data_table.append([account_row, headers] + rows)

    logger.info("Finished processing all PDFs.")
    return data_table
