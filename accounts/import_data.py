# # # Client tbl import
# import re
# import pandas as pd
# from datetime import datetime
# from accounts.models import Client, Group, Bank, UserData


# def import_data():
#     # 1) Load Excel
#     excel_path = r'Z:\Kameet Soft Project\Database\ClientTbl_new.xlsx'
#     df = pd.read_excel(excel_path)

#     # 2) Normalize headers
#     df.columns = df.columns.str.strip().str.lower()

#     # 3) Map your actual headers to model fields (extend if needed)
#     rename_map = {
#         "clientid": "client_id",
#         "client_id": "client_id",
#         "clientname": "client_name",
#         "client_nar": "client_name",

#         "leaglename": "legal_name",
#         "legal_nam": "legal_name",

#         "busycode": "busy_code",
#         "gstin": "gst_no",
#         # "gst_no": "gst_no",
#         "fileno": "file_no",
#         "file_no": "file_no",

#         "address": "address",
#         "pan": "pan",
#         "email": "email",
#         "mobileno": "mobile_no",
#         # "mobile_no": "mobile_no",
#         "tradename": "trade_name",
#         "trade_name": "trade_name",

#         "group": "group",
#         "groupname": "group",
#         "group_name": "group",
#         "bank": "bank",
#         "bankname": "bank",
#         "bank_name": "bank",
#         "ifsc": "bank_ifsc",

#         "gst": "gst_return",
#         "incometax": "it_return",
#         "it_return": "it_return",
#         "tds": "tds_return",
#         "tcs": "tcs_return",

#         "accounting": "gst_data",
#         "period": "period",
#         "status": "status",
#         "sale_define": "sale_define",
#         "gst_scheme": "gst_scheme",
#         "timestamp": "timestamp",
#         "reg_date": "reg_date",
#         "cancel_date": "cancel_date",
#         "cancle_date": "cancel_date",
#         "dob": "dob",

#         "userid": "user_id",
#         "user": "user_name_for_fk",
#         "alloted_to": "user_name_for_fk",
#         "it_alloted_to": "user_name_for_fk",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # 4) Helpers
#     def to_bool(val):
#         s = str(val).strip().lower()
#         if s in ("1", "true", "yes", "y", "t"):  return True
#         if s in ("0", "false", "no", "n", "f"):  return False
#         if s in ("", "nan", "none", "null"):     return False
#         return bool(val)

#     # DB column 'timestamp' is DATE -> parse to date
#     def parse_to_date(raw_ts, row_id_for_msg):
#         if pd.isna(raw_ts):
#             return None
#         ts_str = str(raw_ts).strip()
#         if "," in ts_str:  # e.g., "User, 25/11/2021 5.15.39 PM"
#             ts_str = ts_str.split(",")[-1].strip()
#         fmts = [
#             "%d/%m/%Y %H:%M:%S",
#             "%d-%m-%Y %H:%M:%S",
#             "%d/%m/%Y %I.%M.%S %p",
#             "%d/%m/%Y %I:%M:%S %p",
#             "%d-%m-%Y",
#             "%d/%m/%Y",
#         ]
#         for fmt in fmts:
#             try:
#                 dt = datetime.strptime(ts_str, fmt)
#                 return dt.date()
#             except ValueError:
#                 continue
#         print(f"⚠️ Timestamp parse error for {row_id_for_msg}: {ts_str}")
#         return None

#     def clean_pan(v, rid):
#         """Keep A-Z0-9 only, uppercase, truncate to 10 to satisfy VARCHAR(10)."""
#         if pd.isna(v):
#             return ""
#         s = re.sub(r"[^A-Za-z0-9]", "", str(v)).upper()
#         if len(s) > 10:
#             print(f"ℹ Truncating PAN for {rid}: '{s}' -> '{s[:10]}'")
#         return s[:10]

#     # 5) Import loop
#     success = 0
#     fail = 0

#     for idx, row in df.iterrows():
#         rid = row.get("client_id") or f"(row {idx})"

#         # --- Required fields (keep legal_name OPTIONAL now) ---
#         client_id = (str(row.get("client_id")).strip()
#                      if not pd.isna(row.get("client_id")) else None)
#         client_name = (str(row.get("client_name")).strip()
#                        if not pd.isna(row.get("client_name")) else None)

#         if not client_id or not client_name:
#             print(f"❌ Skip {rid}: missing required client_id/client_name")
#             fail += 1
#             continue

#         # legal_name optional: use None if blank (or set to client_name if you prefer)
#         _legal = None
#        # legal_name optional: store blank string if missing
#         if not pd.isna(row.get("legal_name")) and str(row.get("legal_name")).strip():
#             _legal = str(row.get("legal_name")).strip()
#         else:
#             _legal = ""   # blank instead of None to satisfy NOT NULL
#         # fallback idea (enable if you want it):
#         # if not _legal: _legal = client_name

#         # --- NOT NULL columns with safe defaults ---
#         address = (str(row.get("address")).strip()
#                    if not pd.isna(row.get("address")) else "")
#         pan = clean_pan(row.get("pan"), rid)  # avoid data-too-long
#         email = (str(row.get("email")).strip()
#                  if not pd.isna(row.get("email")) else "")

#         # --- Optional primitives ---
#         mobile_no = (str(row.get("mobile_no")).strip()
#                      if not pd.isna(row.get("mobile_no")) else None)
#         file_no = (str(row.get("file_no")).strip()
#                    if not pd.isna(row.get("file_no")) else None)
#         busy_code = (str(row.get("busy_code")).strip()
#                      if not pd.isna(row.get("busy_code")) else None)
#         trade_name = (str(row.get("trade_name")).strip()
#                       if not pd.isna(row.get("trade_name")) else None)
#         gst_no = (str(row.get("gst_no")).strip()
#                   if not pd.isna(row.get("gst_no")) else None)
#         user_id = (str(row.get("user_id")).strip()
#                    if not pd.isna(row.get("user_id")) and str(row.get("user_id")).strip() else None)
#         password = (str(row.get("password")).strip()
#                     if not pd.isna(row.get("password")) else None)
#         gst_data = (str(row.get("gst_data")).strip()
#                     if not pd.isna(row.get("gst_data")) else None)
#         period = (str(row.get("period")).strip()
#                   if not pd.isna(row.get("period")) else None)
#         status = (str(row.get("status")).strip()
#                   if not pd.isna(row.get("status")) else None)
#         sale_define = (str(row.get("sale_define")).strip()
#                        if not pd.isna(row.get("sale_define")) else None)
#         gst_scheme = (str(row.get("gst_scheme")).strip()
#                       if not pd.isna(row.get("gst_scheme")) else None)

#         # --- Booleans (NOT NULL) ---
#         gst_return = to_bool(row.get("gst_return"))
#         it_return = to_bool(row.get("it_return"))
#         tds_return = to_bool(row.get("tds_return"))
#         tcs_return = to_bool(row.get("tcs_return"))

#         # --- Dates ---
#         reg_date = row.get("reg_date") if not pd.isna(row.get("reg_date")) else None
#         cancel_date = row.get("cancel_date") if not pd.isna(row.get("cancel_date")) else None
#         dob = row.get("dob") if not pd.isna(row.get("dob")) else None
#         timestamp = parse_to_date(row.get("timestamp"), rid)

#         # --- Group FK (by id or group_name) ---
#         group_obj = None
#         grp_val = row.get("group")
#         if not pd.isna(grp_val):
#             try:
#                 group_obj = Group.objects.get(id=int(grp_val))
#             except Exception:
#                 try:
#                     group_obj = Group.objects.get(group_name__iexact=str(grp_val).strip())
#                 except Group.DoesNotExist:
#                     print(f"⚠️ Group not found for {rid}: {grp_val}")

#         # --- Bank FK (by id, bank_name, or IFSC) ---
#         bank_obj = None
#         bank_val = row.get("bank")
#         bank_ifsc = row.get("bank_ifsc")
#         if not pd.isna(bank_val):
#             try:
#                 bank_obj = Bank.objects.get(id=int(bank_val))
#             except Exception:
#                 try:
#                     bank_obj = Bank.objects.get(bank_name__iexact=str(bank_val).strip())
#                 except Bank.DoesNotExist:
#                     if not pd.isna(bank_ifsc):
#                         try:
#                             bank_obj = Bank.objects.get(IFSC__iexact=str(bank_ifsc).strip())
#                         except Bank.DoesNotExist:
#                             print(f"⚠️ Bank not found for {rid}: {bank_val} / IFSC={bank_ifsc}")
#                     else:
#                         print(f"⚠️ Bank not found for {rid}: {bank_val}")
#         elif not pd.isna(bank_ifsc):
#             try:
#                 bank_obj = Bank.objects.get(IFSC__iexact=str(bank_ifsc).strip())
#             except Bank.DoesNotExist:
#                 print(f"⚠️ Bank not found via IFSC for {rid}: {bank_ifsc}")

