from services import gmail
import config
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_watch():
    """
    GmailのPush通知設定（Watch）を行います。
    config.TARGET_LABEL で指定されたラベル（名前）からIDを解決して通知対象とします。
    """
    try:
        # 1. サービスの取得
        srv = gmail.get_gmail_service()
        
        # 2. Watch対象のラベルIDを設定
        # config.TARGET_LABEL は "TARGET" などの「名前」が入っている前提
        target_label_name = config.TARGET_LABEL
        watch_label_ids = ['UNREAD'] # デフォルト

        if target_label_name:
             # 名前からIDを取得 (なければ作成される)
             label_id = gmail.get_or_create_label_id(target_label_name)
             watch_label_ids = [label_id]
             logger.info(f"監視対象: {target_label_name} (ID: {label_id})")
        
        topic_name = f'projects/{config.PROJECT_ID}/topics/gmail-notification'
        logger.info(f"通知先トピック: {topic_name}")

        request = {
            'labelIds': watch_label_ids,
            'topicName': topic_name,
            'labelFilterAction': 'include'
        }

        # 3. watch実行
        response = srv.users().watch(userId='me', body=request).execute()
        
        logger.info(f"✅ Watch設定が完了しました！ History ID: {response.get('historyId')}")
        logger.info(f"有効期限: {response.get('expiration', '不明')} (約7日間)")
        
    except Exception as e:
        logger.error(f"Watch設定中にエラーが発生しました: {e}")

if __name__ == '__main__':
    setup_watch()
