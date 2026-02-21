import pdfplumber
from tabulate import tabulate
import re
from PIL import Image as PILImage  # Renamed to avoid conflict with pdfplumber's Image
from dateutil import parser
from dateutil.parser import parse, ParserError

# Date pattern for DD/MM/YYYY format
date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
bank_name = 'SARVODAYA CO-OP BANK LTD'

def sarvoday_1(pdf_paths, passwords):
    # Initialize an empty list to store all rows
    data_table = []
    
    for pdf_path in pdf_paths:
        account_tables = ['']  # List to store tables per account
        account_numbers = ['']  # List to store account numbers
        
        # Try each password (including None for unencrypted PDFs)
        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        return {'error': 'PDF file is empty'}
                    
                    # Extract the first page to determine header positions
                    f_page = pdf.pages[0]
                    header_positions = {}

                    # Define column headers
                    columns = ["Date", "Particulars", "Chq No.", "Value Date", "Tran ID", "Debit", "Credit", "Closing Balance"]
                    for idx, column in enumerate(columns[:-1]):  # Exclude last column to avoid IndexError
                        search_result = f_page.search(f'{column}\s*{columns[idx+1]}', regex=True)
                        if search_result:
                            header_positions[column] = (search_result[0]["x0"], search_result[0]["x1"])
                
                    # Assign default positions if not found
                    c1_x0, c1_x1 = header_positions.get(columns[0], (0, 50))
                    c2_x0, c2_x1 = header_positions.get(columns[1], (50, 200))
                    c3_x0, c3_x1 = header_positions.get(columns[2], (200, 250))
                    c4_x0, c4_x1 = header_positions.get(columns[3], (250, 300))
                    c5_x0, c5_x1 = header_positions.get(columns[4], (300, 400))
                    c6_x0, c6_x1 = header_positions.get(columns[5], (400, 500))
                    c7_x0, c7_x1 = header_positions.get(columns[6], (500, 600))
                    c8_x0, c8_x1 = header_positions.get(columns[7], (600, 700))

                    column_width = [
                        ("Date", c1_x0, c2_x0),
                        ("Particulars", c2_x0, c3_x0),
                        ("Chq No.", c3_x0, c4_x0),
                        ("Value Date", c4_x0, c5_x0),
                        ("Tran ID", c5_x0, c5_x0 + 100),
                        ("Debit", c5_x0 + 100, c6_x1),
                        ("Credit", c6_x1, c7_x1),
                        ("Closing Balance", c7_x1, c8_x1)
                    ]
  
                    # Process each page
                    for page in pdf.pages:
                        # Extract raw text to find account number
                        words = page.extract_text_simple()
                        current_account = None
                        if words:
                            for word in words.splitlines():
                                pattern = r"(?:Account Number|AccountNo|Account No|Cash Credit Account)\s*:\s*(\d+)"
                                account_match = re.search(pattern, word, re.IGNORECASE)
                                if account_match:
                                    current_account = account_match.group(1)
                                    break
                        # If no account number found, use the last known one
                        if not current_account and account_numbers[-1]:
                            current_account = account_numbers[-1]
                        
                        # Extract tables using line-based detection
                        tables = page.extract_tables({
                            "vertical_strategy": "explicit",
                            "horizontal_strategy": "lines",
                            "explicit_vertical_lines": [col[1] for col in column_width] + [column_width[-1][2]],
                            "intersection_tolerance": 10,
                        })
                        
                        # Create page image with annotations for debugging
                        page_image = page.to_image(resolution=200)
                        debug_image = page_image.draw_vlines(
                            [col[1] for col in column_width] + [column_width[-1][2]] if column_width else [],
                            stroke_width=2,
                            stroke=(255, 0, 0)  # Red vertical lines
                        )
                        
                        # Save the debug image
                        output_path = f"{pdf_path}_debug_page_{pdf.pages.index(page) + 1}.png"
                        debug_image.save(output_path)
                        # Uncomment the line below for debugging if needed
                        # debug_image.show()

                        for table in tables:
                            # Remove empty rows inline
                            table = [row for row in table if any(cell and isinstance(cell, str) and cell.strip() for cell in row)]
                            if table and len(table) > 0:
                                num_columns = len(table[0])
                                
                                # Process tables with 5 or 7 columns
                                if num_columns in (5, 7):
                                    if "date" in table[0][0].strip().lower():
                                        table_content = table[1:]  # Skip header row
                                    else:
                                        table_content = table  # Use full table if no header
                                    
                                    # Link table content to an account
                                    if current_account:
                                        if current_account not in account_numbers:
                                            account_numbers.append(current_account)
                                            account_tables.append(table_content)
                                        else:
                                            acc_idx = account_numbers.index(current_account)
                                            account_tables[acc_idx].extend(table_content)
                
                break  # Exit password loop if successful
            except Exception as e:
                print(f"Error processing {pdf_path}: {str(e)}")
                continue
        
        # Process each account's data
        for acc_idx, account_number in enumerate(account_numbers[1:], 1):  # Skip initial empty string
            table_data = []
            merged_table = account_tables[acc_idx]
            total_row = len(merged_table)
            i = 0
            while i < total_row:
                x = i
                # Find the first row with a valid date
                for x in range(x, min(x + 10, total_row)):
                    if is_valid_date(str(merged_table[x][0])):
                        f_row = x
                        break
                else:
                    i += 1
                    continue
                
                # Find the last row of the current transaction block
                y = x + 1
                for y in range(y, min(y + 10, total_row)):
                    if is_valid_date(str(merged_table[y][0])) or merged_table[y][0] != '' or (len(merged_table[y]) > 3 and merged_table[y][3] != ''):
                        l_row = y
                        break
                else:
                    l_row = total_row
                
                # Process and store the data
                row = ["".join(row[0] for row in merged_table[f_row:l_row])] + \
                      ["".join(col) for col in zip(*merged_table[f_row:l_row])][1:]

                # Handle 7-column rows
                if len(row) == 7:
                    parsed_date = parser.parse(row[0], dayfirst=True)
                    row[0] = parsed_date.strftime("%d-%m-%Y")
                    del row[3]  # Remove Value Date column
                    row[1] = re.sub(rf"\b{re.escape(row[2])}\b", "", row[1]).strip()  # Remove Chq No. from Particulars
                    row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] else 0.0  # Debit
                    row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] else 0.0  # Credit
                    
                    value = str(row[5]).upper()
                    number = re.sub(r'[^\d.-]', '', str(row[5])).rstrip('.')
                    if "DR" in value and "-" not in number:
                        row[5] = -float(number) if '.' in number else -int(number)
                    else:
                        row[5] = float(number) if '.' in number else int(number)

                # Handle 5-column rows
                elif len(row) == 5:
                    row.insert(2, "")  # Insert empty Chq No.
                    parsed_date = parser.parse(row[0], dayfirst=True)
                    row[0] = parsed_date.strftime("%d-%m-%Y")
                    narration = row[1]
                    row[1] = narration[:90]  # Split narration into two parts
                    row[2] = narration[90:]
                    row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] else 0.0  # Debit
                    row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] else 0.0  # Credit
                    
                    value = str(row[5]).upper()
                    number = re.sub(r'[^\d.-]', '', str(row[5])).rstrip('.')
                    if "DR" in value and "-" not in number:
                        row[5] = -float(number) if '.' in number else -int(number)
                    else:
                        row[5] = float(number) if '.' in number else int(number)

                table_data.append(row)
                i = l_row
            
            # Prepare table with account number and headers
            account_row = [bank_name, account_number, "", "", "", ""]
            headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
            
            # Check if account already exists in data_table
            account_exists = False
            for idx, existing_table in enumerate(data_table):
                if existing_table[0][1] == account_number:
                    data_table[idx].extend(table_data)
                    account_exists = True
                    break
            
            if not account_exists:
                data_table.append([account_row, headers] + table_data)
    
    return data_table

def is_valid_date(date_str):
    try:
        if len(re.findall(r'\d+', date_str)) < 3:
            return False
        parse(date_str, dayfirst=True, fuzzy=False)
        return True
    except (ParserError, ValueError, TypeError):
        return False

def print_tables(tables):
    for table_data in tables:
        if len(table_data) < 2:
            account_number = table_data[0][1] if table_data else "Unknown"
            print(f"\nAccount {account_number} has insufficient data to display.\n")
            continue
        print(tabulate(table_data, tablefmt="grid"))

# Run the extraction
if __name__ == "__main__":
    pdf_files = [
        r"E:\Python\PDF\Sarvoday-1.pdf",
    ]
    print(f"PDF files to process: {pdf_files}")
    pdf_password = ["1003021003651"]
    try:
        final_data = sarvoday_1(pdf_files, pdf_password)
        print_tables(final_data)
    except Exception as e:
        print(f"An error occurred: {str(e)}")