#         # --- it_alloted_to FK (UserData) by username ---
#         it_alloted_to_obj = None
#         user_name_for_fk = row.get("user_name_for_fk")
#         if not pd.isna(user_name_for_fk) and str(user_name_for_fk).strip():
#             uname = str(user_name_for_fk).strip()
#             try:
#                 it_alloted_to_obj = UserData.objects.get(username__iexact=uname)
#             except UserData.DoesNotExist:
#                 print(f"⚠️ UserData not found for {rid}: {uname}")

#         # --- Create row ---
#         try:
#             obj = Client.objects.create(
#                 client_id=client_id,
#                 client_name=client_name,
#                 legal_name=_legal,              # optional now
#                 address=address,
#                 other_info=None,
#                 pan=pan,
#                 gst_no=gst_no,
#                 mobile_no=mobile_no,
#                 email=email,
#                 file_no=file_no,
#                 busy_code=busy_code,
#                 group=group_obj,
#                 cancel_date=cancel_date,
#                 dob=dob,
#                 gst_data=gst_data,
#                 gst_scheme=gst_scheme,
#                 password=password,
#                 period=period,
#                 reg_date=reg_date,
#                 sale_define=sale_define,
#                 status=status,
#                 timestamp=timestamp,
#                 trade_name=trade_name,
#                 user_id=user_id,
#                 bank=bank_obj,
#                 it_alloted_to=it_alloted_to_obj,
#                 gst_return=gst_return,
#                 it_return=it_return,
#                 tcs_return=tcs_return,
#                 tds_return=tds_return,
#             )
#             print(f"✔ Imported: {obj.client_id} — {obj.client_name}")
#             success += 1
#         except Exception as e:
#             print(f"❌ Error importing {rid}: {e}")
#             fail += 1

#     print(f"\nDone. Imported: {success}, Failed: {fail}")

# # client_tbl_import_fixed.py
# import re
# import pandas as pd
# from datetime import datetime
# from accounts.models import Client, Group, Bank, UserData


# def import_data():
#     # 1) Load Excel
#     excel_path = r'Z:\Kameet Soft Project\Database\ClientTbl_new.xlsx'
#     df = pd.read_excel(excel_path)

#     # 2) Normalize headers: lowercase, trim, remove non-alphanumerics
#     df.columns = (
#         df.columns
#           .str.strip()
#           .str.lower()
#           .str.replace(r'[^a-z0-9]+', '', regex=True)
#     )

#     # 3) Rename to match model fields
#     rename_map = {
#         "clientid": "client_id",
#         "client_id": "client_id",
#         "clientname": "client_name",
#         "clientnar": "client_name",
#         "leaglename": "legal_name",
#         "legalnam": "legal_name",
#         "busycode": "busy_code",
#         "gstn": "gst_no",
#         "gstno": "gst_no",  # handles “GST No”
#         "fileno": "file_no",
#         "fileno.": "file_no",
#         "address": "address",
#         "pan": "pan",
#         "email": "email",
#         "mobileno": "mobile_no",  # handles “Mobile No”
#         "mobile": "mobile_no",
#         "tradename": "trade_name",
#         "group": "group",
#         "groupname": "group",
#         "group_name": "group",
#         "bank": "bank",
#         "bankname": "bank",
#         "ifsc": "bank_ifsc",
#         "gst": "gst_return",
#         "incometax": "it_return",
#         "tds": "tds_return",
#         "tcs": "tcs_return",
#         "accounting": "gst_data",
#         "period": "period",
#         "status": "status",
#         "saledefine": "sale_define",
#         "gstscheme": "gst_scheme",
#         "timestamp": "timestamp",
#         "regdate": "reg_date",
#         "canceldate": "cancel_date",
#         "cancle_date": "cancel_date",
#         "dob": "dob",
#         "userid": "user_id",
#         "user": "user_name_for_fk",
#         "allotedto": "user_name_for_fk",
#         "itallotedto": "user_name_for_fk",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     print("✅ Normalized Columns:", list(df.columns))  # Debug check

#     # 4) Helpers
#     def to_bool(val):
#         s = str(val).strip().lower()
#         if s in ("1", "true", "yes", "y", "t"): return True
#         if s in ("0", "false", "no", "n", "f", "", "nan", "none", "null"): return False
#         return bool(val)

#     def parse_to_date(raw_ts, rid):
#         if pd.isna(raw_ts):
#             return None
#         ts_str = str(raw_ts).strip()
#         if "," in ts_str:
#             ts_str = ts_str.split(",")[-1].strip()
#         fmts = [
#             "%d/%m/%Y %H:%M:%S",
#             "%d-%m-%Y %H:%M:%S",
#             "%d/%m/%Y %I.%M.%S %p",
#             "%d/%m/%Y %I:%M:%S %p",
#             "%d-%m-%Y",
#             "%d/%m/%Y",
#         ]
#         for fmt in fmts:
#             try:
#                 return datetime.strptime(ts_str, fmt).date()
#             except ValueError:
#                 continue
#         print(f"⚠️ Timestamp parse error for {rid}: {ts_str}")
#         return None

#     def clean_pan(v, rid):
#         if pd.isna(v):
#             return ""
#         s = re.sub(r"[^A-Za-z0-9]", "", str(v)).upper()
#         if len(s) > 10:
#             print(f"ℹ Truncating PAN for {rid}: '{s}' -> '{s[:10]}'")
#         return s[:10]

#     def _to_str(v):
#         return None if pd.isna(v) else str(v).strip()

#     # 5) Import loop
#     success, fail = 0, 0

#     for idx, row in df.iterrows():
#         rid = row.get("client_id") or f"(row {idx})"
#         client_id = _to_str(row.get("client_id"))
#         client_name = _to_str(row.get("client_name"))

#         if not client_id or not client_name:
#             print(f"❌ Skip {rid}: missing required client_id/client_name")
#             fail += 1
#             continue

#         legal_name = _to_str(row.get("legal_name")) or ""

#         address = _to_str(row.get("address")) or ""
#         pan = clean_pan(row.get("pan"), rid)
#         email = _to_str(row.get("email")) or ""
#         mobile_no = _to_str(row.get("mobile_no"))
#         file_no = _to_str(row.get("file_no"))
#         busy_code = _to_str(row.get("busy_code"))
#         trade_name = _to_str(row.get("trade_name"))
#         gst_no = _to_str(row.get("gst_no"))
#         user_id = _to_str(row.get("user_id"))
#         password = _to_str(row.get("password"))
#         gst_data = _to_str(row.get("gst_data"))
#         period = _to_str(row.get("period"))
#         status = _to_str(row.get("status"))
#         sale_define = _to_str(row.get("sale_define"))
#         gst_scheme = _to_str(row.get("gst_scheme"))

#         gst_return = to_bool(row.get("gst_return"))
#         it_return = to_bool(row.get("it_return"))
#         tds_return = to_bool(row.get("tds_return"))
#         tcs_return = to_bool(row.get("tcs_return"))

#         reg_date = row.get("reg_date") if not pd.isna(row.get("reg_date")) else None
#         cancel_date = row.get("cancel_date") if not pd.isna(row.get("cancel_date")) else None
#         dob = row.get("dob") if not pd.isna(row.get("dob")) else None
#         timestamp = parse_to_date(row.get("timestamp"), rid)

#         # Foreign keys
#         group_obj, bank_obj, it_alloted_to_obj = None, None, None

#         grp_val = row.get("group")
#         if not pd.isna(grp_val):
#             try:
#                 group_obj = Group.objects.get(id=int(grp_val))
#             except Exception:
#                 try:
#                     group_obj = Group.objects.get(group_name__iexact=str(grp_val).strip())
#                 except Group.DoesNotExist:
#                     print(f"⚠️ Group not found for {rid}: {grp_val}")

