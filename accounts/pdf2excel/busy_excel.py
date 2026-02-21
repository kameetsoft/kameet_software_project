# # busy_excel.py
# import xlsxwriter
# import os
# from dateutil.parser import parse

# def busy_excel(final_data, detail, output_dir, filename="Extracted_Busy.xlsx"):
#     """
#     Create Busy-format Excel next to the input PDFs (output_dir) and return the full path.
#     Do NOT try to open the file (this runs on the server).
#     """
#     os.makedirs(output_dir, exist_ok=True)
#     output_path = os.path.join(output_dir, filename)

#     incl_cash = ['Cash', 'ATM', 'Self']
#     excl_cash = ['Chrgs', 'chrg', 'charge', 'charges', 'chg', 'upi', 'transfer']

#     # Normalize "tables" structure like bank_excel
#     tables = final_data if (isinstance(final_data, list) and final_data and
#                             isinstance(final_data[0], list) and isinstance(final_data[0][0], list)) \
#              else [final_data]

#     wb = xlsxwriter.Workbook(output_path)
#     try:
#         bold = wb.add_format({'bold': True})
#         currency_format = wb.add_format({'num_format': '#,##0.00'})
#         red_font = wb.add_format({'font_color': 'red'})

#         for table_idx, t_table in enumerate(tables):
#             # Expect first two rows are metadata: [bank_name, account_no], [headers...]
#             bank_Name = t_table[0][0] if t_table and t_table[0] else f"BANK{table_idx+1}"
#             account_no = t_table[0][1] if t_table and len(t_table[0]) > 1 else "NA"
#             table = t_table[2:]  # actual data rows

#             account_name = ''
#             if detail:
#                 for item in detail:
#                     if item[0] is not None:
#                         entry = item[0]
#                         if len(entry) >= 4 and str(entry[3]) == str(account_no):
#                             account_name = entry[2]

#             sheet_name = f"{bank_Name}-{str(account_no)[-4:]}" if table else f"Sheet{table_idx+1}"
#             ws = wb.add_worksheet(sheet_name[:31])

#             # Metadata
#             ws.write("A1", bank_Name, bold)
#             ws.write("B1", account_no)

#             # Headers
#             headers = ['Type', 'Sr.', 'Bank', 'Date', 'Account', 'Narration1',
#                        'Narration2', 'Withdrawals', 'Deposits', 'Cash Withdrawals',
#                        'Cash Deposits', 'Balance']
#             for col_num, header in enumerate(headers):
#                 ws.write(1, col_num, header, bold)

#             # Sr counters per month
#             sr_counters = {}

#             # Data
#             for row_idx, row in enumerate(table, start=2):
#                 # row: [date, narr1, narr2, debit, credit, balance]
#                 date_obj = parse(row[0], dayfirst=True)
#                 month_key = f"{bank_Name}{str(account_no)[-2:]}-{date_obj.strftime('%b')}"
#                 sr_counters[month_key] = sr_counters.get(month_key, 0) + 1
#                 sr_number = f"{month_key}-{sr_counters[month_key]:04d}"

#                 narr1 = row[1] or ""
#                 narr2 = row[2] or ""
#                 debit = row[3] or 0.0
#                 credit = row[4] or 0.0
#                 balance = row[5] or 0.0

#                 ws.write(row_idx, 0, 'Main')
#                 ws.write(row_idx, 1, sr_number)
#                 ws.write(row_idx, 2, account_name)
#                 ws.write(row_idx, 3, row[0])         # keep as text
#                 ws.write(row_idx, 4, '*Unknown*')
#                 ws.write(row_idx, 5, narr1)
#                 ws.write(row_idx, 6, narr2)

#                 is_cash = (any(k.lower() in (narr1 + narr2).lower() for k in incl_cash)
#                            and not any(k.lower() in (narr1 + narr2).lower() for k in excl_cash))

#                 if is_cash:
#                     ws.write(row_idx, 9, debit, currency_format)
#                     ws.write(row_idx, 10, credit, currency_format)
#                 else:
#                     ws.write(row_idx, 7, debit, currency_format)
#                     ws.write(row_idx, 8, credit, currency_format)

#                 ws.write(row_idx, 11, balance, currency_format)

#                 # Diff highlight (simple check with previous balance row)
#                 if row_idx > 2 and len(table[row_idx - 3]) > 5:
#                     prev_balance = table[row_idx - 3][5] or 0.0
#                     diff = round((prev_balance + credit - debit) - balance, 2)
#                     if diff:
#                         ws.set_row(row_idx, None, red_font)

#             # Widths
#             widths = [5, 16, 35, 10, 35, 55, 25, 15, 15, 15, 15, 15]
#             for i, w in enumerate(widths):
#                 ws.set_column(i, i, w)

#     finally:
#         wb.close()

#     # IMPORTANT: return the file path for the view
#     return output_path


# busy_excel.py
import os
import xlsxwriter
from dateutil.parser import parse


