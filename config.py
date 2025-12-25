import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# App Environment
APP_ENV = os.getenv("APP_ENV", "production")

# Google Cloud Config
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
BUCKET_NAME_TEMPLATE = "invoice-archive-{}" 
BQ_TABLE_ID = f"{PROJECT_ID}.invoice_data.invoice_log"

# Gmail API Config
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TARGET_LABEL = os.getenv("TARGET_LABEL", "TARGET")

# OAuth Config
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

# Filtering Config
ALLOWED_DOMAINS = [d.strip() for d in os.getenv("ALLOWED_DOMAINS", "").split(",") if d.strip()]
SUBJECT_KEYWORDS = [k.strip() for k in os.getenv("SUBJECT_KEYWORDS", "").split(",") if k.strip()]