#         bank_val, bank_ifsc = row.get("bank"), row.get("bank_ifsc")
#         if not pd.isna(bank_val):
#             try:
#                 bank_obj = Bank.objects.get(id=int(bank_val))
#             except Exception:
#                 try:
#                     bank_obj = Bank.objects.get(bank_name__iexact=str(bank_val).strip())
#                 except Bank.DoesNotExist:
#                     if not pd.isna(bank_ifsc):
#                         try:
#                             bank_obj = Bank.objects.get(IFSC__iexact=str(bank_ifsc).strip())
#                         except Bank.DoesNotExist:
#                             print(f"⚠️ Bank not found for {rid}: {bank_val} / IFSC={bank_ifsc}")
#                     else:
#                         print(f"⚠️ Bank not found for {rid}: {bank_val}")
#         elif not pd.isna(bank_ifsc):
#             try:
#                 bank_obj = Bank.objects.get(IFSC__iexact=str(bank_ifsc).strip())
#             except Bank.DoesNotExist:
#                 print(f"⚠️ Bank not found via IFSC for {rid}: {bank_ifsc}")

#         user_name_for_fk = row.get("user_name_for_fk")
#         if not pd.isna(user_name_for_fk) and str(user_name_for_fk).strip():
#             uname = str(user_name_for_fk).strip()
#             try:
#                 it_alloted_to_obj = UserData.objects.get(username__iexact=uname)
#             except UserData.DoesNotExist:
#                 print(f"⚠️ UserData not found for {rid}: {uname}")

#         # Create client record
#         try:
#             Client.objects.create(
#                 client_id=client_id,
#                 client_name=client_name,
#                 legal_name=legal_name,
#                 address=address,
#                 other_info=None,
#                 pan=pan,
#                 gst_no=gst_no,
#                 mobile_no=mobile_no,
#                 email=email,
#                 file_no=file_no,
#                 busy_code=busy_code,
#                 group=group_obj,
#                 cancel_date=cancel_date,
#                 dob=dob,
#                 gst_data=gst_data,
#                 gst_scheme=gst_scheme,
#                 password=password,
#                 period=period,
#                 reg_date=reg_date,
#                 sale_define=sale_define,
#                 status=status,
#                 timestamp=timestamp,
#                 trade_name=trade_name,
#                 user_id=user_id,
#                 bank=bank_obj,
#                 it_alloted_to=it_alloted_to_obj,
#                 gst_return=gst_return,
#                 it_return=it_return,
#                 tcs_return=tcs_return,
#                 tds_return=tds_return,
#             )
#             print(f"✔ Imported: {client_id} — {client_name}")
#             success += 1
#         except Exception as e:
#             print(f"❌ Error importing {rid}: {e}")
#             fail += 1

#     print(f"\n✅ Import complete. Success: {success}, Failed: {fail}")



# # account table import
# # accounts/import_accounts.py
# import re
# import pandas as pd
# from datetime import datetime
# from django.db import transaction
# from accounts.models import AccountBank, Client


# def import_accounts():
#     excel_path = r'Z:\Kameet Soft Project\Database\AccTbl_new.xlsx'

#     df = pd.read_excel(excel_path)
#     df.columns = df.columns.str.strip().str.lower()

#     # Map Excel headers -> working column names
#     rename_map = {
#         "accid": "account_id",
#         "clientid": "client_id_text",
#         "accname": "account",
#         "accgroup": "account_group",
#         "bankname": "bank_name",

#         "accountno": "account_no",
#         "twomatch": "two_match",
#         "fullmatch": "full_match",

#         "ifsccode": "ifsc_code",
#         "acctype": "acc_type",
#         "estatement": "e_statement",

#         "pw": "pw",
#         "branch": "branch",
#         "stmpsw": "stms_pws",
#         "accmailid": "acc_mail_id",
#         "bankmailid": "bank_mail_id",
#         "branchmailid": "branch_mail_id",
#         "branchmobileno": "branch_mobile_no",

#         "statementfrequency": "statement_frequency",
#         "reminderdate": "reminder_date",
#         "cifnumber": "cif_number",

#         "stms_pws": "stms_pws",
#         "busyacccode": "busyacccode",

#         # common typo
#         "contact": "contact_no",
#         "contect": "contact_no",

#         "timestamp": "timestamp",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # -------- helpers --------
#     def to_bool(x):
#         s = str(x).strip().lower()
#         if s in ("1", "true", "yes", "y", "t"): return True
#         if s in ("0", "false", "no", "n", "f"): return False
#         if s in ("", "nan", "none", "null"): return False
#         return bool(x)

#     def clean_email(x, required=False):
#         if pd.isna(x):
#             return "" if required else None
#         s = str(x).strip()
#         if not s or "@" not in s:
#             return "" if required else None
#         return s

#     def clean_phone(x, required=False):
#         if pd.isna(x):
#             return "" if required else None
#         digits = re.sub(r"\D", "", str(x))
#         if required:
#             return digits[:15] if digits else ""
#         return digits[:15] if digits else None

#     def parse_date(x, rid):
#         if pd.isna(x):
#             return None
#         s = str(x).strip()
#         if "," in s:
#             s = s.split(",")[-1].strip()
#         fmts = [
#             "%d/%m/%Y %H:%M:%S",
#             "%d-%m-%Y %H:%M:%S",
#             "%d/%m/%Y %I.%M.%S %p",
#             "%d/%m/%Y %I:%M:%S %p",
#             "%d-%m-%Y",
#             "%d/%m/%Y",
#             "%Y-%m-%d",
#         ]
#         for f in fmts:
#             try:
#                 return datetime.strptime(s, f).date()
#             except ValueError:
#                 continue
#         # not fatal; column is nullable
#         return None

#     # choices normalizers
#     def norm_group(x):
#         s = (str(x).strip().lower() if not pd.isna(x) else "")
#         if s in ("bank accounts", "bank", "banks"): return "Bank Accounts"
#         if s in ("credit card", "card", "cc"):      return "Credit Card"
#         # schema has NOT NULL for account_group -> default if blank
#         return "Bank Accounts"

#     def norm_acc_type(x):
#         s = (str(x).strip().lower() if not pd.isna(x) else "")
#         if s in ("saving", "savings", "sb"): return "Saving"
#         if s in ("current", "ca"):           return "Current"
#         # NOT NULL -> default
#         return "Saving"

#     # -------- import loop --------
#     created, failed = 0, 0

#     # Many columns are NOT NULL in MySQL; give safe defaults if Excel blank
#     def required_text(val, default=""):
#         if pd.isna(val):
#             return default
#         s = str(val).strip()
#         return s if s else default

#     with transaction.atomic():
#         for idx, row in df.iterrows():
#             rid = row.get("account_id") or f"(row {idx})"

#             # REQUIRED: client_id link (both FK and the text column)
#             client_key = required_text(row.get("client_id_text"), default="")
#             if not client_key:
#                 print(f"❌ Skip {rid}: missing client_id")
#                 failed += 1
#                 continue

#             try:
#                 client_obj = Client.objects.get(client_id=client_key)
#             except Client.DoesNotExist:
#                 print(f"❌ Skip {rid}: Client not found for client_id={client_key}")
#                 failed += 1
#                 continue

#             # Build values for ALL NOT NULL columns with defaults if empty:
#             data = {
#                 # NOT NULLs:
#                 "account_id": required_text(row.get("account_id"), default=""),
#                 "client": client_obj,                         # FK
#                 "client_name": client_obj.client_name,        # NOT NULL
#                 "account": required_text(row.get("account"), default=""),
#                 "account_group": norm_group(row.get("account_group")),
#                 "data_entry": "Manual",  # or map a column if present; NOT NULL
#                 "acc_mail_id": clean_email(row.get("acc_mail_id"), required=True) or "",
#                 "account_no": required_text(row.get("account_no"), default=""),
#                 "two_match": required_text(row.get("two_match"), default=""),
#                 "full_match": to_bool(row.get("full_match")),        # NOT NULL bool
#                 "ifsc_code": required_text(row.get("ifsc_code"), default=""),
#                 "acc_type": norm_acc_type(row.get("acc_type")),       # NOT NULL choice
#                 "e_statement": to_bool(row.get("e_statement")),       # NOT NULL bool
#                 "bank_name": required_text(row.get("bank_name"), default=""),
#                 "pw": required_text(row.get("pw"), default=""),
#                 "branch": required_text(row.get("branch"), default=""),
#                 "contact_no": clean_phone(row.get("contact_no"), required=True) or "",
#                 # Persist the plain client_id text column too (your schema has it)
#                 "client_id": client_key,

