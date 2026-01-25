import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Email Fetch Configuration
EMAIL_FETCH_HOURS = 48  # Fetch emails from last 48 hours (24h + delta)
EMAIL_FETCH_DELTA_HOURS = 24  # Delta buffer

# Database Configuration
DATABASE_PATH = "email_brief.db"

# Gmail OAuth Configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"

# AI Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
SUMMARY_MODEL = "gpt-4o-mini"

# Email Delivery Configuration
EMAIL_DELIVERY_CONFIG = {
    'enabled': os.getenv('EMAIL_DELIVERY_ENABLED', 'false').lower() == 'true',
    'from_email': os.getenv('EMAIL_FROM', 'noreply@dailybrief.local'),
    'smtp_server': os.getenv('SMTP_SERVER', ''),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'smtp_username': os.getenv('SMTP_USERNAME', ''),
    'smtp_password': os.getenv('SMTP_PASSWORD', ''),
}
