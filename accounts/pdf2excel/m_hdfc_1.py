import pdfplumber
from tabulate import tabulate
import re
from PIL import Image
from dateutil import parser
from dateutil.parser import parse
from dateutil.parser import ParserError

# Date pattern for DD/MM/YYYY format
date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
bank_name = 'HDFC'

def hdfc_1(pdf_paths, passwords):
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
                            "horizontal_strategy": "text",
                            "intersection_tolerance": 10,
                        })
                        
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
            total_row = (len(merged_table)-1)
            i = 0
            y = 0
            while i < total_row:
                x = i
                # Find the first matching row for the day pattern
                for x in range(x, min(x+10, total_row)):
                    #print(str(merged_table[x][0]))
                    if is_valid_date(str(merged_table[x][0])):
                        f_row = x
                        break
                else:
                    i += 1  # Skip to the next iteration if no match is found
                    continue
                
                # Find the first matching row for the year pattern
                y=+(x+1)
                for y in range(y, min(y+10, (total_row + 1))):
                    if y == total_row:
                        l_row = total_row
                        break
                    elif (is_valid_date(str(merged_table[y][0])) or merged_table[y][0]!='') or merged_table[y][3]!='':
                        l_row = y
                        break
                else:
                    i += 1  # Skip to the next iteration if no match is found
                    continue
                #print(f_row,l_row)
                # Process and store the data
                row = ["".join(row[0] for row in merged_table[f_row:l_row])] + \
                    ["".join(col) for col in zip(*merged_table[f_row:l_row])][1:] 

            # for 7 row
                if len(row)==7 :
                    #row.insert(2, "")
                    parsed_date = parser.parse(row[0], dayfirst=True)
                    row[0] = parsed_date.strftime("%d-%m-%Y")
                    del row[3]
                    row[1] = re.sub(rf"\b{re.escape(row[2])}\b", "", row[1]).strip()
                    row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] is not None else 0.0
                    row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] is not None else 0.0
                    
                    value = row[5].upper()
                    number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
                    if "DR" in value and "-" not in number:  # Only make negative if not already negative
                        row[5] = -float(number) if '.' in number else -int(number)
                    else:
                        row[5] = float(number) if '.' in number else int(number)

                # for 5 Row
                if len(row)==5:  # Ensure rows have at least 5 elements
                    row.insert(2, "")
                    parsed_date = parser.parse(row[0], dayfirst=True)
                    row[0] = parsed_date.strftime("%d-%m-%Y")
                    narration=row[1]
                    row[1] = narration[:90]
                    row[2] = narration[90:]
                    row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[3]))) and row[3] is not None else 0.0
                    row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(row[4]))) and row[4] is not None else 0.0
                    
                    value = row[5].upper()
                    number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
                    if "DR" in value and "-" not in number:  # Only make negative if not already negative

                        row[5] = -float(number) if '.' in number else -int(number)
                    else:
                        row[5] = float(number) if '.' in number else int(number)


                #print(row)
                table_data.append(row)

                # Move `i` forward to skip processed rows
                i = l_row
                l_row=0
                f_row=0
            
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
        # Ensure the string has at least 3 parts (to enforce year, month, and day)
        if len(re.findall(r'\d+', date_str)) < 3:
            return False

        parsed_date = parse(date_str, dayfirst=True, fuzzy=False)
        
        return True  # Now we know it's a full date

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
        r"E:\Python\PDF\HDFC-6.pdf",
    ]
    print(f"PDF files to process: {pdf_files}")
    pdf_password = ["sdfssffs", "8401665589", "asfafdafaeee"]
    try:
        final_data = hdfc_1(pdf_files, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")