#                 # NULLable columns:
#                 "bank_mail_id": clean_email(row.get("bank_mail_id")),         # NULL ok
#                 "branch_mail_id": clean_email(row.get("branch_mail_id")),     # NULL ok
#                 "branch_mobile_no": clean_phone(row.get("branch_mobile_no")), # NULL ok
#                 "cif_number": required_text(row.get("cif_number"), default=None),
#                 "closing_date": parse_date(row.get("closing_date"), rid),
#                 "reminder_date": parse_date(row.get("reminder_date"), rid),
#                 "statement_frequency": required_text(row.get("statement_frequency"), default=None),
#                 "stms_pws": required_text(row.get("stms_pws"), default=""),
#                 "busyacccode": required_text(row.get("busyacccode"), default=""),
#             }

#             # Enforce hard NOT NULL again (in case of weird values)
#             for key in [
#                 "account_id", "client_name", "account", "account_group",
#                 "data_entry", "acc_mail_id", "account_no", "two_match",
#                 "ifsc_code", "acc_type", "bank_name", "pw", "branch", "contact_no",
#                 "stms_pws", "busyacccode"
#             ]:
#                 if data.get(key) is None:
#                     data[key] = ""

#             try:
#                 obj = AccountBank.objects.create(**data)
#                 print(f"✔ Imported: {obj.client.client_id} — {obj.account}")
#                 created += 1
#             except Exception as e:
#                 print(f"❌ Error importing {rid}: {e}")
#                 failed += 1

#     print(f"\nDone. Accounts created: {created}, Failed: {failed}")

#############################################################
# # accounts/import_accounts.py
# import re
# import pandas as pd
# from datetime import datetime
# from django.db import transaction
# from accounts.models import AccountBank, Client


# def import_accounts():
#     excel_path = r'Z:\Kameet Soft Project\Database\AccTbl_new.xlsx'

#     df = pd.read_excel(excel_path)
#     df.columns = df.columns.str.strip().str.lower()

#     # Map Excel headers -> working column names
#     rename_map = {
#         "accid": "account_id",
#         "clientid": "client_id_text",
#         "accname": "account",
#         "accgroup": "account_group",
#         "bankname": "bank_name",

#         "accno": "account_no",
#         "twomatch": "two_match",
#         "fullmatch": "full_match",

#         "ifsc": "ifsc_code",
#         "acctype": "acc_type",
#         "estatement": "e_statement",

#         "pw": "pw",
#         "branch": "branch",
#         "stmps": "stms_pws",
#         "accmailid": "acc_mail_id",
#         "bankmailid": "bank_mail_id",
#         "branchmailid": "branch_mail_id",
#         "branchmobileno": "branch_mobile_no",

#         "statementfrequency": "statement_frequency",
#         "reminderdate": "reminder_date",
#         "cifnumber": "cif_number",

#         "stms_pws": "stms_pws",
#         "busyacccode": "busyacccode",

#         # common typo
#         "contact": "contact_no",
#         "contect": "contact_no",

#         "timestamp": "timestamp",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # -------- helpers --------
#     def to_bool(x):
#         s = str(x).strip().lower()
#         if s in ("1", "true", "yes", "y", "t"): return True
#         if s in ("0", "false", "no", "n", "f"): return False
#         if s in ("", "nan", "none", "null"): return False
#         return bool(x)

#     def clean_email(x, required=False):
#         if pd.isna(x):
#             return "" if required else None
#         s = str(x).strip()
#         if not s or "@" not in s:
#             return "" if required else None
#         return s

#     def clean_phone(x, required=False):
#         if pd.isna(x):
#             return "" if required else None
#         digits = re.sub(r"\D", "", str(x))
#         if required:
#             return digits[:15] if digits else ""
#         return digits[:15] if digits else None

#     def parse_date(x, rid):
#         if pd.isna(x):
#             return None
#         s = str(x).strip()
#         if "," in s:
#             s = s.split(",")[-1].strip()
#         fmts = [
#             "%d/%m/%Y %H:%M:%S",
#             "%d-%m-%Y %H:%M:%S",
#             "%d/%m/%Y %I.%M.%S %p",
#             "%d/%m/%Y %I:%M:%S %p",
#             "%d-%m-%Y",
#             "%d/%m/%Y",
#             "%Y-%m-%d",
#         ]
#         for f in fmts:
#             try:
#                 return datetime.strptime(s, f).date()
#             except ValueError:
#                 continue
#         return None

#     def norm_acc_type(x):
#         s = (str(x).strip().lower() if not pd.isna(x) else "")
#         if s in ("saving", "savings", "sb"): return "Saving"
#         if s in ("current", "ca"):           return "Current"
#         return "Saving"

#     # -------- import loop --------
#     created, failed = 0, 0

#     # Many columns are NOT NULL in MySQL; give safe defaults if Excel blank
#     def required_text(val, default=""):
#         if pd.isna(val):
#             return default
#         s = str(val).strip()
#         return s if s else default

#     with transaction.atomic():
#         for idx, row in df.iterrows():
#             rid = row.get("account_id") or f"(row {idx})"

#             # REQUIRED: client_id link (both FK and the text column)
#             client_key = required_text(row.get("client_id_text"), default="")
#             if not client_key:
#                 print(f"❌ Skip {rid}: missing client_id")
#                 failed += 1
#                 continue

#             try:
#                 client_obj = Client.objects.get(client_id=client_key)
#             except Client.DoesNotExist:
#                 print(f"❌ Skip {rid}: Client not found for client_id={client_key}")
#                 failed += 1
#                 continue

#             # Keep account_group EXACTLY as in Excel (trimmed only)
#             raw_group = row.get("account_group")
#             excel_group = "" if pd.isna(raw_group) else str(raw_group).strip()

#             data = {
#                 # NOT NULLs:
#                 "account_id": required_text(row.get("account_id"), default=""),
#                 "client": client_obj,                         # FK
#                 "client_name": client_obj.client_name,        # NOT NULL
#                 "account": required_text(row.get("account"), default=""),

#                 # exact value from Excel for account_group
#                 "account_group": excel_group,

#                 "data_entry": "Manual",  # NOT NULL
#                 "acc_mail_id": clean_email(row.get("acc_mail_id"), required=True) or "",
#                 "account_no": required_text(row.get("account_no"), default=""),
#                 "two_match": required_text(row.get("two_match"), default=""),
#                 "full_match": to_bool(row.get("full_match")),        # NOT NULL bool
#                 "ifsc_code": required_text(row.get("ifsc_code"), default=""),
#                 "acc_type": norm_acc_type(row.get("acc_type")),       # NOT NULL choice
#                 "e_statement": to_bool(row.get("e_statement")),       # NOT NULL bool
#                 "bank_name": required_text(row.get("bank_name"), default=""),
#                 "pw": required_text(row.get("pw"), default=""),
#                 "branch": required_text(row.get("branch"), default=""),
#                 "contact_no": clean_phone(row.get("contact_no"), required=True) or "",
#                 # Persist the plain client_id text column too (your schema has it)
#                 "client_id": client_key,

#                 # NULLable columns:
#                 "bank_mail_id": clean_email(row.get("bank_mail_id")),         # NULL ok
#                 "branch_mail_id": clean_email(row.get("branch_mail_id")),     # NULL ok
#                 "branch_mobile_no": clean_phone(row.get("branch_mobile_no")), # NULL ok
#                 "cif_number": required_text(row.get("cif_number"), default=None),
#                 "closing_date": parse_date(row.get("closing_date"), rid),
#                 "reminder_date": parse_date(row.get("reminder_date"), rid),
#                 "statement_frequency": required_text(row.get("statement_frequency"), default=None),
#                 "stms_pws": required_text(row.get("stms_pws"), default=""),
#                 "busyacccode": required_text(row.get("busyacccode"), default=""),
#             }

#             # Enforce hard NOT NULL again (in case of weird values)
#             for key in [
#                 "account_id", "client_name", "account", "account_group",
#                 "data_entry", "acc_mail_id", "account_no", "two_match",
#                 "ifsc_code", "acc_type", "bank_name", "pw", "branch", "contact_no",
#                 "stms_pws", "busyacccode"
#             ]:
#                 if data.get(key) is None:
#                     data[key] = ""

#             try:
#                 obj = AccountBank.objects.create(**data)
#                 print(f"✔ Imported: {obj.client.client_id} — {obj.account} ({data['account_group']})")
#                 created += 1
#             except Exception as e:
#                 print(f"❌ Error importing {rid}: {e}")
#                 failed += 1

#     print(f"\nDone. Accounts created: {created}, Failed: {failed}")


# # userdata tbl
# import pandas as pd
# from django.db import transaction
# from accounts.models import UserData


