# import xlsxwriter
# import os
# from datetime import datetime
# from dateutil.parser import parse
# import time

# def bank_excel(final_data, detail, file_directory):

#     # Generate output file name
#     file_name = os.path.splitext(os.path.basename(file_directory))[0]
#     output_file_name = f"{file_name}.xlsx"
#     download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
#     output_path = os.path.join(download_folder, output_file_name)

#     # Create Excel file using XlsxWriter
#     try:
#         wb = xlsxwriter.Workbook(output_path)
        
#         # Define formats
#         bold = wb.add_format({'bold': True})
#         currency_format = wb.add_format({'num_format': '#,##0.00'})
#         red_font = wb.add_format({'font_color': 'red'})
        
#         # Ensure final_data is a list of tables (even if single table)
#         tables = final_data if isinstance(final_data[0], list) and isinstance(final_data[0][0], list) else [final_data]

#         # Iterate over each table
#         for table_idx, t_table in enumerate(tables):

#             bank_Name=t_table[0][0]
#             account_no=t_table[0][1]
#             table=t_table[2:]

#             # Create sheet name: table[0][0]-last4chars (BANK-last4)
#             sheet_name = f"{bank_Name}-{str(account_no)[-4:]}" if len(table[0]) > 1 else f"Sheet{table_idx + 1}"
#             ws = wb.add_worksheet(sheet_name[:31])  # Excel sheet name limit is 31 chars
            
#             # Write metadata (BANK and Account Number)
#             ws.write("A1", bank_Name, bold)  # BANK
#             ws.write("B1", account_no if len(table[0]) > 1 else "N/A")  # Account Number

#             # Write headers
#             headers = ['Date','Narration1', 
#                       'Narration2', 'Withdrawals', 'Deposits', 'Balance']
#             for col_num, header in enumerate(headers):
#                 ws.write(1, col_num, header, bold)
            
#             # Generate sequential Sr. numbers per month
#             sr_counters = {}
            
#             # Write data (skip first two rows: metadata and headers)
#             for row_num, row_data in enumerate(table, start=2):  # Start at row 4 (0-based)
 
#                 ws.write(row_num, 0, row_data[0])  # Date
#                 ws.write(row_num, 1, row_data[1])  # Narration 1
#                 ws.write(row_num, 2, row_data[2])  # Narration 2
#                 ws.write(row_num, 3, row_data[3] if row_data[3] else 0.0, currency_format)
#                 ws.write(row_num, 4, row_data[4] if row_data[4] else 0.0, currency_format)
#                 ws.write(row_num, 5, row_data[5], currency_format)  # Balance
                
#                 diff = 0
#                 if row_num > 2 and len(row_data) > 3 and len(table[row_num - 3]) > 3:
#                     diff = round((table[row_num - 3][5] + row_data[4] - row_data[3]) - row_data[5], 2)

#                 if diff:
#                     ws.set_row(row_num, None, red_font)
            
            
#         # Adjust column widths
#         column_widths = [ 15, 40, 30,15,15,15]
#         for i, width in enumerate(column_widths):
#             ws.set_column(i, i, width)
            
#         wb.close()
#         print(f"Data extracted and saved to {output_path}")
        
#         time.sleep(1)
#         if os.path.exists(output_path):
#             os.startfile(output_path)
#         else:
#             print(f"File not found: {output_path}")
    
#     except PermissionError:
#         print(f"Permission denied: Cannot write to {output_path}")
#     except Exception as e:
#         print(f"Error occurred: {e}")


# accounts/pdf2excel/bank_excel.py
# import os
# import xlsxwriter

# def bank_excel(final_data, detail, output_dir, filename="Extracted_Bank.xlsx"):
#     """
#     Write the Excel next to the input PDFs (output_dir) and return the full path.
#     Do NOT try to open the file (this runs on the server).
#     """
#     os.makedirs(output_dir, exist_ok=True)
#     output_path = os.path.join(output_dir, filename)

