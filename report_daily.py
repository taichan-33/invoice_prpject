import os
import datetime
import logging
import adapters
import services.gmail
import services.slack
import config

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_processed_count_yesterday() -> int:
    """昨日の処理成功件数を取得 (Adapter経由)"""
    try:
        bq = adapters.get_bigquery_adapter()
        # 昨日の日付 (YYYY-MM-DD)
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        
        return bq.get_processed_count(yesterday)
    except Exception as e:
        logger.error(f"集計エラー: {e}")
        return -1

def get_error_count_all() -> int:
    """Gmailから現在の未解決エラー件数を取得"""
    try:
        srv = services.gmail.get_gmail_service()
        error_label_id = services.gmail.get_or_create_label_id(config.ERROR_LABEL_NAME)
        
        # エラーラベル付きのメール総数
        results = srv.users().labels().get(userId='me', id=error_label_id).execute()
        return results.get('messagesTotal', 0)
    except Exception as e:
        logger.error(f"Gmail集計エラー: {e}")
        return -1

def send_daily_report():
    """日次レポートを作成してSlackに送信"""
    logger.info("日次レポートの集計を開始します...")
    
    success_count = get_processed_count_yesterday()
    error_count = get_error_count_all()
    
    # メッセージの作成
    today_str = datetime.date.today().isoformat()
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    status_emoji = "🟢" if error_count == 0 else "🔴"
    
    report_text = f"""*📊 Invoice Process Daily Report ({today_str})*
対象期間: {yesterday_str}

{status_emoji} 成功件数: *{success_count if success_count >=0 else '取得失敗'}* 件 (昨日)
🔴 未解決エラー: *{error_count if error_count >=0 else '取得失敗'}* 件 (現在)

<https://mail.google.com/mail/u/0/#search/label%3A{config.ERROR_LABEL_NAME}|🔗 Gmailでエラーを確認>
<https://console.cloud.google.com/logs/query?project={config.PROJECT_ID}|🔗 Cloud Loggingでログを確認>"""

    # 共通モジュールで送信
    level = "success" if error_count == 0 else "warning"
    services.slack.send_slack_alert(report_text, level=level)

if __name__ == "__main__":
    send_daily_report()