# def import_users():
#     r"""Import users from Excel: Z:\Kameet Soft Project\Database\user_tbl.xlsx"""
#     excel_path = r'Z:\Kameet Soft Project\Database\user_tbl.xlsx'

#     # 1) Load Excel
#     df = pd.read_excel(excel_path)
#     df.columns = df.columns.str.strip().str.lower()

#     # 2) Ensure expected columns
#     for col in ["username", "password", "in_date", "out_date"]:
#         if col not in df.columns:
#             df[col] = None

#     def clean_str(v):
#         return "" if pd.isna(v) else str(v).strip()

#     created, updated, skipped = 0, 0, 0

#     # 3) Import in a transaction
#     with transaction.atomic():
#         for idx, row in df.iterrows():
#             username = clean_str(row.get("username"))
#             if not username:
#                 print(f"⚠️ Skip row {idx}: missing username")
#                 skipped += 1
#                 continue

#             password = clean_str(row.get("password"))
#             in_date = row.get("in_date") if not pd.isna(row.get("in_date")) else None
#             out_date = row.get("out_date") if not pd.isna(row.get("out_date")) else None

#             try:
#                 obj, is_created = UserData.objects.update_or_create(
#                     username=username,
#                     defaults={
#                         "password": password,
#                         "in_date": in_date,
#                         "out_date": out_date,
#                     },
#                 )
#                 if is_created:
#                     print(f"✔ Created user: {obj.username}")
#                     created += 1
#                 else:
#                     print(f"↺ Updated user: {obj.username}")
#                     updated += 1
#             except Exception as e:
#                 print(f"❌ Row {idx} ({username}): {e}")
#                 skipped += 1

#     print(f"\nDone. Users created: {created}, updated: {updated}, skipped: {skipped}")


# import dataentry tbl
# import os
# import shutil
# from pathlib import Path
# from datetime import datetime, date
# import pandas as pd
# from django.conf import settings
# from django.db import transaction
# from accounts.models import Client, AccountBank, UserData, DataEntry
# from accounts.utills import get_fiscal_year_from_date


# def import_data_entries():
#     r"""Import DataEntry from CSV: Z:\Kameet Soft Project\Database\trans_tbl_1.csv"""
#     excel_path = r'Z:\Kameet Soft Project\Database\trans_tbl_1.csv'
#     # 1) Load Excel
#     df = pd.read_csv(excel_path)
#     df.columns = df.columns.str.strip().str.lower()

#     # 2) Normalize common headers
#     # rename_map = {
#     #     "clientid": "client_id",
#     #     "client": "client_id",
#     #     "client_name": "client_name",
#     #     "accountid": "account_id",
#     #     "account": "account_id",
#     #     "virtual": "virtual_account_type",
#     #     "virtual_account": "virtual_account_type",
#     #     "alloted_to_user": "alloted_to",
#     #     "user": "alloted_to",
#     #     "allocate_to": "alloted_to",
#     #     "attach": "source_file",
#     #     "attach_path": "source_file",
#     #     "attachment": "source_file",
#     #     "recdate": "rec_date",
#     #     "received_date": "rec_date",
#     #     "from": "from_date",
#     #     "to": "last_date",
#     #     "alloted_dt": "alloted_date",
#     #     "done_dt": "done_date",
#     # }
#     # df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # 2) Normalize common headers  (after df.columns = df.columns.str.strip().str.lower())
#     rename_map = {
#         "clientid": "client_id",
#         "client": "client_id",
#         "client_name": "client_name",

#         "accid": "account_id",
#         "accountid": "account_id",
#         "account": "account_id",

#         "recdate": "rec_date",
#         "recformat": "format",
#         "recby": "received_by",

#         "fromdate": "from_date",
#         "lastdate": "last_date",

#         "allotedto": "alloted_to",
#         "alloted_to_user": "alloted_to",
#         "user": "alloted_to",
#         "allocate_to": "alloted_to",

#         "alloteddate": "alloted_date",
#         "donedate": "done_date",

#         "timestamp": "timestamp",
#         "nil": "nil",                          # if you want to use it to set is_nil

#         "status": "status",
#         "query": "query",
#         "remark": "remark",

#         "filelink": "source_file",
#         "attach": "source_file",
#         "attach_path": "source_file",
#         "attachment": "source_file",

#         "virtual": "virtual_account_type",
#         "virtual_account": "virtual_account_type",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # 3) Ensure all expected columns exist
#     needed = [
#         "client_id", "client_name", "account_id", "virtual_account_type", "alloted_to",
#         "rec_date", "from_date", "last_date", "alloted_date", "done_date",
#         "format", "received_by", "status", "query", "remark", "msg_id",
#         "source_file"
#     ]
#     for col in needed:
#         if col not in df.columns:
#             df[col] = None

#     # ---- helpers ----
#     def _parse_date(x):
#         if pd.isna(x) or x is None or str(x).strip() == "":
#             return None
#         if isinstance(x, (datetime, pd.Timestamp)):
#             return x.date()
#         for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
#             try:
#                 return datetime.strptime(str(x).strip(), fmt).date()
#             except Exception:
#                 continue
#         return None

#     def _nz(v):
#         return "" if pd.isna(v) or v is None else str(v).strip()

#     def _choose_db(from_date_val, last_date_val):
#         base = from_date_val or last_date_val or date.today()
#         fy = get_fiscal_year_from_date(base)
#         return f"fy_{fy}"

#     def _copy_attach(entry, src_path, db_alias):
#         """Copy file to MEDIA_ROOT/fy_xxxx_xx/client_id/account_id/id.ext"""
#         if not src_path or not os.path.exists(src_path):
#             return
#         try:
#             client_part = entry.client.client_id.strip()
#             acc_part = (entry.account.account_id if entry.account else "unknown-account")
#             ext = Path(src_path).suffix or ""
#             rel_path = os.path.join(db_alias, client_part, acc_part, f"{entry.id}{ext}")
#             dest_path = os.path.join(settings.MEDIA_ROOT, rel_path)
#             os.makedirs(os.path.dirname(dest_path), exist_ok=True)
#             shutil.copy2(src_path, dest_path)
#             entry.attach_file.name = rel_path
#             entry.save(using=db_alias, update_fields=["attach_file"])
#             print(f"📎 Copied attachment for {entry.id}")
#         except Exception as e:
#             print(f"⚠️ Attachment copy failed for {entry.id}: {e}")

#     # ---- import ----
#     created, skipped, errors = 0, 0, 0

#     with transaction.atomic():
#         for idx, row in df.iterrows():
#             rid = f"row {idx+1}"

#             client_id = _nz(row.get("client_id"))
#             client_name = _nz(row.get("client_name"))

#             client_obj = None
#             if client_id:
#                 client_obj = Client.objects.filter(client_id=client_id).first()
#             if not client_obj and client_name:
#                 client_obj = Client.objects.filter(client_name__iexact=client_name).first()

#             if not client_obj:
#                 print(f"❌ {rid}: Client not found ({client_id or client_name})")
#                 skipped += 1
#                 continue

#             # account / virtual
#             account_obj = None
#             acc_code = _nz(row.get("account_id"))
#             virtual = _nz(row.get("virtual_account_type"))
#             if virtual in ("1", "2"):
#                 account_obj = None
#             elif acc_code:
#                 account_obj = AccountBank.objects.filter(client=client_obj, account_id=acc_code).first()

#             # user
#             user_obj = None
#             alloted = _nz(row.get("alloted_to"))
#             if alloted:
#                 user_obj = UserData.objects.filter(username__iexact=alloted).first()

#             # dates
#             rec_date = _parse_date(row.get("rec_date"))
#             from_date = _parse_date(row.get("from_date"))
#             last_date = _parse_date(row.get("last_date"))
#             alloted_date = _parse_date(row.get("alloted_date"))
#             done_date = _parse_date(row.get("done_date"))

#             if not from_date or not last_date:
#                 print(f"⚠️ {rid}: Missing from/last date, skipped.")
#                 skipped += 1
#                 continue

#             db_alias = _choose_db(from_date, last_date)

#             nil_val = _nz(row.get("nil")).lower()
#             is_nil_flag = nil_val in ("1", "yes", "y", "true", "done", "nil")
            
