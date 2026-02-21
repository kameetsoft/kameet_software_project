# import os
# from datetime import datetime, timezone
# from email.header import decode_header, make_header
# from email.utils import parsedate_to_datetime

# from django.conf import settings
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build

# from accounts.models import MailLog

# SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# def _decode_hdr(v):
#     if not v: return ""
#     try: return str(make_header(decode_header(v)))
#     except: return v

# def _hdr(headers, name, default=""):
#     for h in headers:
#         if h.get("name","").lower() == name.lower():
#             return h.get("value", default)
#     return default

# def _has_attachments(payload) -> bool:
#     stack = [payload]
#     while stack:
#         p = stack.pop()
#         if p.get("filename"): return True
#         for c in p.get("parts", []) or []:
#             stack.append(c)
#     return False

# def _service_for(mailbox_email: str):
#     token_path = os.path.join(settings.GMAIL_TOKEN_DIR, f"{mailbox_email}.json")
#     if not os.path.exists(token_path):
#         raise RuntimeError(f"No token for {mailbox_email}. Link it first.")
#     creds = Credentials.from_authorized_user_file(token_path, SCOPES)
#     return build("gmail", "v1", credentials=creds)

# def fy_alias_from_date(dt: datetime) -> str:
#     dt = dt.astimezone(timezone.utc)
#     start = dt.year if dt.month >= 4 else dt.year - 1
#     return f"fy_{start}_{(start+1)%100:02d}"

# def fetch_for_account(mailbox_email: str, query="in:inbox newer_than:30d", max_count=200,
#                       auto_fy=False, db_alias="default"):
#     svc = _service_for(mailbox_email)
#     resp = svc.users().messages().list(userId="me", q=query, maxResults=max_count).execute()
#     for m in resp.get("messages", []):
#         mid = m["id"]
#         full = svc.users().messages().get(userId="me", id=mid, format="full").execute()
#         payload = full.get("payload", {})
#         headers = payload.get("headers", [])

#         frm = _hdr(headers, "From")
#         to  = _hdr(headers, "To")
#         sub = _decode_hdr(_hdr(headers, "Subject"))
#         hdt = _hdr(headers, "Date")

#         try:
#             rec_dt = parsedate_to_datetime(hdt)
#             if rec_dt.tzinfo is None: rec_dt = rec_dt.replace(tzinfo=timezone.utc)
#             rec_dt = rec_dt.astimezone(timezone.utc)
#         except Exception:
#             rec_ms = int(full.get("internalDate", "0"))
#             rec_dt = datetime.fromtimestamp(rec_ms/1000.0, tz=timezone.utc)

#         target_db = fy_alias_from_date(rec_dt) if auto_fy else db_alias

#         if MailLog.objects.using(target_db).filter(mailbox=mailbox_email, msg_id=mid).exists():
#             continue

#         MailLog.objects.using(target_db).create(
#             mailbox=mailbox_email,
#             rec_dat=rec_dt,
#             sender_mail=frm,
#             receiver_mail=to,
#             subject=sub,
#             attachment=_has_attachments(payload),
#             msg_id=mid,
#         )
