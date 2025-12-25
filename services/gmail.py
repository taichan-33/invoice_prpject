import google.auth
from googleapiclient.discovery import build
import config

_service = None

def get_gmail_service():
    """
    Lazy loads the Gmail API service.
    """
    global _service
    if _service:
        return _service
        
    creds = None
    
    # 1. Try to use Refresh Token if available (Prioritize for Personal Gmail)
    if config.GMAIL_REFRESH_TOKEN and config.GMAIL_CLIENT_ID and config.GMAIL_CLIENT_SECRET:
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            None, # access_token (will be refreshed)
            refresh_token=config.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.GMAIL_CLIENT_ID,
            client_secret=config.GMAIL_CLIENT_SECRET,
            scopes=config.GMAIL_SCOPES
        )
    
    # 2. Fallback to ADC (Service Account / gcloud auth application-default)
    if not creds:
        creds, project = google.auth.default(scopes=config.GMAIL_SCOPES)
        
    _service = build('gmail', 'v1', credentials=creds)
    return _service
