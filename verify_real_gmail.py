import os
import asyncio
import logging
from unittest.mock import MagicMock
# Note: We do NOT mock google.auth/googleapiclient here because we want REAL Gmail access.

# 1. Set environment to LOCAL
# This forces the app to use LocalStorageAdapter and LocalBigQueryAdapter
os.environ["APP_ENV"] = "local"

# 2. Configure Filters (Set these to match your test email)
os.environ["ALLOWED_DOMAINS"] = "" # Empty = Allow all (for testing)
os.environ["SUBJECT_KEYWORDS"] = "" # Empty = Allow all (for testing)

# 3. Import main
import main
from main import receive_gmail_notification, PubSubBody, PubSubMessage
from fastapi import BackgroundTasks

# Logging setup
logging.basicConfig(level=logging.INFO)

async def run_real_gmail_verification():
    print("!!! 警告: このスクリプトは実際の Gmail API に接続します !!!")
    print("前提条件: .env に OAuth 認証情報を設定するか、'gcloud auth application-default login' を実行済みである必要があります")
    print("----------------------------------------------------------------")
    
    # Simulate a Pub/Sub trigger
    # The data doesn't strictly matter because our Claim Check logic ignores the ID in the notification 
    # and goes to fetch 'label:TARGET is:unread' directly.
    # HOWEVER, you must have an unread email with label 'TARGET' in your inbox.
    
    body = PubSubBody(
        message=PubSubMessage(data="e30=", messageId="trigger_1"), # {} base64
        subscription="projects/my-project/subscriptions/my-sub"
    )
    
    bg_tasks = BackgroundTasks()
    
    print(">>> Cloud Run ロジックをトリガーします...")
    response = await receive_gmail_notification(body, bg_tasks)
    
    print(f">>> Response: {response}")
    
    if response.get('locked_count', 0) > 0:
        print(f">>> {response['locked_count']} 件のメールを処理中...")
        # Execute background tasks
        for task in bg_tasks.tasks:
            await task()
        print(">>> 完了しました。 'local_storage/' フォルダと 'local_bq_log.jsonl' を確認してください。")
    else:
        print(">>> メール処理なし。 ('TARGET' ラベルが付いた未読メールはありましたか？)")

if __name__ == "__main__":
    asyncio.run(run_real_gmail_verification())
