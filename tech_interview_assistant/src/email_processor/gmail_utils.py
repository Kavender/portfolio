from typing import List, Dict, Any
import os
import time
import base64
import socket
from email import message_from_bytes
from dotenv import load_dotenv, find_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain_community.tools.gmail.search import GmailSearch
from langchain_google_community.gmail.utils import get_gmail_credentials
from langchain_community.tools.gmail.utils import clean_email_body, build_resource_service
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception
from src.utils.logger import default_logger as logger


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
    except (RefreshError, ValueError, IOError, Exception) as e:
        logger.warning(f"Credential error: {str(e)}. Regenerating token.")
        # Check if token file exists before trying to remove it
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
                logger.info(f"Removed token file {token_file}")
            except Exception as remove_error:
                logger.error(f"Error removing token file: {str(remove_error)}")
        
        # Generate new token
        try:
            get_auth_token(credential_file, token_file, scopes)
            logger.info(f"Regenerated token file at {token_file}")
        except Exception as auth_error:
            logger.error(f"Error generating new token: {str(auth_error)}")
            raise
    
    # Try again with the new token
    try:
        return get_gmail_credentials(
            token_file=token_file,
            scopes=scopes,
            client_secrets_file=os.getenv("GOOGLE_APP_CREDENTIALS"),
        )
    except Exception as retry_error:
        logger.error(f"Failed to get credentials after token regeneration: {str(retry_error)}")
        raise


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


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=(retry_if_exception_type((socket.timeout, ConnectionError, TimeoutError, HttpError)) |
           retry_if_exception(lambda e: isinstance(e, Exception) and 
                             ("Timeout" in str(e) or "connection" in str(e).lower() or 
                              "Connection" in str(e) or "network" in str(e).lower())))
)
def execute_with_retry(request):
    try:
        return request.execute(num_retries=5)
    except Exception as e:
        logger.warning(f"Request failed, will retry: {str(e)}")
        time.sleep(2)
        raise


def read_emails_from_senders(credentials, sender_addresses: list, limit=10, since_timestamp=None, timeout=900) -> str:
    """
    Reads emails from a list of known senders, optionally filtering by timestamp.
    
    Args:
        credentials: Google API credentials
        sender_addresses: List of sender email addresses to filter by
        limit: Maximum number of emails to process
        since_timestamp: Optional datetime object to filter emails by timestamp
        timeout: Timeout in seconds for API requests (default: 900)
        
    Returns:
        List of email data dictionaries or error message string
    """
    if not credentials:
        logger.error("No credentials provided")
        return "Error: No credentials provided"
        
    if not sender_addresses:
        logger.warning("No sender addresses provided, will fetch all emails")

    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    logger.info(f"Set socket timeout to {timeout} seconds")
    
    try:
        service = build('gmail', 'v1', credentials=credentials)
        sender_query = " OR ".join([f"from:{sender}" for sender in sender_addresses])
        
        # Add timestamp filter if provided
        if since_timestamp:
            # Convert datetime to Unix timestamp in seconds
            if hasattr(since_timestamp, 'timestamp'):
                unix_timestamp = int(since_timestamp.timestamp())
                timestamp_query = f"after:{unix_timestamp}"
                query = f"({sender_query}) AND {timestamp_query}"
            else:
                # If since_timestamp is not a datetime object, log a warning and use only sender query
                logger.warning(f"Invalid timestamp format: {since_timestamp}. Using only sender filter.")
                query = sender_query
        else:
            query = sender_query
        
        logger.info(f"Executing Gmail API query: {query}")
        
        # Execute the query with pagination
        page_token = None
        all_messages = []
        
        while True:
            try:
                # Use pagination to get results in smaller chunks
                # Use a smaller chunk size to reduce the chance of timeouts
                chunk_size = min(50, limit if limit else 50)
                logger.info(f"Fetching messages with chunk size: {chunk_size}")
                
                request = service.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token,
                    maxResults=chunk_size
                )
                
                # Add a progress log
                logger.info(f"Executing API request (page token: {page_token})")
                start_time = time.time()
                
                results = execute_with_retry(request)
                
                # Log the time taken
                elapsed = time.time() - start_time
                logger.info(f"API request completed in {elapsed:.2f} seconds")
                
                messages = results.get('messages', [])
                if messages:
                    logger.info(f"Retrieved {len(messages)} messages in this batch")
                    all_messages.extend(messages)
                else:
                    logger.info("No messages found in this batch")
                
                # Check if we have enough messages or if there are no more pages
                if limit and len(all_messages) >= limit:
                    all_messages = all_messages[:limit]
                    break
                
                # Get the next page token
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching message list: {str(e)}")
                raise
        
        email_data = []
        if not all_messages:
            logger.info('No messages found matching the criteria.')
            return []
        else:
            logger.info(f"Found {len(all_messages)} messages, processing up to {limit if limit else 'all'}")

            for i, message in enumerate(all_messages):
                try:
                    logger.info(f"Processing message {i+1}/{len(all_messages)}: {message['id']}")
                    
                    # Add a small delay between processing messages to avoid rate limiting
                    if i > 0 and i % 5 == 0:
                        logger.info(f"Pausing briefly after processing {i} messages")
                        time.sleep(2)
                    
                    request = service.users().messages().get(userId='me', format="raw", id=message['id'])
                    
                    start_time = time.time()
                    mail = execute_with_retry(request)
                    elapsed = time.time() - start_time
                    logger.info(f"Retrieved message {message['id']} in {elapsed:.2f} seconds")
                    
                    mail_data = _parse_messages(message=mail)
                    email_data.append(mail_data)
                    
                    # Log progress periodically
                    if (i+1) % 10 == 0 or i+1 == len(all_messages):
                        logger.info(f"Progress: {i+1}/{len(all_messages)} messages processed")
                        
                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {str(e)}")
                    # Continue processing other messages even if one fails
                    continue             
        return email_data
    except HttpError as error:
        error_msg = f'An error occurred: {error}'
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        # If it's a RetryError, provide more detailed information
        if "RetryError" in str(e):
            logger.error("All retry attempts failed. This could be due to network issues, " +
                         "API rate limits, or the operation taking longer than the timeout period.")
            logger.error("Consider increasing the timeout value or reducing the batch size.")
        return error_msg
    finally:
        # Restore original socket timeout
        socket.setdefaulttimeout(original_timeout)
    

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
        logger.error(f"An error occurred while marking message as read: {error}")
        return None