#             try:
#                 entry = DataEntry(
#                     client=client_obj,
#                     account=account_obj,
#                     alloted_to=user_obj,
#                     virtual_account_type=(virtual if virtual in ("1", "2") else None),
#                     rec_date=rec_date,
#                     from_date=from_date,
#                     last_date=last_date,
#                     alloted_date=alloted_date,
#                     done_date=done_date,
#                     format=_nz(row.get("format")) or "Soft Copy",
#                     received_by=_nz(row.get("received_by")) or "Mail",
#                     status=_nz(row.get("status")) or None,
#                     query=_nz(row.get("query")) or None,
#                     remark=_nz(row.get("remark")) or None,
#                     msg_id=_nz(row.get("msg_id")) or None,
#                     is_nil=is_nil_flag if not _nz(row.get("status")) else (_nz(row.get("status")).lower()=="nil"),
#                 )
#                 entry.save(using=db_alias)
#                 src_file = _nz(row.get("source_file"))
#                 if src_file and os.path.exists(src_file):
#                     _copy_attach(entry, src_file, db_alias)
#                 created += 1
#                 print(f"✔ Imported {rid}: id={entry.id} → {db_alias}")
#             except Exception as e:
#                 errors += 1
#                 print(f"❌ {rid}: {e}")

#     print(f"\n✅ Done. Entries created: {created}, skipped: {skipped}, errors: {errors}")

#correction with the mag_id and virtual_account_type in data entry
# # import dataentry tbl 2024-25
# import os
# import shutil
# from pathlib import Path
# from datetime import datetime, date
# import pandas as pd
# from django.conf import settings
# from django.db import transaction
# from accounts.models import Client, AccountBank, UserData, DataEntry
# from accounts.utills import get_fiscal_year_from_date


# def import_data_entries():
#     r"""Import DataEntry from CSV: Z:\Kameet Soft Project\Database\trans_tbl_1.csv"""
#     excel_path = r'Z:\Kameet Soft Project\Database\trans_tbl_1.csv'

#     # 1) Load CSV
#     if not os.path.exists(excel_path):
#         print(f"❌ CSV not found: {excel_path}")
#         return
#     df = pd.read_csv(excel_path)
#     df.columns = df.columns.str.strip().str.lower()

#     # 2) Normalize common headers
#     rename_map = {
#         "clientid": "client_id",
#         "client": "client_id",
#         "client_name": "client_name",

#         "accid": "account_id",
#         "accountid": "account_id",
#         "account": "account_id",

#         "recdate": "rec_date",
#         "recformat": "format",
#         "recby": "received_by",

#         "fromdate": "from_date",
#         "lastdate": "last_date",

#         "allotedto": "alloted_to",
#         "alloted_to_user": "alloted_to",
#         "user": "alloted_to",
#         "allocate_to": "alloted_to",

#         "alloteddate": "alloted_date",
#         "donedate": "done_date",

#         "timestamp": "timestamp",
#         "nil": "nil",

#         "status": "status",
#         "query": "query",
#         "remark": "remark",

#         "filelink": "source_file",
#         "attach": "source_file",
#         "attach_path": "source_file",
#         "attachment": "source_file",

#         "virtual": "virtual_account_type",
#         "virtual_account": "virtual_account_type",
#         # msg id (accept both)
#         "message_id": "msg_id",
#         "msgid": "msg_id",
#         "messageid": "msg_id",
#     }
#     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

#     # 3) Ensure columns exist
#     needed = [
#         "client_id", "client_name", "account_id", "virtual_account_type", "alloted_to",
#         "rec_date", "from_date", "last_date", "alloted_date", "done_date",
#         "format", "received_by", "status", "query", "remark", "msg_id",
#         "source_file"
#     ]
#     for col in needed:
#         if col not in df.columns:
#             df[col] = None

#     # ---- helpers ----
#     def _parse_date(x):
#         if pd.isna(x) or x is None or str(x).strip() == "":
#             return None
#         if isinstance(x, (datetime, pd.Timestamp)):
#             return x.date()
#         for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y"):
#             try:
#                 return datetime.strptime(str(x).strip(), fmt).date()
#             except Exception:
#                 continue
#         # try pandas as fallback
#         try:
#             d = pd.to_datetime(str(x).strip(), dayfirst=True, errors="coerce")
#             if pd.notna(d):
#                 return d.date()
#         except Exception:
#             pass
#         return None

#     def _nz(v):
#         return "" if pd.isna(v) or v is None else str(v).strip()

#     def _choose_db(from_date_val, last_date_val):
#         base = from_date_val or last_date_val or date.today()
#         fy = get_fiscal_year_from_date(base)   # e.g., "2024_25"
#         return f"fy_{fy}"

#     def _copy_attach(entry, src_path, db_alias):
#         """Copy file to MEDIA_ROOT/fy_xxxx_xx/client_id/account_id/id.ext"""
#         if not src_path or not os.path.exists(src_path):
#             return
#         try:
#             client_part = entry.client.client_id.strip()
#             acc_part = (entry.account.account_id if entry.account else "unknown-account")
#             ext = Path(src_path).suffix or ""
#             rel_path = os.path.join(db_alias, client_part, acc_part, f"{entry.id}{ext}")
#             dest_path = os.path.join(settings.MEDIA_ROOT, rel_path)
#             os.makedirs(os.path.dirname(dest_path), exist_ok=True)
#             shutil.copy2(src_path, dest_path)
#             entry.attach_file.name = rel_path
#             entry.save(using=db_alias, update_fields=["attach_file"])
#             print(f"📎 Copied attachment for {entry.id}")
#         except Exception as e:
#             print(f"⚠️ Attachment copy failed for {entry.id}: {e}")

#     def _virtual_from_account_id(acc_id_text: str):
#         """Return '1' or '2' if account_id indicates a virtual account, else None."""
#         if acc_id_text in ("1", "2"):
#             return acc_id_text
#         # Also handle numeric 1/2 that may have come as float (e.g., 1.0/2.0)
#         try:
#             if acc_id_text and str(int(float(acc_id_text))) in ("1", "2"):
#                 return str(int(float(acc_id_text)))
#         except Exception:
#             pass
#         return None

#     # ---- import ----
#     created, skipped, errors = 0, 0, 0

#     with transaction.atomic():
#         for idx, row in df.iterrows():
#             rid = f"row {idx+1}"

#             client_id = _nz(row.get("client_id"))
#             client_name = _nz(row.get("client_name"))

#             client_obj = None
#             if client_id:
#                 client_obj = Client.objects.filter(client_id=client_id).first()
#             if not client_obj and client_name:
#                 client_obj = Client.objects.filter(client_name__iexact=client_name).first()

#             if not client_obj:
#                 print(f"❌ {rid}: Client not found ({client_id or client_name})")
#                 skipped += 1
#                 continue

#             # account_id handling (virtual beats account resolution)
#             acc_code_raw = _nz(row.get("account_id"))
#             # prefer deriving virtual from account_id ("1"/"2")
#             virtual_from_acc = _virtual_from_account_id(acc_code_raw)
#             # also accept explicit CSV virtual value if already correct
#             explicit_virtual = _nz(row.get("virtual_account_type"))
#             explicit_virtual = explicit_virtual if explicit_virtual in ("1", "2") else None
#             # final virtual value
#             virtual_value = virtual_from_acc or explicit_virtual

#             # real account only when NOT virtual
#             account_obj = None
#             if not virtual_value and acc_code_raw:
#                 account_obj = AccountBank.objects.filter(
#                     client=client_obj, account_id=acc_code_raw
#                 ).first()

#             # user
#             user_obj = None
#             alloted = _nz(row.get("alloted_to"))
#             if alloted:
#                 user_obj = UserData.objects.filter(username__iexact=alloted).first()

#             # dates
#             rec_date = _parse_date(row.get("rec_date"))
#             from_date = _parse_date(row.get("from_date"))
#             last_date = _parse_date(row.get("last_date"))
#             alloted_date = _parse_date(row.get("alloted_date"))
#             done_date = _parse_date(row.get("done_date"))

#             if not from_date or not last_date:
#                 print(f"⚠️ {rid}: Missing from/last date, skipped.")
#                 skipped += 1
#                 continue

#             db_alias = _choose_db(from_date, last_date)

#             # Nil flag
#             nil_val = _nz(row.get("nil")).lower()
#             is_nil_flag = nil_val in ("1", "yes", "y", "true", "done", "nil")

#             # msg_id: accept either msg_id or message_id (already normalized)
#             msg_id_val = _nz(row.get("msg_id")) or None

