import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

DEFAULT_CREDS = Path.home() / ".secrets" / "firstwave" / "google-credentials.json"
creds_path = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", str(DEFAULT_CREDS))

flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
creds = flow.run_local_server(port=0)
print("REFRESH TOKEN:", creds.refresh_token)
