import pdfplumber
import os
import re
def get_module_name(pdf_path, passwords):
    pdf_path = pdf_path.strip()
    print(f"[🔍] Checking file path: {pdf_path}")
    print(f"[🔍] Using passwords: {passwords}")

    if not os.path.exists(pdf_path):
        return "Check Path"

    # Try each password in the list
    for password in passwords + [None]:
        sbi_brand_seen = False

        try:
            with pdfplumber.open(pdf_path, password=password) as pdf:
                if not pdf.pages:
                    return "PDF Empty"
                    # return {'error': 'PDF file is empty'}
                
                any_text_found = False   # ✅ KEY FLAG
                # Check all pages
                for page in pdf.pages:

                    # --- Detect SBI brand ONCE ---
                    if page.search(r'State\s+Bank\s+of\s+India', regex=True, case=False):
                        sbi_brand_seen = True

                     
                    try:
                        txt = page.extract_text() or ""
                    except Exception:
                        txt = ""

                    txt = txt.replace("\u200b", " ").replace("\xa0", " ")

                    if txt.strip():
                        any_text_found = True  # ✅ At least one page has text
                    # if not txt.strip():
                    #     print("⚠️ Scanned / image-only PDF detected")
                    #     return "Scanned PDF"


                    # ================= BANK DETECTION =================



                    # ---------- SBI FORMAT-3 (Txn Date / Value Date layout) ----------
                    try:
                        txt = page.extract_text() or ""
                    except Exception:
                        txt = ""

                    txt = txt.replace("\u200b", " ").replace("\xa0", " ")
                    txt_norm = re.sub(r"\s+", " ", txt).lower()

                    if (
                        "txn date" in txt_norm
                        and "value" in txt_norm
                        and "description" in txt_norm
                        and "ref no" in txt_norm
                        and "debit" in txt_norm
                        and "credit" in txt_norm
                        and "balance" in txt_norm
                    ):
                        print("✅ SBI FORMAT-3 DETECTED (HEADER)")
                        return "sbi_3"



                    # ---------- ICICI BANK (DETAILED STATEMENT – TABLE FORMAT) ----------
                    txt_norm = re.sub(r"\s+", " ", txt).lower()

                    icici_hits = (
                        "detailed statement" in txt_norm
                        and "transactions list" in txt_norm
                        and "value date" in txt_norm
                        and "transaction date" in txt_norm
                        and "withdrawal" in txt_norm
                        and "deposit" in txt_norm
                        and "balance" in txt_norm
                    )

                    if icici_hits:
                        print("✅ ICICI DETAILED STATEMENT (TABLE FORMAT) DETECTED")
                        return "icici_2"

                    # BANDHAN
                    # ---------- BANDHAN BANK (FIXED) ----------
                    if (
                        page.search(r'Bandhan\s+Bank', regex=True, case=False)
                        or page.search(r'BDBL\d{7}', regex=True, case=False)  # IFSC hint
                    ) and (
                        page.search(r'Transaction\s+Date', regex=True, case=False)
                        and page.search(r'Dr\s*/\s*Cr', regex=True, case=False)
                        and page.search(r'Balance', regex=True, case=False)
                    ):
                        return "bandhan_1"


                      # ---------- SBI (table header based) ----------
                    if (
                        page.search(r'Transaction\s+Reference', regex=True, case=False)
                        and ( page.search(r'Ref\.?/?No\.?/Chq\.?/?No\.?', regex=True, case=False)
                            or page.search(r'Ref\.?\.?No\./Chq\.?\.?No\.?', regex=True, case=False) )
                        and page.search(r'\bCredit\b', regex=True, case=False)
                        and page.search(r'\bDebit\b',  regex=True, case=False)
                        and page.search(r'\bBalance\b',regex=True, case=False)
                    ):
                        return "sbi_1"   # <-- ensure bank_modules["sbi_1"] = m_sbi_1.sbi_1


                    # SPCB check
                    if page.search('This is SPCB', regex=True, case=False):
                        return "spcb_1"
                    
                    if page.search('Statement Downloaded by INB User', regex=True, case=False):
                        return "spcb_2"
                

                    # SPCB-3 check (Post Dt / Val Dt format)
                    if (
                        page.search(r'Post\s+Dt\.?', regex=True, case=False)
                        and page.search(r'Val\s+Dt\.?', regex=True, case=False)
                        and page.search(r'\bDebit\b', regex=True, case=False)
                        and page.search(r'\bCredit\b', regex=True, case=False)
                        and page.search(r'\bBalance\b', regex=True, case=False)
                    ):
                        return "spcb_3"

                    # BOB check
                    if page.search('www.bankofbaroda.in', regex=True, case=False):
                        return "bob_1"
                    elif page.search('using bob World', regex=True, case=False):
                        return "bob_1"
                    elif page.search('Main Account Holder Name :', regex=True, case=False):
                        return "bob_1"
                    elif page.search('through bob World mobile app', regex=True, case=False):
                        return "bob_1"
                    # elif page.search('Statement Period', regex=True, case=False):
                    #     return "bob_1"
                    elif (
                        page.search(r'Statement\s+Period', regex=True, case=False)
                        and (
                            page.search(r'Bank\s+of\s+Baroda', regex=True, case=False)
                            or page.search(r'www\.bankofbaroda\.in', regex=True, case=False)
                            or page.search(r'bob\s+World', regex=True, case=False)
                        )
                    ):
                        return "bob_1"



                    # HDFC check
                    if (page.search('www.hdfcbank.com', regex=True, case=False) or 
                        page.search('savings account Details', regex=True, case=False)):
                        return "hdfc_1"
                    
                    if page.search('Txn Date\s*Narration\s*Withdrawals\s*Deposits', regex=True, case=False) and page.search('Joint Holders 2', regex=True, case=False):
                        return "hdfc_1"

                    # AXIS check
                    if page.search('Statement of Axis Account', regex=True, case=False):
                        return "axis_1"
                    if page.search('Canara Bank', regex=True, case=False):
                        return "canara_1"
                    # BOM check
                    if page.search('Website : www.bankofmaharashtra.in', regex=True, case=False):
                        return "bom_1"
                    
                    # SUTEX check
                    if (page.search('Date\s*Particulars\s*.*?\s+Debit\s*Credit', regex=True, case=False) 
                       and page.search('STATEMENT SUMMARY', regex=True, case=False)):
                        return "sutex_1"
                    
                    # sarvodaya check
                    if (page.search('Date\s*Particulars\s*Chq No.', regex=True, case=False) 
                        and page.search('The Sarvodaya Sahakari Bank Ltd', regex=True, case=False)):
                        return "sarvodaya_1"

                    

                    # # ---------- ICICI BANK (DETAILED STATEMENT - FORMAT 2) ----------
                    # if (
                    #     page.search(r'ICICI\s*Bank', regex=True, case=False)
                    #     or page.search(r'www\.icicibank\.com', regex=True, case=False)
                    # ) and (
                    #     page.search(r'DETAILED\s+STATEMENT', regex=True, case=False)
                    #     and page.search(r'Transactions\s+List', regex=True, case=False)
                    # ) and (
                    #     page.search(r'Withdrawal\s+Amount', regex=True, case=False)
                    #     and page.search(r'Deposit\s+Amount', regex=True, case=False)
                    #     and page.search(r'Balance', regex=True, case=False)
                    # ):
                    #     return "icici_2"
                    # ---------- ICICI BANK (DETAILED STATEMENT - FORMAT 2) ----------
                    txt = page.extract_text() or ""
                    txt = txt.replace("\u200b", " ").replace("\xa0", " ")
                    txt_norm = re.sub(r"\s+", " ", txt).lower()

                    if (
                        "icici bank" in txt_norm
                        and "detailed statement" in txt_norm
                        and "transactions list" in txt_norm
                        and "withdrawal" in txt_norm
                        and "deposit" in txt_norm
                        and "balance" in txt_norm
                    ):
                        print("✅ ICICI FORMAT-2 DETECTED")
                        return "icici_2"



                    # icici_1 check
                    if page.search('www.icicibank.com', regex=True, case=False):
                        return "icici_1"
                   
                
                    # Kalupur Bank check (brand + header)
                    if (
                        page.search(r"The\s+Kalupur\s+Commercial\s+Co\.?\.?op\.?\s+Bank\s+Ltd\.?", regex=True, case=False)
                        or page.search(r"\bIFSC\s*:\s*KCCB0", regex=True, case=False)
                    ) and (
                        page.search(r"\bDate\s+Value\s+Date\s+TR-Mode-?", regex=True, case=False)
                        and page.search(r"\bParticulars\b", regex=True, case=False)
                        and page.search(r"\bDebit\s+Amt\.?\b", regex=True, case=False)
                        and page.search(r"\bCredit\s+Amt\.?\b", regex=True, case=False)
                        and page.search(r"\bBalance\b", regex=True, case=False)
                    ):
                        return "kalupur_1"



                    # pnb
                    if (
                        page.search(r'Punjab\s+National\s+Bank', regex=True, case=False)
                        or page.search(r'pnbindia\.in', regex=True, case=False)
                        or page.search(r'\bKIMS\s*Remark', regex=True, case=False)
                        or (
                            page.search(r'\bTxn\s*Date\b', regex=True, case=False)
                            and page.search(r'\bDescription\b', regex=True, case=False)
                            and (page.search(r'\bDr\s*Amount\b', regex=True, case=False) or
                                page.search(r'\bDebit\s*Amount\b', regex=True, case=False))
                            and (page.search(r'\bCr\s*Amount\b', regex=True, case=False) or
                                page.search(r'\bCredit\s*Amount\b', regex=True, case=False))
                            and page.search(r'\bBalance\b', regex=True, case=False)
                        )
                    ):
                        return "pnb_1"
                    
                    # ... inside the per-page loop in get_module_name(...)

                    # KOTAK check (brand + header cues)
                    if (
                        page.search(r'Kotak\s+Mahindra\s+Bank', regex=True, case=False)
                        or page.search(r'\bKKBK\b', regex=True, case=False)  # appears in IMPS refs
                        or page.search(r'Account\s*No', regex=True, case=False)
                    ) and (
                        page.search(r'\bDate\s+Narration\b', regex=True, case=False)
                        and (page.search(r'Withdrawal\s*\(?\s*Dr\s*\)?', regex=True, case=False)
                            or page.search(r'Deposit\s*\(?\s*Cr\s*\)?', regex=True, case=False))
                        and page.search(r'\bBalance\b', regex=True, case=False)
                    ):
                        return "kotak_1"

                    # kotak_2
                    # KOTAK NEW FORMAT (Debit / Credit)
                    if (
                        page.search(r'Kotak\s+Mahindra\s+Bank', regex=True, case=False)
                        and page.search(r'DEBIT', regex=True, case=False)
                        and page.search(r'CREDIT', regex=True, case=False)
                        and page.search(r'BALANCE', regex=True, case=False)
                    ):
                        return "kotak_2"


                    # union bank check
                    # UNION BANK check (robust to slight variations)
                    if (
                        page.search(r'unionbankofindia', regex=True, case=False)
                        or (
                            page.search(r'S\.?No', regex=True, case=False) and
                            page.search(r'Transaction\s*Id', regex=True, case=False) and
                            page.search(r'Amount\(Rs\.\)', regex=True, case=False) and
                            page.search(r'Balance\(Rs\.\)', regex=True, case=False)
                        )
                        # or page.search(r'Statement\s+Period', regex=True, case=False)
                    ):
                        return "union_1"
                    # UNION BANK (STRICT)
                    # if (
                    #     page.search(r'Union\s+Bank\s+of\s+India', regex=True, case=False)
                    #     or page.search(r'unionbankofindia\.co\.in', regex=True, case=False)
                    #     or (
                    #         page.search(r'S\.?\s*No', regex=True, case=False)
                    #         and page.search(r'Transaction\s*Id', regex=True, case=False)
                    #         and page.search(r'Amount\s*\(Rs', regex=True, case=False)
                    #         and page.search(r'Balance\s*\(Rs', regex=True, case=False)
                    #     )
                    # ):
                    #     return "union_1"

                    
                    # INDIAN BANK check
                    if (
                        # brand signal(s)
                        page.search(r'\bIndian\s+Bank\b', regex=True, case=False)
                        or page.search(r'indianbank\.in', regex=True, case=False)
                        or page.search(r'Account\s*Number\s*[:\-]?\s*\d{6,20}', regex=True, case=False)
                    ) and (
                        # header / columns signal(s)
                        page.search(r'Date\s+Transaction\s+Details\s+Debits\s+Credits\s+Balance', regex=True, case=False)
                        or (
                            page.search(r'\bTransaction\s+Details\b', regex=True, case=False)
                            and page.search(r'\bDebits\b', regex=True, case=False)
                            and page.search(r'\bCredits\b', regex=True, case=False)
                            and page.search(r'\bBalance\b', regex=True, case=False)
                        )
                    ):
                        return "indian_1"   # <-- ensure bank_modules["indian_1"] = m_indian_1.indian_1
                    # ---------- SBI (layout-2) ----------
                    # Looks for: "State Bank of India" + header row with "Date  Credit  Balance  Details ...  Debit"
                    if (
                        page.search(r'State\s+Bank\s+of\s+India', regex=True, case=False)
                        and page.search(r'\bDate\b', regex=True, case=False)
                        and page.search(r'\bCredit\b', regex=True, case=False)
                        and page.search(r'\bBalance\b', regex=True, case=False)
                        and page.search(r'Details?.*Ref.*Cheque', regex=True, case=False)
                        and page.search(r'\bDebit\b', regex=True, case=False)
                    ):
                        return "sbi_2"
                    

                #     print("🔎 SBI BRAND SEEN:", sbi_brand_seen)

                #   # ---------- SBI FORMAT 3 (Txn Date / Value Date layout) ----------
                #     if (
                #         sbi_brand_seen
                #         and page.search(r'\bTxn\s+Date\b', regex=True, case=False)
                #         and page.search(r'\bValue\b', regex=True, case=False)
                #         and page.search(r'\bDescription\b', regex=True, case=False)
                #         and page.search(r'Ref\s+No', regex=True, case=False)
                #         and page.search(r'\bDebit\b', regex=True, case=False)
                #         and page.search(r'\bCredit\b', regex=True, case=False)
                #         and page.search(r'\bBalance\b', regex=True, case=False)
                #     ):
                #         print("✅ SBI FORMAT-3 DETECTED")
                #         return "sbi_3"




                 
                    #                     # IDBI 'Choice Point' check
                    # # IDBI 'Choice Point' check
                    # # signals: brand + the 5-column header
                    # if (
                    #     page.search(r'\bIDBI\b', regex=True, case=False)
                    #     or page.search(r'IDBI\s+Bank', regex=True, case=False)
                    #     or page.search(r'Account\s*Number\s*[:\-]?\s*\d{6,20}', regex=True, case=False)
                    # ):
                    #     if page.search(r'^\s*Sr\.?\s+Date\s+Description\s+Amount\s+Type\s*$', regex=True, case=False):
                    #         return "idbi_choicepoint"
                                        # ---------- IDBI 'Choice Point' (robust) ----------
                    # This detector tolerates header variants and matches txn lines like:
                    # "1. 05-AUG-25 SOME TEXT ... 75,000.00 Cr"
                    try:
                        txt = page.extract_text() or ""
                    except Exception:
                        txt = ""
                    txt = txt.replace("\u200b", " ").replace("\xa0", " ")

                    # tolerate Sr/Sr. No/S. No/etc in header
                    idbi_head_rx = re.compile(
                        r"\b(Sr\.?\s*No\.?|S\.?\s*No\.?|Sr\.?)\s+Date\s+Description\s+Amount\s+Type\b",
                        re.I
                    )

                    # txn rows (multi-line mode; ^ and $ act per-line)
                    idbi_txn_rx = re.compile(
                        r"^\s*\d+\.\s+\d{2}-[A-Za-z]{3}-\d{2}\s+.+?\s+[\d,]+\.\d{2}\s+(Cr|Dr)\s*$",
                        re.I | re.M,
                    )

                    # brand hint (optional; some pages may omit)
                    brand_hit = (
                        page.search(r'\bIDBI\b', regex=True, case=False)
                        or page.search(r'IDBI\s+Bank', regex=True, case=False)
                    )

                    header_hit = bool(idbi_head_rx.search(txt))
                    txn_hits = len(idbi_txn_rx.findall(txt))

                    # decision: many txn lines OR header + ≥1 txn OR brand + ≥1 txn
                    if txn_hits >= 3 or (header_hit and txn_hits >= 1) or (brand_hit and txn_hits >= 1):
                        return "idbi_choicepoint"
                    

                print("❌ Module not detected for this PDF")
                print("----- PDF TEXT SAMPLE -----")
                print((txt or "")[:1500])
                print("---------------------------")

                if not any_text_found:
                     return "Scanned PDF"
                print("✅ Detected Text (first 500):", txt_norm[:500])

                return "Module Not Found"

        except Exception as e:
            print(f"[⚠️] Password failed: {password} - {e}")
            # If password fails, continue to next password
            continue
    
    # If all passwords fail
    return "Passwords failed"

# Your specific parameters
pdf_path = r"E:\Python\PDF\ICICI-1.pdf"
passwords = ["sdfssffs", "8401665589", "asfafdafaeee"]

# Run the extraction
if __name__ == "__main__":
    try:
        result = get_module_name(pdf_path, passwords)
        print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")