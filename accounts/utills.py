from datetime import date

def get_fiscal_year_from_date(d: date) -> str:
    """
    Given a date, returns fiscal year string in format '2024_25'
    """
    if d.month >= 4:
        start_year = d.year
        end_year = d.year + 1
    else:
        start_year = d.year - 1
        end_year = d.year
    return f"{start_year}_{str(end_year)[-2:]}"


# Add the inverse helper in

def fy_to_daterange(fy_str: str):
    """
    '2025-26' or '2025_26' -> (date(2025,4,1), date(2026,3,31))
    '2025'                  -> (date(2025,4,1), date(2026,3,31))
    Returns None if not parseable.
    """
    if not fy_str:
        return None
    s = fy_str.strip()
    m = re.match(r"^(\d{4})[ _-]?(\d{2})$", s) or re.match(r"^(\d{4})$", s)
    if not m:
        return None
    start_year = int(m.group(1))
    start = date(start_year, 4, 1)
    end   = date(start_year + 1, 3, 31)
    return (start, end)

def get_db_for_fy(fy_str):
    """
    Convert a fiscal year string like '2024-25' into db alias like 'fy_2024_25'
    """
    if not fy_str:
        raise ValueError("Fiscal year not provided")
    return f"fy_{fy_str.replace('-', '_')}"

from datetime import date

def fiscal_year_range(fy_str):
    """
    Given fiscal year like '2024-25', returns (start_date, end_date)
    """
    try:
        start_year, end_suffix = fy_str.split("-")
        start_year = int(start_year)
        end_year = 2000 + int(end_suffix)
        return date(start_year, 4, 1), date(end_year, 3, 31)
    except Exception as e:
        raise ValueError(f"Invalid fiscal year format: {fy_str}") from e
    

# reports/utils.py
# utils.py

import fitz
import re
from datetime import datetime
import pdfplumber
import re
import pdfplumber
import io
import re

def parse_ais_pdf(file_obj, password=None):
    file_obj.seek(0)  # 🔁 rewind the pointer just in case
    buffer = io.BytesIO(file_obj.read())  # ⚠️ must be a fresh stream

    data = []

    try:
        with pdfplumber.open(buffer, password=password) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 3:
                            continue

                        joined_row = " ".join(cell for cell in row if cell)
                        if any(keyword in joined_row for keyword in [
                            "Dividend", "Interest", "Sale of securities"
                        ]):
                            data.append({
                                "category": row[0],
                                "reported_on": row[1],
                                "description": row[2],
                                "amount": parse_amount(row[3] if len(row) > 3 else ""),
                                "status": row[4] if len(row) > 4 else "",
                            })

    except Exception as e:
        print("⚠️ PDF parse failed:", e)
        return []

    return data

def parse_amount(val):
    try:
        return float(val.replace(",", "").strip())
    except:
        return 0.0


# accounts/utils.py
from datetime import date

def get_current_fy():
    """
    Returns the current Indian financial year in 'YYYY-YY' format.
    FY runs from April 1 to March 31.
    Example: if today is Aug 2025 -> '2025-26'
             if today is Jan 2025 -> '2024-25'
    """
    today = date.today()
    year = today.year
    if today.month >= 4:  # April or later
        fy_start = year
        fy_end = year + 1
    else:  # Jan to Mar
        fy_start = year - 1
        fy_end = year

    return f"{fy_start}-{str(fy_end)[-2:]}"


from django.conf import settings

def get_all_fy_aliases():
    """
    Returns all FY database aliases like:
    ['fy_2024_25', 'fy_2025_26', ...]
    """
    return sorted(
        alias
        for alias in settings.DATABASES.keys()
        if alias.startswith("fy_")
    )