def busy_excel(final_data, detail, output_dir,
               filename="Extracted_Busy.xlsx",
               bank_ledger_name=None):
    """
    Create Busy-format Excel next to the input PDFs (output_dir) and return the full path.
    bank_ledger_name: string for the 'Bank' column (Busy ledger name).
                      If None, falls back to detail[] mapping or bank name.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    incl_cash = ['Cash', 'ATM', 'Self']
    excl_cash = ['Chrgs', 'chrg', 'charge', 'charges', 'chg', 'upi', 'transfer']

    # Normalize "tables" structure like bank_excel
    tables = (
        final_data
        if (isinstance(final_data, list) and final_data
            and isinstance(final_data[0], list)
            and isinstance(final_data[0][0], list))
        else [final_data]
    )

    wb = xlsxwriter.Workbook(output_path)
    try:
        bold = wb.add_format({'bold': True})
        currency_format = wb.add_format({'num_format': '#,##0.00'})
        red_font = wb.add_format({'font_color': 'red'})

        for table_idx, t_table in enumerate(tables):
            # Expect first two rows are metadata: [bank_name, account_no], [headers...]
            bank_Name = t_table[0][0] if t_table and t_table[0] else f"BANK{table_idx+1}"
            account_no = t_table[0][1] if t_table and len(t_table[0]) > 1 else "NA"
            table = t_table[2:]  # actual data rows

            # ------------- figure out what to put in 'Bank' column -------------
            # 1) start with value passed from view (Busy ledger name)
            account_name = bank_ledger_name or ""

            # 2) if not given, try old "detail" mapping
            if not account_name and detail:
                for item in detail:
                    if item and item[0] is not None:
                        entry = item[0]
                        if len(entry) >= 4 and str(entry[3]) == str(account_no):
                            account_name = entry[2]
                            break

            # 3) last fallback – use the plain bank name from metadata
            if not account_name:
                account_name = bank_Name
            # -------------------------------------------------------------------

            sheet_name = f"{bank_Name}-{str(account_no)[-4:]}" if table else f"Sheet{table_idx+1}"
            ws = wb.add_worksheet(sheet_name[:31])

            # Metadata (top-left)
            ws.write("A1", bank_Name, bold)
            ws.write("B1", account_no)

            # Headers
            headers = [
                'Type', 'Sr.', 'Bank', 'Date', 'Account', 'Narration1',
                'Narration2', 'Withdrawals', 'Deposits', 'Cash Withdrawals',
                'Cash Deposits', 'Balance',
            ]
            for col_num, header in enumerate(headers):
                ws.write(1, col_num, header, bold)

            # Sr counters per month
            sr_counters = {}

            # Data rows
            for row_idx, row in enumerate(table, start=2):
                # row: [date, narr1, narr2, debit, credit, balance]
                date_obj = parse(row[0], dayfirst=True)
                month_key = f"{bank_Name}{str(account_no)[-2:]}-{date_obj.strftime('%b')}"
                sr_counters[month_key] = sr_counters.get(month_key, 0) + 1
                sr_number = f"{month_key}-{sr_counters[month_key]:04d}"

                narr1 = row[1] or ""
                narr2 = row[2] or ""
                debit = row[3] or 0.0
                credit = row[4] or 0.0
                balance = row[5] or 0.0

                ws.write(row_idx, 0, 'Main')          # Type
                ws.write(row_idx, 1, sr_number)       # Sr.
                ws.write(row_idx, 2, account_name)    # Bank  ✅ now filled
                ws.write(row_idx, 3, row[0])          # Date (text)
                ws.write(row_idx, 4, '*Unknown*')     # Account
                ws.write(row_idx, 5, narr1)           # Narration1
                ws.write(row_idx, 6, narr2)           # Narration2

                is_cash = (
                    any(k.lower() in (narr1 + narr2).lower() for k in incl_cash)
                    and not any(k.lower() in (narr1 + narr2).lower() for k in excl_cash)
                )

                if is_cash:
                    ws.write(row_idx, 9, debit, currency_format)   # Cash Withdrawals
                    ws.write(row_idx, 10, credit, currency_format) # Cash Deposits
                else:
                    ws.write(row_idx, 7, debit, currency_format)   # Withdrawals
                    ws.write(row_idx, 8, credit, currency_format)  # Deposits

                ws.write(row_idx, 11, balance, currency_format)    # Balance

                # Diff highlight (simple check with previous balance row)
                if row_idx > 2 and len(table[row_idx - 3]) > 5:
                    prev_balance = table[row_idx - 3][5] or 0.0
                    diff = round((prev_balance + credit - debit) - balance, 2)
                    if diff:
                        ws.set_row(row_idx, None, red_font)

            # Column widths
            widths = [5, 16, 35, 10, 35, 55, 25, 15, 15, 15, 15, 15]
            for i, w in enumerate(widths):
                ws.set_column(i, i, w)

    finally:
        wb.close()

    # IMPORTANT: return the file path for the view
    return output_path