#             try:
#                 entry = DataEntry(
#                     client=client_obj,
#                     account=account_obj,
#                     alloted_to=user_obj,
#                     virtual_account_type=virtual_value,   # ✅ set from account_id/explicit
#                     rec_date=rec_date,
#                     from_date=from_date,
#                     last_date=last_date,
#                     alloted_date=alloted_date,
#                     done_date=done_date,
#                     format=_nz(row.get("format")) or "Soft Copy",
#                     received_by=_nz(row.get("received_by")) or "Mail",
#                     status=_nz(row.get("status")) or None,
#                     query=_nz(row.get("query")) or None,
#                     remark=_nz(row.get("remark")) or None,
#                     msg_id=msg_id_val,                    # ✅ stored properly
#                     is_nil=is_nil_flag if not _nz(row.get("status")) else (_nz(row.get("status")).lower()=="nil"),
#                 )
#                 entry.save(using=db_alias)

#                 # copy attachment if present
#                 src_file = _nz(row.get("source_file"))
#                 if src_file and os.path.exists(src_file):
#                     _copy_attach(entry, src_file, db_alias)

#                 created += 1
#                 print(f"✔ Imported {rid}: id={entry.id} → {db_alias}")
#             except Exception as e:
#                 errors += 1
#                 print(f"❌ {rid}: {e}")

#     print(f"\n✅ Done. Entries created: {created}, skipped: {skipped}, errors: {errors}")

import os
import shutil
from pathlib import Path
from datetime import datetime, date
import pandas as pd
from django.conf import settings
from django.db import transaction
from accounts.models import Client, AccountBank, UserData, DataEntry


# 🔁 Change this path to where fy_25_26.xlsx is on *your* system
EXCEL_PATH = r"Z:\Kameet Soft Project\Database\DataEntry.xlsx"

# 🔁 This is the DB alias where entries will be saved
TARGET_DB_ALIAS = "fy_2025_26"


