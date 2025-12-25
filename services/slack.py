"""
Slack通知ユーティリティ
システムアラートや日次レポートの送信に使用
"""
import requests
import logging
import config

logger = logging.getLogger(__name__)

def send_slack_alert(message: str, level: str = "info") -> bool:
    """
    Slackにアラートを送信する。
    
    Args:
        message: 送信するメッセージ
        level: "info", "warning", "error" のいずれか
    
    Returns:
        送信成功ならTrue
    """
    if not config.SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL が設定されていないため、アラート送信をスキップします。")
        return False
    
    # レベルに応じた絵文字
    emoji_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "🚨",
        "success": "✅"
    }
    emoji = emoji_map.get(level, "📢")
    
    text = f"{emoji} *[Invoice System Alert]*\n{message}"
    
    try:
        response = requests.post(config.SLACK_WEBHOOK_URL, json={"text": text})
        if response.status_code == 200:
            logger.info(f"Slackアラートを送信しました: {level}")
            return True
        else:
            logger.error(f"Slackアラート送信失敗 (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        logger.error(f"Slackアラート送信例外: {e}")
        return False
