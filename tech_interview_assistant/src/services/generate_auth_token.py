import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# check more scope available at https://developers.google.com/gmail/api/auth/scopes
SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/drive'
        ]

def get_auth_token(credential_file_path, token_file_path, scopes=SCOPES):
    """
    sourced from: https://python.langchain.com/v0.2/docs/integrations/chat_loaders/gmail/

    Args:
        credential_file_path (_type_): _description_
        token_file_path (_type_): _description_
        scopes (_type_, optional): _description_. Defaults to SCOPES.
    """
    creds = None

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credential_file_path,
                scopes,
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file_path, "w") as token:
            token.write(creds.to_json())
    print(f"Generated auth2.0 token files at: {token_file_path}")
