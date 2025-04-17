# this is the old gmail_service.py
from typing import List, Dict, Any
import os
import base64
import logging
from email import message_from_bytes
from dotenv import load_dotenv, find_dotenv
from langchain_google_community.gmail.utils import get_gmail_credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_community.tools.gmail.search import GmailSearch
from langchain_community.tools.gmail.get_message import GmailGetMessage
from langchain_community.tools.gmail.utils import (clean_email_body, build_resource_service)
from ipdb import set_trace

logger = logging.getLogger(__name__)
_ = load_dotenv(find_dotenv())

# check more scope available at https://developers.google.com/gmail/api/auth/scopes
DEFAULT_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/documents.readonly'
        ]


def init_google_credentials(scopes=DEFAULT_SCOPES):
    token_file = os.getenv("GOOGLE_APP_TOKEN")
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
        logger.info(f"remove token file {token_file} to regenerate")
    return get_google_credentials(credential_file=os.getenv("GOOGLE_APP_CREDENTIALS"),
        token_file=token_file, scopes=scopes)


def get_auth_token(credential_file_path, token_file_path, scopes=DEFAULT_SCOPES):
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
    logger.info(f"Generated auth2.0 token files at: {token_file_path}")


def fetch_emails(credentials, sender_address=None, limit=None):
    api_resource = build_resource_service(credentials=credentials)
    search = GmailSearch(api_resource=api_resource)
    emails = search._run(query="in:read", max_results=1000)

    mails = []
    count_emails = 0
    for mail in emails:
        sender = mail['sender']
        if sender_address and sender not in sender_address:
            continue
        mails.append({
            "id": mail["id"],
            "thread_id": mail["threadId"],
            "date": mail["date"],
            "sender": mail["sender"],
            "snippet": mail["snippet"],
            "subject": mail["subject"],
            "body": mail["body"]
        })
        count_emails += 1
        if limit and count_emails >= limit:
            break
    return mails


def read_emails_from_senders(credentials, sender_addresses: list, limit =10) -> str:
    """Reads emails from a list of known senders."""

    try:
        service = build('gmail', 'v1', credentials=credentials)
        query = " OR ".join([f"from:{sender}" for sender in sender_addresses])
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        email_data = []
        if not messages:
            return 'No messages found from specified senders.'
        else:
            messages = messages[:limit] if limit is not None else messages
            for message in messages:
                mail = service.users().messages().get(userId='me', format="raw", id=message['id']).execute()
                mail_data = _parse_messages(message=mail)
                email_data.append(mail_data)
        return email_data
    except HttpError as error:
        return f'An error occurred: {error}'
    

def _parse_messages(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_message = base64.urlsafe_b64decode(message["raw"])

    email_msg = message_from_bytes(raw_message)

    subject = email_msg["Subject"]
    sender = email_msg["From"]

    message_body = ""
    if email_msg.is_multipart():
        for part in email_msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdispo:
                try:
                    message_body = part.get_payload(decode=True).decode("utf-8")  # type: ignore[union-attr]
                except UnicodeDecodeError:
                    message_body = part.get_payload(decode=True).decode(  # type: ignore[union-attr]
                        "latin-1"
                    )
                break
    else:
        message_body = email_msg.get_payload(decode=True).decode("utf-8")  # type: ignore[union-attr]

    body = clean_email_body(message_body)
    return {
            "id": message["id"],
            "threadId": message["threadId"],
            "date": email_msg["Date"],
            "sender": sender,
            "snippet": message["snippet"],
            "body": body,
            "subject": subject,
            "body": body
        }


def mark_as_read(message_id: str, credentials) -> dict:
    """
    Mark an email as read by removing the 'UNREAD' label from the specified message.
    
    Args:
        message_id (str): The Gmail message ID.
        credentials: Google API credentials.
    
    Returns:
        dict: The result of the modify operation, or None if an error occurs.
    """
    try:
        service = build("gmail", "v1", credentials=credentials)
        result = service.users().messages().modify(
            userId="me", 
            id=message_id, 
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return result
    except HttpError as error:
        print(f"An error occurred while marking message as read: {error}")
        return None