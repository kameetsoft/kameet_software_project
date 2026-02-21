import pdfplumber
from tabulate import tabulate
import re
from PIL import Image
from dateutil import parser
from dateutil.parser import parse
from dateutil.parser import ParserError

# Date pattern for DD/MM/YYYY format
date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
bank_name = 'ICICI Bank'




def icici_1(pdf_paths, passwords):
    # Initialize an empty list to store all rows

    data_table = []
    for pdf_path in pdf_paths:
        account_tables = []
        account_numbers = []
        
        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        return {'error': 'PDF file is empty'}

                    all_data= []
                    # Process each page
                    for page in pdf.pages:
                        
                        try:
                            # Assign default positions if not found
                            c1_x0 = round(page.search(r'DATE\s*MODE\*{0,2}', regex=True)[0]["x0"],0)
                            c2_x0 = round(page.search(r'MODE\*{0,2}\s*PARTICULARS', regex=True)[0]["x0"],0)
                            c3_x0 = round(page.search('PARTICULARS\s*DEPOSITS', regex=True)[0]["x0"],0)
                            c4_x1 = round(page.search('PARTICULARS\s*DEPOSITS', regex=True)[0]["x1"] ,0)  
                            c5_x1 = round(page.search('DEPOSITS\s*WITHDRAWALS', regex=True)[0]["x1"],0)
                            c6_x1 = round(page.search('WITHDRAWALS\s*BALANCE', regex=True)[0]["x1"],0)
        

                            column_width = [
                                ("Date", c1_x0-5, c2_x0-5),
                                ("Mode", c2_x0-5, c3_x0-3),
                                ("Particulars", c3_x0-3, c4_x1-65),
                                ("DEPOSITS", c4_x1-65, c4_x1+3),
                                ("WITHDRAWALS", c4_x1+3, c5_x1+3),
                                ("BALANCE", c5_x1+3, c6_x1+3)
                            ]
                        except Exception as e:
                            # If header not found, skip the page
                            #print(f"Header not found on page {pdf.pages.index(page) + 1}: {str(e)}")
                            continue
                        # Debugging: Draw bounding boxes for column positions
                        # img = page.to_image(resolution=300)
                        # for col in column_width:
                        #     img.draw_rect([col[1], 0, col[2], page.height], stroke="red")
                        # img.save(f"debug_page_{pdf.pages.index(page) + 1}.png")
                        # img.show()
            
                        tables = page.extract_tables({
                        "vertical_strategy": "explicit",
                        "horizontal_strategy": "lines",
                        "explicit_vertical_lines": [col[1] for col in column_width] + [column_width[-1][2]],
                        "intersection_tolerance": 3,
                        })

                        for table in tables:
                            for row in table:
                                # print("\n")
                                # print(row)
                                all_data.append(row)

                    #print_tables(all_data)

                    # Extract account numbers and separate data
                    current_account = None
                    for i, row in enumerate(all_data):
                        #print(row)
                        # combined_text = (
                        #     (" ".join(all_data[i-1]) + " " if i > 0 else "") +
                        #     " ".join(row) +
                        #     (" " + " ".join(all_data[i+1]) if i < len(all_data) - 1 else "")
                        # )

                        combined_text = " ".join(filter(None, row)) if row else ""
                     
                        #print(combined_text)
                        #pattern = r"(Account\s*X{8}\d{4}|Account\s*Number:\s*\d+)"
                        pattern = r"(?:Account\s*X{8}(\d{4})|Account\s*Number:\s*(\d+))"
                        account_match = re.search(pattern, combined_text, re.IGNORECASE)
                        
                        if account_match:
                            current_account = account_match.group(1) or account_match.group(2)  # Extract only the account number
                            if current_account not in account_numbers:
                                account_numbers.append(current_account)
                                account_tables.append([])
                        elif current_account:
                            acc_idx = account_numbers.index(current_account)
                            account_tables[acc_idx].append(row)
                break
            except Exception as e:
                print(f"Error processing PDF file {pdf_path} with password '{password}': {str(e)}")
                continue

        # Process each account's data

        final_data = []
        for acc_idx, account_number in enumerate(account_numbers):
            table_data = []
            account_data = account_tables[acc_idx]
            i = 0
            for i, row in enumerate(account_data):
                #print(row)
                f_row=i
                l_row=i

                if is_date(account_data[i][0]) and not ("Opening Balance" in account_data[i][1] or "Closing Balance" in account_data[i][1]):
                    row = account_data[i]
              
                    table_data.append(row)

                    i =l_row+1


            # Format the data
            for row in table_data:
                #print(row)
                parsed_date = parser.parse(row[0], dayfirst=True)
                row[0] = parsed_date.strftime("%d-%m-%Y")

                narration1 = row[2].replace("\n", " ")
                narration2 = row[1].replace("\n", " ")
                row[1] = narration1[:90]
                row[2] = narration1[90:]+"  " + narration2

                deposit = row[3]
                withdrawal = row[4]
                row[3] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(withdrawal))) and withdrawal is not None else 0.0
                row[4] = float(cleaned) if (cleaned := re.sub(r"[,\s]", "", str(deposit))) and deposit is not None else 0.0

    
                value = row[5].upper()
                number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
                if "DR" in value and "-" not in number:  # Only make negative if not already negative
                    row[5] = -float(number) if '.' in number else -int(number)
                else:
                    row[5] = float(number) if '.' in number else int(number)

                #print(row)
            # Add account number as the first row in the table
            account_row = [bank_name, account_number, "", "", "", ""]
            headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL BALANCE"]
        
            # for row in table_data:
            #     print(row)
            # Check if the account number table already exists
            account_exists = False
            for idx, existing_table in enumerate(data_table):
                if existing_table[0][1] == account_number:  # Compare account numbers
                    #print(f"Account Number: {account_number}, Appending to Table Index: {idx}")
                    account_exists = True
                    data_table[idx].extend(table_data)  # Append table_data to the existing table at this index
                    break

            if not account_exists:
                # If the account number table does not exist, create a new one
                data_table.append([account_row, headers] + table_data)
    #print_tables(data_table)

        # Print tables with account number as part of the table
        print_tables(data_table)
    return data_table

def is_date(date_str):
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
        if len(table_data) < 2:  # Ensure there are at least headers and data
            account_number = table_data[0][1] if table_data else "Unknown"
            #print(f"\nAccount {account_number} has insufficient data to display.\n")
            continue
        print(tabulate(table_data, tablefmt="grid"))

# Run the extraction
if __name__ == "__main__":
    #pdf_file = r"E:\Python\Pdf2Xls F\PDF\BOB-1- TAA064101.pdf"
    pdf_files = [r"E:\Python\PDF\ICICI-1.pdf",
                #r"E:\Python\Pdf2Xls F\PDF\BOB\BOBC3.pdf",
                 ]
    print(pdf_files)
    pdf_password = ["1003021003651", "new_password"]
    try:
        final_data = icici_1(pdf_files, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")