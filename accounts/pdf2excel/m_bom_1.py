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
bank_name='BOM'

def bom_1(pdf_paths, passwords):
    extracted_tables = []
    # print(pdf_path)
    # print(password)

    for pdf_path in pdf_paths:

        for password in passwords + [None]:
            try:
                with pdfplumber.open(pdf_path, password=password) as pdf:
                    if not pdf.pages:
                        return {'error': 'PDF file is empty'}

                #with pdfplumber.open(pdf_path, password=password) as pdf:
                    data=pdf.pages[0].extract_text_simple()
                    # Flatten the list of lists into a single list
                    flat_data = [line.strip() for line in data.split("\n") if line.strip()]
                    text_content = ' '.join(flat_data)
                    #print(flat_data)


                    bank='BOM'
                    # Extract Client Name
                    #print(text_content)
                    client_name = "" #re.search(r'Holder\s+(.*?)\s+Customer Details', text_content).group(1).strip()
                    #print(client_name)

                    #print(text_content)
                    # Extract Account Number
                    account_number_match = re.search(r'Account No (\d+)', text_content)
                    if account_number_match:
                        account_number = account_number_match.group(1)
                        #print(f"Account Number: {account_number}")

                    # Extract Start Date and End Date using regex
                    date_match = re.search(r'from (\d{2}/\d{2}/\d{4}) to (\d{2}/\d{2}/\d{4})', text_content)
                    if date_match:
                        start_date = date_match.group(1)
                        end_date = date_match.group(2)
                        #print(f"Start Date: {start_date}")
                        #print(f"End Date: {end_date}")
                    
                    detail={'client_name':client_name,'bank':bank,'account_number':account_number,'start_date':start_date,'end_date':end_date}            
                    
                    merged_table = []
                    for page in pdf.pages:
                    # Extract tables using line-based detection
                        tables = page.extract_tables({
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                            "intersection_tolerance": 2,
                        })
                            
                        for table in tables:
                            #print_tables(table)
                            if table and len(table) > 0:
                                # Check if all rows in the table have exactly 8 columns
                                if all(len(row) == 8 for row in table):
                                    #print(table[0][0].strip())
                                    if re.search(date_pattern,table[1][1].strip()):
                                        if table[0][0].strip() == "Sr No":
                                            merged_table.extend(table[1:])
                                        else:
                                            merged_table.extend(table)

                break
            except Exception as e:
                # If password fails, continue to next password
                continue


    final_data=merged_table
    
    #  format
    cleaned_data = []

    for row in final_data:
        # Ensure row[1] is a valid date before proceeding
        if not is_valid_date(row[1]) or row[0]==None:
            continue  # Skip row if row[1] is not a valid date

        del row[0]  # Remove the first column
        row[0] = parser.parse(row[0], dayfirst=True).strftime("%d/%m/%Y")  # Convert date format

        # Clean and convert row[1]
        row[1] = re.sub(r"[\n]", "", str(row[1])) if row[1] is not None else ""

        # Clean and convert row[3]
        cleaned = re.sub(r"[,\s\n]", "", str(row[3])) if row[3] is not None else ""
        row[3] = float(cleaned) if cleaned and cleaned != '-' else 0.0

        # Clean and convert row[4]
        cleaned = re.sub(r"[,\s\n]", "", str(row[4])) if row[4] is not None else ""
        row[4] = float(cleaned) if cleaned and cleaned != '-' else 0.0

        # Process row[5] to handle "DR"
        value = row[5].upper() if row[5] else ""
        number = re.sub(r'[^\d.-]', '', str(row[5])).rstrip('.')  # Remove non-numeric characters

        try:
            if "DR" in value and "-" not in number:
                row[5] = -float(number) if '.' in number else -int(number)
            else:
                row[5] = float(number) if '.' in number else int(number)
        except ValueError:
            row[5] = 0  # Default to 0 if conversion fails

        # Ensure row[6] exists before deletion
        if len(row) > 6:
            del row[6]

        cleaned_data.append(row)  # Store cleaned row


        # Add account number as the first row in the table
    account_row = [bank_name, account_number, "", "", "", ""]
    headers = ["DATE", "NARRATION 1", "NARRATION 2", "WITHDRAWAL", "DEPOSIT", "CL. BALANCE"]
    cleaned_data.insert(0, headers )
    cleaned_data.insert(0, account_row)

    
    #print_tables(cleaned_data)
    return cleaned_data
    

def is_valid_date(date_str):
    try:
        # Try parsing the string to a datetime object
        parse(date_str)
        return True
    except ParserError:
        return False

def print_tables(table):
    # for i, table in enumerate(tables):
    #     print(f"\nTable {i + 1}:\n")
        print(tabulate(table, headers="firstrow", tablefmt="grid"))

if __name__ == "__main__":
    pdf_file = [r"C:\Users\itpam\Downloads\11.pdf"]
    pdf_password = ["rona2709"]  # Set password if required

    try:
        bom_1(pdf_file, pdf_password)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