#     # Normalize "tables" structure
#     tables = final_data if (isinstance(final_data, list) and final_data and
#                             isinstance(final_data[0], list) and isinstance(final_data[0][0], list)) \
#              else [final_data]

#     wb = xlsxwriter.Workbook(output_path)
#     try:
#         bold = wb.add_format({'bold': True})
#         currency_format = wb.add_format({'num_format': '#,##0.00'})
#         red_font = wb.add_format({'font_color': 'red'})

#         for table_idx, t_table in enumerate(tables):
#             # Expect: [ [bank_name, account_no], [maybe headers/meta], [rows…] ]
#             bank_name = t_table[0][0] if t_table and t_table[0] else f"Bank{table_idx+1}"
#             account_no = t_table[0][1] if t_table and t_table[0] and len(t_table[0]) > 1 else ""
#             table_rows = t_table[2:] if len(t_table) > 2 else []

#             sheet_name = f"{bank_name}-{str(account_no)[-4:]}" if account_no else f"Sheet{table_idx+1}"
#             ws = wb.add_worksheet(sheet_name[:31])

#             # Headers
#             ws.write("A1", bank_name, bold)
#             ws.write("B1", account_no or "N/A")

#             headers = ['Date', 'Narration1', 'Narration2', 'Withdrawals', 'Deposits', 'Balance']
#             for col_num, header in enumerate(headers):
#                 ws.write(1, col_num, header, bold)

#             # Data
#             for row_idx, row in enumerate(table_rows, start=2):
#                 # guard for short rows
#                 c = lambda i, default="": (row[i] if i < len(row) else default)
#                 ws.write(row_idx, 0, c(0))                           # Date (as text)
#                 ws.write(row_idx, 1, c(1))                           # Narration1
#                 ws.write(row_idx, 2, c(2))                           # Narration2
#                 ws.write_number(row_idx, 3, float(c(3, 0) or 0), currency_format)
#                 ws.write_number(row_idx, 4, float(c(4, 0) or 0), currency_format)
#                 ws.write_number(row_idx, 5, float(c(5, 0) or 0), currency_format)

#                 # Simple anomaly flagging vs prior row balance (if present)
#                 if row_idx > 2 and len(table_rows[row_idx - 3]) >= 6:
#                     try:
#                         prev_bal = float(table_rows[row_idx - 3][5] or 0)
#                         dep = float(c(4, 0) or 0)
#                         wdl = float(c(3, 0) or 0)
#                         bal = float(c(5, 0) or 0)
#                         diff = round((prev_bal + dep - wdl) - bal, 2)
#                         if diff:
#                             ws.set_row(row_idx, None, red_font)
#                         # optionally write diff in a hidden col if needed
#                     except Exception:
#                         pass

#             # Widths per sheet
#             ws.set_column(0, 0, 15)  # Date
#             ws.set_column(1, 1, 40)  # Narration1
#             ws.set_column(2, 2, 30)  # Narration2
#             ws.set_column(3, 5, 15)  # Amounts

#     finally:
#         wb.close()

#     # IMPORTANT: return path for the view
#     return output_path


import os
import re
import xlsxwriter

INVALID_SHEET_CHARS = r'[:\\/?*\[\]]'

def _safe_float(x, default=0.0):
    # Handles None, "", "1,234.56", "1 234.56"
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace(" ", "")
    if not s:
        return default
    try:
        return float(s)
    except Exception:
        return default

def _sanitize_sheet_name(name: str) -> str:
    name = re.sub(INVALID_SHEET_CHARS, "-", str(name))
    name = name.strip() or "Sheet"
    return name[:31]

