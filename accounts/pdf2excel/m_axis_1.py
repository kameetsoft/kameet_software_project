import pdfplumber
from tabulate import tabulate
import re
from PIL import Image
from dateutil import parser
from dateutil.parser import parse
from dateutil.parser import ParserError

# days_pattern = r'([0-2][0-9]|(3)[0-1])'
# months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
# years_pattern = r'(20[0-9][0-9])'
date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
bank_name='AXIS'
def axis_1(pdf_paths, passwords):
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
                    
                    # Debugging: Confirm total pages
                    #print(f"Processing {pdf_path} with {len(pdf.pages)} pages")
                    
                    # Process each page
                    for page in pdf.pages:
                        # Extract raw text to find account number
                        words = page.extract_text_simple()
                        current_account = None
                        if words:
                            for word in words.splitlines():
                                #print(word)
                                pattern = r"(?:Account Number|AccountNo|Account No|Cash Credit Account)\s*:\s*(\d+)"
                                account_match = re.search(pattern, word, re.IGNORECASE)
                                if account_match:
                                    current_account = account_match.group(1)
                                    #print(f"Page {pdf.pages.index(page)}: Found account {current_account}")
                                    break
                        # If no account number found on this page, use the last known one
                        if not current_account and account_numbers[-1]:
                            current_account = account_numbers[-1]
                        
                        # Extract tables using line-based detection
                        tables = page.extract_tables({
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "intersection_tolerance":1,
                        })

                        # im = page.to_image(resolution=300)
                        # im.draw_rects(page.extract_words())
                        # for _, x0, x1 in column_boundaries:
                        #     im.draw_vlines([x0, x1], stroke="blue", stroke_width=1)
                        # im.save("debug_image_page2.png")
                        # im.show()
                        
                        for table in tables:
                            # Remove empty rows inline
                            table = [row for row in table if any(cell and isinstance(cell, str) and cell.strip() for cell in row)]
                            if table and len(table) > 0:
                                num_columns = len(table[0])
                                # Debugging: Log table structure
                                #print(f"Page {pdf.pages.index(page)}: Table with {num_columns} columns")
                                
                                # Process tables with 5 or 7 columns
                                if num_columns == 5 or num_columns == 7:
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
                #print(f"Password {password} failed for {pdf_path}: {str(e)}")
                continue
        
        # Process each account's data
        for acc_idx, account_number in enumerate(account_numbers[1:], 1):  # Skip initial empty string
            table_data = []
            merged_table = account_tables[acc_idx]
            final_data = []
            final_data = [[cell.strip() if isinstance(cell, str) else "" for cell in row] for row in merged_table]
            for i in range(len(final_data)-1 ):
                row = final_data[i]

                if is_valid_date(row[0]):
                    row[0] = parser.parse(row[0], dayfirst=True).strftime("%d-%m-%Y")
                    ChqNo=row[1]
                    del row[1]
                    row.insert(2,'')
                    narration=row[1]
                    row[1] = narration[:90]
                    row[2] = narration[90:]+"  "+ChqNo
                    row[1] = re.sub(rf"\b{re.escape(row[2])}\b", "", row[1]).strip()
                    row[1] = re.sub(r"[\n]", "", str(row[1])) if row[1] is not None else ""
                    row[2] = re.sub(r"[\n]", "", str(row[2])) if row[2] is not None else ""
                    row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] is not None else 0.0
                    row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] is not None else 0.0
                    
                    value = row[5].upper()
                    number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
                    if "DR" in value and "-" not in number:  # Only make negative if not already negative

                        row[5] = -float(number) if '.' in number else -int(number)
                    else:
                        row[5] = float(number) if '.' in number else int(number)
                    del row[6]

                    #print(row)
                    table_data.append(row)

      
            
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
    
    # Print the final tables
    #print_tables(data_table)
    return data_table

def is_valid_date(date_str):
    try:
        # Remove extra spaces and newlines
        date_str = date_str.strip()

        # Ensure the date format is strictly "DD-MM-YYYY"
        if not date_str or len(date_str) != 10 or date_str[2] != '-' or date_str[5] != '-':
            return False

        # Parse the date string
        parsed_date = parser.parse(date_str, dayfirst=True)

        # Extract components and validate against input
        day, month, year = map(int, date_str.split('-'))
        return (parsed_date.day == day and parsed_date.month == month and parsed_date.year == year)
    except (ValueError, TypeError):
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
        r"E:\Python\PDF\AXIS-1.pdf",
    ]
    print(f"PDF files to process: {pdf_files}")
    pdf_password = ["sdfssffs", "8401665589", "asfafdafaeee"]
    try:
        final_data = axis_1(pdf_files, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")