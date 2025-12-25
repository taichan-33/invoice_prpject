import base64
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from services.locking import lock_and_get_messages
from services.processor import process_email_task
import services.gmail
import config

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class PubSubMessage(BaseModel):
    data: str | None = None
    messageId: str

class PubSubBody(BaseModel):
    message: PubSubMessage
    subscription: str

@app.post("/")
async def receive_gmail_notification(body: PubSubBody, background_tasks: BackgroundTasks):
    logger.info(f"★通知を受信しました! Pub/Sub MessageID: {body.message.messageId}")

    # Decode data for logging
    if body.message.data:
        try:
            decoded_data = base64.b64decode(body.message.data).decode("utf-8")
            logger.info(f"★データ内容: {decoded_data}")
        except Exception as e:
            logger.warning(f"データのデコードに失敗しました: {e}")

    # 1. Claim Check (Lock)
    locked_msgs = lock_and_get_messages()
    
    if not locked_msgs:
        logger.info("未読のメッセージは見つかりませんでした。")
        return {"status": "ok"}

    # 2. Process (Background)
    for msg in locked_msgs:
        background_tasks.add_task(process_email_task, msg)

    return {"status": "ok", "locked_count": len(locked_msgs)}

@app.post("/refresh-watch")
async def refresh_watch_subscription():
    """
    Cloud Scheduler から毎日叩かれるエンドポイント。
    Gmail の Watch 設定（有効期限7日）を更新します。
    """
    logger.info("Gmail Watch設定の更新を開始します...")
    try:
        srv = services.gmail.get_gmail_service()
        
        # TARGETラベル (ID) の通知のみを受け取る設定
        # 注意: 本番環境では config.TARGET_LABEL に 'Label_...' 形式のIDが入っていることを期待します
        label_ids = [config.TARGET_LABEL] if config.TARGET_LABEL and config.TARGET_LABEL != "TARGET" else ['UNREAD']
        
        topic_name = f'projects/{config.PROJECT_ID}/topics/gmail-notification'
        
        request = {
            'labelIds': label_ids,
            'topicName': topic_name,
            'labelFilterAction': 'include'
        }
        
        response = srv.users().watch(userId='me', body=request).execute()
        logger.info(f"Gmail Watch設定を更新しました。History ID: {response.get('historyId')}")
        return {"status": "ok", "historyId": response.get("historyId")}
        
    except Exception as e:
        logger.error(f"Gmail Watch設定の更新に失敗しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Local dev
    uvicorn.run(app, host="0.0.0.0", port=8080)