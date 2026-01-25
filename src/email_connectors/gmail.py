import os
import base64
import json
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import GMAIL_SCOPES, GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, EMAIL_FETCH_HOURS


class GmailConnector:
    """Gmail connector using OAuth2 for authentication."""
    
    def __init__(self):
        self.service = None
        self.creds = None
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token
        if os.path.exists(GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                    print(f"Error: {GMAIL_CREDENTIALS_FILE} not found.")
                    print("Please download OAuth2 credentials from Google Cloud Console:")
                    print("https://console.cloud.google.com/apis/credentials")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(GMAIL_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def fetch_recent_emails(self, hours: int = EMAIL_FETCH_HOURS) -> List[Dict]:
        """
        Fetch emails from the last N hours.
        
        Args:
            hours: Number of hours to look back (default from config)
            
        Returns:
            List of email dictionaries with metadata and content
        """
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            # Query for emails after cutoff time
            query = f'after:{cutoff_timestamp}'
            
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=100).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                try:
                    email_data = self._get_message_details(msg['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    print(f"Error fetching message {msg['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def _get_message_details(self, msg_id: str) -> Optional[Dict]:
        """Get full details of a message."""
        try:
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full').execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse date
            try:
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            return {
                'id': msg_id,
                'subject': subject,
                'sender': sender,
                'date': date.isoformat(),
                'snippet': message.get('snippet', ''),
                'body': body[:1000],  # Limit body to first 1000 chars
                'thread_id': message.get('threadId', ''),
            }
        except Exception as e:
            print(f"Error getting message details: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    # Prefer plain text, but use HTML if no plain text
                    if not body:
                        data = part['body'].get('data')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
