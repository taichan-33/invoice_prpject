import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config
import logging

logger = logging.getLogger(__name__)

_service = None
_oauth_alert_sent = False  # 同じセッション中で重複アラートを防ぐフラグ

def get_gmail_service():
    """
    Lazy loads the Gmail API service.
    """
    global _service, _oauth_alert_sent
    if _service:
        return _service
        
    creds = None
    
    try:
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
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gmail API認証エラー: {error_msg}")
        
        # OAuthエラーの検知とSlack通知
        if not _oauth_alert_sent:
            try:
                import services.slack
                alert_msg = f"Gmail API認証失敗 🚨\n```{error_msg}```\n\n*⚠️ OAuthトークンが無効化された可能性があります。手動でのトークン再取得が必要です。*"
                services.slack.send_slack_alert(alert_msg, level="error")
                _oauth_alert_sent = True
            except:
                pass  # Slack送信失敗しても元のエラーを投げる
        
        raise

def get_or_create_label_id(label_name: str) -> str:
    """
    指定されたラベル名のIDを取得します。
    存在しない場合は新規作成してそのIDを返します。
    """
    srv = get_gmail_service()
    
    try:
        # 1. 既存ラベルのリストを取得
        results = srv.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        # 2. 名前で検索
        for label in labels:
            if label['name'] == label_name:
                return label['id']
                
        # 3. なければ作成
        print(f"Creating new label: {label_name}")
        created_label = srv.users().labels().create(
            userId='me',
            body={
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
        ).execute()
        return created_label['id']
        
    except Exception as e:
        print(f"Error getting/creating label: {e}")
        raise