def bank_excel(final_data, detail, output_dir, filename="Extracted_Bank.xlsx"):
    """
    Writes Excel in output_dir and returns full path.
    final_data expected shape:
      [
        [ [bank_name, account_no], <optional meta row>, [rows... each row list of at least 6 cols] ],
        ...
      ]
    """

    # 🔥 NEW: normalize dict-based parsers (SBI-3)
    if isinstance(final_data, dict) and "rows" in final_data:
        final_data = [
            [
                [final_data.get("bank", "Bank"), ""],  # head row
                [],                                     # meta row placeholder
                *final_data.get("rows", [])
            ]
        ]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    # Normalize into list-of-tables
    tables = (
        final_data
        if (isinstance(final_data, list) and final_data and
            isinstance(final_data[0], list) and isinstance(final_data[0][0], list))
        else [final_data]
    )
   

    wb = xlsxwriter.Workbook(output_path)
    try:
        bold = wb.add_format({'bold': True})
        currency_format = wb.add_format({'num_format': '#,##0.00'})
        red_font = wb.add_format({'font_color': 'red'})

        used_sheet_names = set()

        for table_idx, t_table in enumerate(tables):
            if not t_table or not isinstance(t_table, list):
                continue

            # Header row with bank/account
            head = t_table[0] if t_table and isinstance(t_table[0], list) else []
            bank_name = head[0] if len(head) >= 1 and head[0] else f"Bank{table_idx+1}"
            account_no = head[1] if len(head) >= 2 else ""

            # Data rows (skip head + optional meta)
            table_rows = t_table[2:] if len(t_table) > 2 else []
            if not table_rows:
                # nothing to write — skip sheet creation
                continue

            # Build sheet name, sanitize, dedupe
            suffix = f"-{str(account_no)[-4:]}" if account_no else f"-{table_idx+1}"
            base_name = _sanitize_sheet_name(f"{bank_name}{suffix}") or f"Sheet{table_idx+1}"
            sheet_name = base_name
            i = 2
            while sheet_name in used_sheet_names:
                # ensure uniqueness
                candidate = f"{base_name[:29]}_{i}"
                sheet_name = candidate[:31]
                i += 1
            used_sheet_names.add(sheet_name)

            ws = wb.add_worksheet(sheet_name)

            # Top labels
            ws.write("A1", str(bank_name), bold)
            ws.write("B1", str(account_no) if account_no else "N/A")

            # Headers
            headers = ['Date', 'Narration1', 'Narration2', 'Withdrawals', 'Deposits', 'Balance']
            for col, h in enumerate(headers):
                ws.write(1, col, h, bold)

            # Data rows
            for r_idx, row in enumerate(table_rows, start=2):
                row = row if isinstance(row, list) else []
                # Safe getters
                def c(i, default=""):
                    return row[i] if i < len(row) else default

                ws.write(r_idx, 0, str(c(0, "")))             # Date (text)
                ws.write(r_idx, 1, str(c(1, "")))             # Narration1
                ws.write(r_idx, 2, str(c(2, "")))             # Narration2

                wdl = _safe_float(c(3, 0))
                dep = _safe_float(c(4, 0))
                bal = _safe_float(c(5, 0))

                ws.write_number(r_idx, 3, wdl, currency_format)
                ws.write_number(r_idx, 4, dep, currency_format)
                ws.write_number(r_idx, 5, bal, currency_format)

                # Anomaly flag vs previous row balance
                if r_idx > 2:
                    prev = table_rows[r_idx - 3] if (r_idx - 3) < len(table_rows) else None
                    if isinstance(prev, list) and len(prev) >= 6:
                        prev_bal = _safe_float(prev[5], 0)
                        diff = round((prev_bal + dep - wdl) - bal, 2)
                        if diff != 0:
                            ws.set_row(r_idx, None, red_font)

            # Column widths
            ws.set_column(0, 0, 15)  # Date
            ws.set_column(1, 1, 40)  # Narration1
            ws.set_column(2, 2, 30)  # Narration2
            ws.set_column(3, 5, 15)  # Amounts

    finally:
        wb.close()

    return output_path