def import_data_entries_25_26():
    r"""Import DataEntry for FY 2025-26 from Excel: fy_25_26.xlsx → DB fy_2025_26"""

    # 1) Load Excel
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Excel file not found: {EXCEL_PATH}")
        return

    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip().str.lower()

    # 2) Normalize common headers
    rename_map = {
        "clientid": "client_id",
        "client": "client_id",
        "client_name": "client_name",

        "accid": "account_id",
        "accountid": "account_id",
        "account": "account_id",

        "recdate": "rec_date",
        "recformat": "format",
        "recby": "received_by",

        "fromdate": "from_date",
        "lastdate": "last_date",

        "allotedto": "alloted_to",
        "alloted_to_user": "alloted_to",
        "user": "alloted_to",
        "allocate_to": "alloted_to",

        "alloteddate": "alloted_date",
        "donedate": "done_date",

        "timestamp": "timestamp",
        "nil": "nil",

        "status": "status",
        "query": "query",
        "remark": "remark",

        "filelink": "source_file",
        "attach": "source_file",
        "attach_path": "source_file",
        "attachment": "source_file",

        "virtual": "virtual_account_type",
        "virtual_account": "virtual_account_type",

        "message_id": "msg_id",
        "msgid": "msg_id",
        "messageid": "msg_id",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 3) Ensure columns exist
    needed = [
        "client_id", "client_name", "account_id", "virtual_account_type", "alloted_to",
        "rec_date", "from_date", "last_date", "alloted_date", "done_date",
        "format", "received_by", "status", "query", "remark", "msg_id",
        "source_file"
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = None

    # ---- helpers ----
    def _parse_date(x):
        if pd.isna(x) or x is None or str(x).strip() == "":
            return None
        if isinstance(x, (datetime, pd.Timestamp)):
            return x.date()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y"):
            try:
                return datetime.strptime(str(x).strip(), fmt).date()
            except Exception:
                continue
        try:
            d = pd.to_datetime(str(x).strip(), dayfirst=True, errors="coerce")
            if pd.notna(d):
                return d.date()
        except Exception:
            pass
        return None

    def _nz(v):
        return "" if pd.isna(v) or v is None else str(v).strip()

    def _copy_attach(entry, src_path, db_alias):
        """Copy file to MEDIA_ROOT/fy_xxxx_xx/client_id/account_id/id.ext"""
        if not src_path or not os.path.exists(src_path):
            return
        try:
            client_part = entry.client.client_id.strip()
            acc_part = (entry.account.account_id if entry.account else "unknown-account")
            ext = Path(src_path).suffix or ""
            rel_path = os.path.join(db_alias, client_part, acc_part, f"{entry.id}{ext}")
            dest_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
            entry.attach_file.name = rel_path
            entry.save(using=db_alias, update_fields=["attach_file"])
            print(f"📎 Copied attachment for {entry.id}")
        except Exception as e:
            print(f"⚠️ Attachment copy failed for {entry.id}: {e}")

    def _virtual_from_account_id(acc_id_text: str):
        """Return '1' or '2' if account_id indicates a virtual account, else None."""
        if acc_id_text in ("1", "2"):
            return acc_id_text
        try:
            if acc_id_text and str(int(float(acc_id_text))) in ("1", "2"):
                return str(int(float(acc_id_text)))
        except Exception:
            pass
        return None

    created, skipped, errors = 0, 0, 0

    with transaction.atomic():
        for idx, row in df.iterrows():
            rid = f"row {idx+1}"

            client_id = _nz(row.get("client_id"))
            client_name = _nz(row.get("client_name"))

            client_obj = None
            if client_id:
                client_obj = Client.objects.filter(client_id=client_id).first()
            if not client_obj and client_name:
                client_obj = Client.objects.filter(client_name__iexact=client_name).first()

            if not client_obj:
                print(f"❌ {rid}: Client not found ({client_id or client_name})")
                skipped += 1
                continue

            # account_id / virtual
            acc_code_raw = _nz(row.get("account_id"))
            virtual_from_acc = _virtual_from_account_id(acc_code_raw)
            explicit_virtual = _nz(row.get("virtual_account_type"))
            explicit_virtual = explicit_virtual if explicit_virtual in ("1", "2") else None
            virtual_value = virtual_from_acc or explicit_virtual

            account_obj = None
            if not virtual_value and acc_code_raw:
                account_obj = AccountBank.objects.filter(
                    client=client_obj, account_id=acc_code_raw
                ).first()

            # user
            user_obj = None
            alloted = _nz(row.get("alloted_to"))
            if alloted:
                user_obj = UserData.objects.filter(username__iexact=alloted).first()

            # dates
            rec_date = _parse_date(row.get("rec_date"))
            from_date = _parse_date(row.get("from_date"))
            last_date = _parse_date(row.get("last_date"))
            alloted_date = _parse_date(row.get("alloted_date"))
            done_date = _parse_date(row.get("done_date"))

            if not from_date or not last_date:
                print(f"⚠️ {rid}: Missing from/last date, skipped.")
                skipped += 1
                continue

            # 🔒 For this import we *force* everything into fy_2025_26
            db_alias = TARGET_DB_ALIAS

            nil_val = _nz(row.get("nil")).lower()
            is_nil_flag = nil_val in ("1", "yes", "y", "true", "done", "nil")

            msg_id_val = _nz(row.get("msg_id")) or None

            try:
                entry = DataEntry(
                    client=client_obj,
                    account=account_obj,
                    alloted_to=user_obj,
                    virtual_account_type=virtual_value,
                    rec_date=rec_date,
                    from_date=from_date,
                    last_date=last_date,
                    alloted_date=alloted_date,
                    done_date=done_date,
                    format=_nz(row.get("format")) or "Soft Copy",
                    received_by=_nz(row.get("received_by")) or "Mail",
                    status=_nz(row.get("status")) or None,
                    query=_nz(row.get("query")) or None,
                    remark=_nz(row.get("remark")) or None,
                    msg_id=msg_id_val,
                    is_nil=is_nil_flag if not _nz(row.get("status")) else (_nz(row.get("status")).lower() == "nil"),
                )
                entry.save(using=db_alias)

                src_file = _nz(row.get("source_file"))
                if src_file and os.path.exists(src_file):
                    _copy_attach(entry, src_file, db_alias)

                created += 1
                print(f"✔ Imported {rid}: id={entry.id} → {db_alias}")
            except Exception as e:
                errors += 1
                print(f"❌ {rid}: {e}")

    print(f"\n✅ Done (FY 2025-26). Entries created: {created}, skipped: {skipped}, errors: {errors}")


# # Statement Password
# # import pandas as pd
# # from django.db import transaction
# # from accounts.models import Client, AccountBank


# # def import_stmt_passwords():
# #     r"""Update AccountBank.stms_pws from Excel: Z:\Kameet Soft Project\Database\AccTbl_new.xlsx"""
# #     excel_path = r"Z:\Kameet Soft Project\Database\AccTbl_new.xlsx"

# #     # 1) Load and normalize headers
# #     df = pd.read_excel(excel_path)
# #     df.columns = df.columns.str.strip().str.lower()

# #     # 2) Minimal rename map (ONLY your current headers)
# #     # Excel: ClientID, AccID, StmPs
# #     rename_map = {
# #         "clientid": "client_id",
# #         "accid": "account_id",
# #         "stmps": "stmt_pwd",
# #     }
# #     df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

# #     # 3) Ensure needed columns exist
# #     for col in ["client_id", "account_id", "stmt_pwd"]:
# #         if col not in df.columns:
# #             df[col] = None

# #     def _nz(x):
# #         if x is None:
# #             return ""
# #         try:
# #             import math
# #             if isinstance(x, float) and math.isnan(x):
# #                 return ""
# #         except Exception:
# #             pass
# #         return str(x).strip()

# #     updated = 0
# #     unchanged = 0
# #     not_found_client = 0
# #     not_found_account = 0
# #     skipped = 0

# #     with transaction.atomic():
# #         for i, row in df.iterrows():
# #             rid = f"row {i+1}"
# #             client_code = _nz(row.get("client_id"))
# #             account_code = _nz(row.get("account_id"))
# #             pwd = _nz(row.get("stmt_pwd"))

# #             # must have all three
# #             if not client_code or not account_code or not pwd:
# #                 print(f"⚠️ {rid}: missing ClientID/AccID/StmPs → skipped")
# #                 skipped += 1
# #                 continue

# #             client = Client.objects.filter(client_id=client_code).first()
# #             if not client:
# #                 print(f"❌ {rid}: client '{client_code}' not found")
# #                 not_found_client += 1
# #                 continue

# #             acc = AccountBank.objects.filter(client=client, account_id=account_code).first()
# #             if not acc:
# #                 print(f"❌ {rid}: account '{account_code}' not found for client '{client_code}'")
# #                 not_found_account += 1
# #                 continue

# #             if (acc.stms_pws or "") == pwd:
# #                 unchanged += 1
# #                 # print(f"· {rid}: unchanged for {client_code}/{account_code}")
# #                 continue

# #             acc.stms_pws = pwd
# #             acc.save(update_fields=["stms_pws"])
# #             print(f"✔ {rid}: {client_code}/{account_code} → stms_pws updated")
# #             updated += 1

# #     print(
# #         f"\nDone. Updated: {updated}, unchanged: {unchanged}, "
# #         f"missing client: {not_found_client}, missing account: {not_found_account}, skipped: {skipped}"
# #     )


# # Virtual_account_type and Msg_id in Data entry
# # accounts/fix_dataentry_msg_virtual.py
# # --- paste this into Django shell ---

# # --- paste into Django shell ---

# import os
# import pandas as pd
# from datetime import datetime, date
# from django.db import transaction, connections
# from django.core.exceptions import ImproperlyConfigured
# from accounts.models import Client, DataEntry
# from accounts.utills import get_fiscal_year_from_date

# # Your fixed path
# CSV_PATH = r'Z:\Kameet Soft Project\Database\trans_tbl_1.csv'

# # Flexible header getters
# def _nz(v, default=""):
#     if v is None:
#         return default
#     try:
#         import pandas as pd
#         if pd.isna(v):
#             return default
#     except Exception:
#         pass
#     return str(v).strip()

# def _get_any(row, *names):
#     for n in names:
#         if n in row:
#             val = row.get(n)
#             if val is not None:
#                 s = _nz(val, "")
#                 if s != "":
#                     return s
#     return ""

# def _parse_date(v):
#     s = _nz(v, "")
#     if not s:
#         return None
#     fmts = ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%Y/%m/%d","%d-%b-%Y","%d %b %Y","%d-%b-%y","%d/%b/%Y")
#     for f in fmts:
#         try:
#             return datetime.strptime(s, f).date()
#         except ValueError:
#             continue
#     # Try pandas fallback
#     try:
#         d = pd.to_datetime(s, dayfirst=True, errors="coerce")
#         if pd.notna(d):
#             return d.date()
#     except Exception:
#         pass
#     return None

# def _fy_alias_candidates(from_dt, last_dt):
#     ref = from_dt or last_dt or date.today()
#     fy = get_fiscal_year_from_date(ref)    # e.g. "2024_25"
#     # Try your common patterns
#     return [
#         f"fy_{fy}",
#         f"kameet_{fy}",
#         fy,  # sometimes people actually named alias as "2024_25"
#     ]

# def _pick_virtual(acc_id):
#     if acc_id == "1": return "1"  # Sales
#     if acc_id == "2": return "2"  # Purchase
#     return None

# def _alias_exists(alias):
#     try:
#         _ = connections.databases[alias]
#         return True
#     except Exception:
#         return False

# def fix_msg_and_virtual():
#     if not os.path.exists(CSV_PATH):
#         print(f"❌ CSV not found: {CSV_PATH}")
#         return

#     df = pd.read_csv(CSV_PATH)
#     df.columns = df.columns.str.strip().str.lower()

#     updated, skipped = 0, 0

#     with transaction.atomic():
#         for i, r in df.iterrows():
#             # Flexible column mapping
#             client_id_txt = _get_any(r,
#                 "client_id","clientid","client","client id","client_name","clientname"
#             )
#             acc_id_txt = _get_any(r,
#                 "account_id","accountid","accid","account id"
#             )
#             msg_id_txt = _get_any(r,
#                 "msg_id","message_id","msgid","messageid"
#             )

#             from_dt = _parse_date(r.get("from_date"))
#             if not from_dt:
#                 from_dt = _parse_date(_get_any(r,"fromdate","from dt","from"))
#             last_dt = _parse_date(r.get("last_date"))
#             if not last_dt:
#                 last_dt = _parse_date(_get_any(r,"lastdate","to_date","todate","to dt","to"))
#             rec_dt = _parse_date(_get_any(r,"rec_date","received_date","recdate","received dt"))

#             if not client_id_txt:
#                 print(f"Row {i}: skip (no client_id)")
#                 skipped += 1
#                 continue

#             try:
#                 client = Client.objects.get(client_id=client_id_txt)
#             except Client.DoesNotExist:
#                 print(f"Row {i}: skip (client '{client_id_txt}' not found)")
#                 skipped += 1
#                 continue

#             desired_virtual = _pick_virtual(acc_id_txt)

#             # Decide DB alias (try multiple patterns)
#             alias_list = _fy_alias_candidates(from_dt, last_dt)
#             alias_hit = None
#             for alias in alias_list:
#                 if _alias_exists(alias):
#                     alias_hit = alias
#                     break
#             if not alias_hit:
#                 print(f"Row {i}: skip (no matching DB alias among {alias_list})")
#                 skipped += 1
#                 continue

#             qs = DataEntry.objects.using(alias_hit).filter(client=client)

#             # Try specific→broad filters
#             buckets = [
#                 qs.filter(from_date=from_dt, last_date=last_dt, rec_date=rec_dt),
#                 qs.filter(from_date=from_dt, last_date=last_dt),
#                 qs.filter(from_date=from_dt, rec_date=rec_dt),
#                 qs.filter(last_date=last_dt, rec_date=rec_dt),
#                 qs.filter(from_date=from_dt),
#                 qs.filter(last_date=last_dt),
#                 qs.filter(rec_date=rec_dt),
#             ]

#             target_qs = None
#             for b in buckets:
#                 if b.exists():
#                     target_qs = b
#                     break

#             if not target_qs:
#                 print(f"Row {i}: skip (no rows found in {alias_hit} for client={client_id_txt}, dates from={from_dt}, to={last_dt}, rec={rec_dt})")
#                 skipped += 1
#                 continue

#             # If multiple, update all (we're only touching two fields)
#             count = target_qs.count()
#             changed_here = 0

#             for de in target_qs:
#                 changed = False
#                 if desired_virtual and de.virtual_account_type != desired_virtual:
#                     de.virtual_account_type = desired_virtual
#                     changed = True
#                 if msg_id_txt and _nz(de.msg_id) != msg_id_txt:
#                     de.msg_id = msg_id_txt
#                     changed = True
#                 if changed:
#                     de.save(using=alias_hit, update_fields=["virtual_account_type","msg_id"])
#                     changed_here += 1

#             if changed_here == 0:
#                 # nothing needed updating in these matches
#                 skipped += 1
#             else:
#                 updated += changed_here

#     print(f"✅ Done. Updated (rows changed): {updated}, Skipped: {skipped}")
