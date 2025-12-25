import time
import logging
from services.locking import lock_and_get_messages
from services.processor import process_email_task

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def watch_gmail():
    print("--- Gmail 監視モードを開始します (Ctrl+C で停止) ---")
    print("60秒ごとに新規メール('TARGET'ラベル & 未処理)をチェックします...")

    try:
        while True:
            # 1. チェック (Claim Check)
            print("\n[チェック中...]")
            locked_msgs = lock_and_get_messages()
            
            if not locked_msgs:
                print(">> 新規メールはありません。")
            else:
                print(f">> {len(locked_msgs)} 件のメールを発見！処理を開始します。")
                
                # 2. 処理 (Process)
                for msg in locked_msgs:
                    process_email_task(msg)
                
                print(">> 全件処理完了。")

            # 60秒待機
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n\n--- 監視を停止しました ---")

if __name__ == "__main__":
    watch_gmail()
