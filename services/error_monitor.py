"""
エラー監視モジュール
閾値ベースのアラートシステム

- 通常時: 日次レポートのみ
- 異常時: エラー率が閾値を超えたら即座にSlack通知（ただし1回だけ）
"""
import time
import logging
import threading
import config

logger = logging.getLogger(__name__)

# --- 設定値 ---
ERROR_RATE_THRESHOLD = 0.05  # 5%を超えたらアラート
CHECK_WINDOW_SECONDS = 3600  # 1時間のウィンドウ
ALERT_COOLDOWN_SECONDS = 3600  # アラート後1時間はクールダウン

# --- 内部状態 ---
_lock = threading.Lock()
_processed_count = 0
_error_count = 0
_window_start_time = time.time()
_last_alert_time = 0

def record_success():
    """処理成功を記録"""
    global _processed_count
    with _lock:
        _maybe_reset_window()
        _processed_count += 1

def record_error():
    """
    処理エラーを記録し、必要に応じてアラートを送信
    """
    global _error_count
    with _lock:
        _maybe_reset_window()
        _error_count += 1
        _check_and_alert()

def _maybe_reset_window():
    """ウィンドウ期間が過ぎていたらカウンターをリセット"""
    global _processed_count, _error_count, _window_start_time
    now = time.time()
    if now - _window_start_time > CHECK_WINDOW_SECONDS:
        logger.debug(f"ウィンドウリセット: 処理={_processed_count}, エラー={_error_count}")
        _processed_count = 0
        _error_count = 0
        _window_start_time = now

def _check_and_alert():
    """エラー率をチェックし、必要ならアラートを送信"""
    global _last_alert_time
    
    # 最低限の処理件数がないと率を計算しても意味がない
    total = _processed_count + _error_count
    if total < 10:
        return
    
    error_rate = _error_count / total
    
    # 閾値を超えているか
    if error_rate < ERROR_RATE_THRESHOLD:
        return
    
    # クールダウン中か
    now = time.time()
    if now - _last_alert_time < ALERT_COOLDOWN_SECONDS:
        return
    
    # アラート送信
    _last_alert_time = now
    _send_threshold_alert(error_rate, _error_count, total)

def _send_threshold_alert(error_rate: float, error_count: int, total: int):
    """閾値超過アラートを送信"""
    try:
        import services.slack
        
        alert_msg = f"""*⚠️ エラー率異常検知*

直近1時間の統計:
• 処理件数: {total} 件
• エラー件数: {error_count} 件
• エラー率: *{error_rate:.1%}* (閾値: {ERROR_RATE_THRESHOLD:.0%})

*システム障害の可能性があります。Cloud Loggingを確認してください。*

<https://console.cloud.google.com/logs/query?project={config.PROJECT_ID}|🔗 Cloud Loggingを開く>
<https://mail.google.com/mail/u/0/#search/label%3A{config.ERROR_LABEL_NAME}|🔗 Gmailでエラーを確認>"""
        
        services.slack.send_slack_alert(alert_msg, level="error")
        logger.warning(f"閾値アラートを送信しました: エラー率 {error_rate:.1%}")
        
    except Exception as e:
        logger.error(f"閾値アラートの送信に失敗: {e}")

def get_current_stats() -> dict:
    """現在のウィンドウ統計を取得（デバッグ用）"""
    with _lock:
        total = _processed_count + _error_count
        return {
            "processed": _processed_count,
            "errors": _error_count,
            "total": total,
            "error_rate": _error_count / total if total > 0 else 0,
            "window_age_seconds": time.time() - _window_start_time
        }
