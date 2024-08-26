from typing import List, Dict, Any
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_community.tools.gmail.search import GmailSearch
from langchain_community.tools.gmail.utils import (clean_email_body, build_resource_service)
from ipdb import set_trace



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


def read_emails_from_senders(credentials, sender_address: list, limit =10) -> str:
    """Reads emails from a list of known senders."""

    try:
        service = build('gmail', 'v1', credentials=credentials)
        query = " OR ".join([f"from:{sender}" for sender in sender_address])
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        email_data = []
        if not messages:
            return 'No messages found from specified senders.'
        else:
            messages = messages[:limit] if limit is not None else messages
            for message in messages:  # Limiting to the first 10 messages for simplicity
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