import os
from dotenv import load_dotenv, find_dotenv
from langchain_google_community.gmail.utils import get_gmail_credentials
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from services.generate_auth_token import get_auth_token

_ = load_dotenv(find_dotenv())


DEFAULT_SCOPES = ['https://www.googleapis.com/auth/documents.readonly',
                  'https://www.googleapis.com/auth/gmail.readonly']

def init_google_credentials(scopes=DEFAULT_SCOPES):
    token_file = os.getenv("GOOGLE_APP_TOKEN")
    # try:
    #     return Credentials.from_authorized_user_file(token_file, scopes=scopes)
    # except:
    #     return 
    return get_google_credentials(
        credential_file=os.getenv("GOOGLE_APP_CREDENTIALS"),
        token_file=token_file, scopes=scopes)
    

def get_google_credentials(credential_file, token_file, scopes):
    try:
        return get_gmail_credentials(
            token_file=token_file,
            scopes=scopes,
            client_secrets_file=os.getenv("GOOGLE_APP_CREDENTIALS"),
            )
    except RefreshError:
        os.remove(token_file)
        get_auth_token(credential_file, token_file, scopes)
        print("token file to regenerate", token_file)
    return get_google_credentials(token_file, scopes)
    