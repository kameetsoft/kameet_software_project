import pdfplumber
from tabulate import tabulate
import re
#from PIL import Image
from dateutil.parser import parse
from dateutil.parser import ParserError

days_pattern = r'([0-2][0-9]|(3)[0-1])'
months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
years_pattern = r'(20[0-9][0-9])'
date_pattern = f'{days_pattern}-{months_pattern}-{years_pattern}'

bank_name = "SPCB"

column_1 = [
    (20, 85),    #Sr No
    (85,150),   # Trans DATE  
    (150, 300),    # Value DATE
    (300, 355),   # NARRATION
    (355, 425),  # CHQ-NO.
    (425, 500),  # WITHDRAWAL (DR)
    (500, 580),  # DEPOSIT (CR)
]
def spcb_2(pdf_paths, passwords):
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

                # Open the PDF with password
                #with pdfplumber.open(pdf_path, password=password) as pdf:
                    all_data = []

                    for line in pdf.pages[0].extract_text().splitlines():
                        #print(line)
                        if re.search(r'^\s*Value Date\s*Post Date\s*Narration Cheque', line, re.IGNORECASE): # 6 Column
                            column_boundaries = column_1
                            y_coordinate = 5
                            break

                    #print(len(column_boundaries))
                    page = pdf.pages[0]

                    # # Convert page to image
                    # im = page.to_image(resolution=300)

                    # # Extract words and draw rectangles around them
                    # words = page.extract_words()
                    # if words:
                    #     im.draw_rects([
                    #         (word['x0'], word['top'], word['x1'], word['bottom']) for word in words
                    #     ])

                    # # Draw vertical lines for column boundaries
                    # for x0, x1 in column_boundaries:
                    #     im.draw_vlines([x0, x1], stroke="blue", stroke_width=2)

                    # # Save and show the debug image
                    # im.save("debug_image_page1.png")
                    # im.show()

                    # Process each page
                    for page in pdf.pages:

                        # Extract all text as words with their coordinates
                        words = page.extract_words()

                        rows = []
                        y_positions = []
                        for word in words:
                            # Round the y-coordinate of the word to the nearest multiple of 5 to group words into rows
                            y_pos = round(word['top'] / y_coordinate) * y_coordinate
                            if y_pos not in y_positions:
                                y_positions.append(y_pos)
                                rows.append([])
                            row_idx = y_positions.index(y_pos)
                            rows[row_idx].append([
                                word['text'],
                                word['x0'],
                                word['x1']
                            ])
                        
                        # Process each row
                        for row_idx, y_pos in enumerate(y_positions):
                            row_words = rows[row_idx]
                            # Initialize row as list with empty strings for the number of columns
                            row_data = [''] * len(column_boundaries)  # Updated to match column boundaries length
                
                            
                            for word in row_words:
                                word_center = (word[1] + word[2]) / 2  # x0 and x1 from list
                                for i, boundary in enumerate(column_boundaries):
                                    start, end = boundary
                                    if start <= word_center <= end:
                                        if row_data[i]:
                                            row_data[i] += ' ' + word[0]  # text from list
                                        else:
                                            row_data[i] = word[0]
                                        break
                            
                            if any(row_data):
                                all_data.append(row_data)

                    #print_tables(all_data)

                    # Extract account numbers and separate data
                    current_account = None
                    for i, row in enumerate(all_data):
                        #print(row)
                        combined_text = (
                            (" ".join(all_data[i-1]) + " " if i > 0 else "") +
                            " ".join(row) +
                            (" " + " ".join(all_data[i+1]) if i < len(all_data) - 1 else "")
                        )
                        #print(combined_text)
                        pattern = r'Account\s*(Number|No)\s*:\s*(\d+)'
                        account_match = re.search(pattern, combined_text, re.IGNORECASE)    
                        #account_match = re.search(r'\s*Account (\d+)', " ".join(row),re.IGNORECASE)
                        
                        if account_match:
                            current_account = account_match.group(2) #account_match.group(0).lower().replace("account", "").replace(" ", "")  # Changed to group(0) to capture the full match
                            if current_account not in account_numbers:
                                account_numbers.append(current_account)
                                account_tables.append([])
                        elif current_account:
                            acc_idx = account_numbers.index(current_account)
                            account_tables[acc_idx].append(row)
                break
            except Exception as e:
                # If password fails, continue to next password
                continue

        if len(column_boundaries)==7:
            for row in all_data:
                del row[1]
                #print(row)
  

        # Process each account's data

        final_data = []
        for acc_idx, account_number in enumerate(account_numbers):
            table_data = []
            account_data = account_tables[acc_idx]
            total_row = (len(account_data)-1)
            i = 0
            y = 0
            while i < total_row:
                x = i

                #print(account_data[i])
                # Find the first matching row for the day pattern
                for x in range(x, min(x+10, total_row)):
                    #print(account_data[x][0])
                    if is_date(account_data[x][0]):
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
                    elif is_date(str(account_data[y][0])) or account_data[y][0]!='':
                        l_row = y
                        break
                else:
                    i += 1  # Skip to the next iteration if no match is found
                    continue
                #print(f_row,l_row)
                # Process and store the data
                row = ["".join(row[0] for row in account_data[f_row:l_row])] + \
                    ["".join(col) for col in zip(*account_data[f_row:l_row])][1:] 

                #print(row)
                table_data.append(row)   
                # Move `i` forward to skip processed rows
                i = l_row
                l_row=0
                f_row=0

            
            # Format the data
            for row in table_data:
                date_obj = parse(row[0],dayfirst=True)
                row[0] = date_obj.strftime("%d-%m-%Y")
                row[3] = float(re.sub(r"[,\s]", "", str(row[3]))) if row[3] is not None else 0.0
                row[4] = float(re.sub(r"[,\s]", "", str(row[4]))) if row[4] is not None else 0.0
                
                value = row[5].upper()
                number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')
                if "DR" in value and "-" not in number:
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

    print_tables(data_table)

        # Print tables with account number as part of the table
        #print_tables(data_table)
    return data_table

def is_date(date_str):
    try:
        # Ensure the string has at least 3 parts (to enforce year, month, and day)
        if len(re.findall(r'\d+', date_str)) < 3:
            return False

        parsed_date = parse(date_str, dayfirst=False, fuzzy=False)
        
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
    pdf_files = [r"E:\Python\PDF\HDFC-7.pdf",
                #r"E:\Python\Pdf2Xls F\PDF\BOB\BOBC3.pdf",
                 ]
    print(pdf_files)
    pdf_password = ["sdfssffs", "8401665589", "asfafdafaeee"]
    try:
        final_data = spcb_2(pdf_files, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")