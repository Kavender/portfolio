import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# https://developers.google.com/gmail/api/auth/scopes
SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/drive'
        ]

def get_auth_token(token_file_path, scopes=SCOPES):
    creds = None

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                scopes,
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file_path, "w") as token:
            token.write(creds.to_json())
    print(f"Generated auth2.0 token files at: {token_file_path}")

if __name__ == "__main__":
    get_auth_token(token_file_path="gmail_token.json", 
                   scopes=['https://www.googleapis.com/auth/gmail.readonly'])