import pdfplumber
from tabulate import tabulate
import re
from dateutil import parser
from dateutil.parser import parse
from dateutil.parser import ParserError

# days_pattern = r'([0-2][0-9]|(3)[0-1])'
# months_pattern = r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
# years_pattern = r'(20[0-9][0-9])'
date_pattern = r"\b(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/\d{4}\b"
bank_name='SUTEX'
account_number=''
def sutex_1(pdf_paths, passwords):
    global account_number
    extracted_tables = []
    merged_table = []
    for pdf_path in pdf_paths:

        for password in passwords + [None]:  # Add None to try opening without a password
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        return {'error': 'PDF file is empty'}
                    
                    for page in pdf.pages: 
                        # Extract Account Number
                        accNo=page.search(r'Account\s*(Number|No)\s*:\s*(\d+)', regex=True ,case=False)
                        if account_number == '':
                            account_number = accNo[0]['groups'][1] if accNo else None
                

                    # Extract tables using line-based detection
                        tables = page.extract_tables({
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "intersection_tolerance":10,
                            #"text_y_tolerance": 3
                           
                        })
                            
                        for table in tables:
                            # **Remove empty rows inline**
                            table = [row for row in table if any(cell and isinstance(cell, str) and cell.strip() for cell in row)]
                            if table and len(table) > 0:
                                for i in range(len(table)):
                                    table[i] = [item.replace('\n', '').rstrip('_') for item in table[i]]
                                # Check if all rows in the table have exactly 8 columns
                                num_columns = len(table[0])
                                if num_columns == 6 :
                                    if "date" in table[0][0].strip().lower():
                                        merged_table.extend(table[1:])
                                    else:
                                        merged_table.extend(table)

                                if num_columns == 7:
                                    for row in table:
                                        del row[3]
                                    if "date" in table[0][0].strip().lower():
                                        merged_table.extend(table[1:])
                                    else:
                                        merged_table.extend(table)


                    #detail={'client_name':client_name,'bank':bank,'account_number':account_number,'start_date':start_date,'end_date':end_date}            
               
                break
            except Exception as e:
                # If password fails, continue to next password
                continue   

        # Display the merged table or notify if none found
        # if merged_table:
        for row in merged_table:
            print(row)

       
    final_data = []


    # Format the data
    for row in merged_table:
        if not row[0]:
            continue
        parsed_date = parser.parse(row[0], dayfirst=True)
        row[0] = parsed_date.strftime("%d-%m-%Y")
        narration1=row[1]
        row[1] = narration1[:90]
        narration2=row[2]
        row[2] = narration1[90:]+ ' - '+ narration2

        if row[3] is not None:
            if re.sub(r"[,\s]", "", str(row[3])) == "-":
                cleaned = re.sub(r"[,\-\s]", "", str(row[3]))
            else:
                cleaned = re.sub(r"[,\s]", "", str(row[3]))
            row[3] = float(cleaned) if cleaned else 0.0
        else:
            row[3] = 0.0

        if row[4] is not None:
            if re.sub(r"[,\s]", "", str(row[4])) == "-":
                cleaned = re.sub(r"[,\-\s]", "", str(row[4]))
            else:
                cleaned = re.sub(r"[,\s]", "", str(row[4]))
            row[4] = float(cleaned) if cleaned else 0.0
        else:
            row[4] = 0.0
        
        value = row[5].upper()
        number = re.sub(r'[^\d.-]', '', row[5]).rstrip('.')  # Preserve negative sign
        if "DR" in value and "-" not in number:  # Only make negative if not already negative
            row[5] = -float(number) if '.' in number else -int(number)
        else:
            row[5] = float(number) if '.' in number else int(number)

        #print(row)
        final_data.append(row)



    #print_tables(final_data)

    # Add account number as the first row in the table
    account_row = [bank_name, account_number, "", "", "", ""]
    headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
    final_data.insert(0, headers )
    final_data.insert(0, account_row)


    # print(detail)
    #print_tables(final_data)
    return final_data
    

def is_valid_date(date_str):
    try:
        # Ensure the string has at least 3 parts (to enforce year, month, and day)
        if len(re.findall(r'\d+', date_str)) < 3:
            return False

        parsed_date = parse(date_str, dayfirst=True, fuzzy=False)
        
        return True  # Now we know it's a full date

    except (ParserError, ValueError, TypeError):
        return False

def print_tables(table):
    # for i, table in enumerate(tables):
    #     print(f"\nTable {i + 1}:\n")
        print(tabulate(table, headers="firstrow", tablefmt="grid"))

if __name__ == "__main__":
    pdf_file = [r"E:\Python\Pdf2Xls F\PDF\SUTEX1.pdf",
                #r"\\dadaji\E\OFFICE EXCEL\Bank Statement\H.R. Enterprise\H.R Enterprise\-\01-05-2024 To 23-09-2024 -.pdf"
                ]
    #print(pdf_file)
    pdf_password = ["213213"]  # Set password if required

    try:
        sutex_1(pdf_file, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
