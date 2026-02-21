# import os
# from django.conf import settings
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build

# SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# def link_once() -> str:
#     """
#     Opens a consent window (on the machine running the server),
#     stores the OAuth token under gmail_tokens/<email>.json, and
#     returns that email address.
#     """
#     os.makedirs(settings.GMAIL_TOKEN_DIR, exist_ok=True)
#     flow = InstalledAppFlow.from_client_secrets_file(settings.GMAIL_CLIENT_SECRETS_FILE, SCOPES)
#     creds = flow.run_local_server(port=0)
#     svc = build("gmail", "v1", credentials=creds)
#     email = svc.users().getProfile(userId="me").execute()["emailAddress"]
#     token_path = os.path.join(settings.GMAIL_TOKEN_DIR, f"{email}.json")
#     with open(token_path, "w") as f:
#         f.write(creds.to_json())
#     return email

# def linked_accounts():
#     os.makedirs(settings.GMAIL_TOKEN_DIR, exist_ok=True)
#     return [f[:-5] for f in os.listdir(settings.GMAIL_TOKEN_DIR) if f.endswith(".json")]
