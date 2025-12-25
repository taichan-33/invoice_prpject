import logging
from typing import List, Dict, Any
import services.gmail
import config

logger = logging.getLogger(__name__)

def lock_and_get_messages() -> List[Dict[str, Any]]:
    """
    【Claim Check パターン】の実装 (Label版):
    
    1. 検索: 「TARGET」ラベルがあり、かつ「PROCESSED」ラベルが無いメールを探します。
       (未読/既読は気にしません)
    2. ロック: 見つかったメールに「PROCESSED」ラベルを付与します。
    3. 返却: ラベル付与に成功したメールを返します。
    
    Returns:
        List[Dict]: 処理対象となるメールのリスト
    """
    locked_messages = []
    
    try:
        srv = services.gmail.get_gmail_service()
        
        # 処理済みラベルのIDを取得（なければ作る）
        processed_label_id = services.gmail.get_or_create_label_id(config.PROCESSED_LABEL_NAME)
        
        # 1. 検索 (Claim Check)
        # TARGETラベルがあり、かつ「処理済み」でも「エラー」でもないメールを検索
        query = f"label:{config.TARGET_LABEL} -label:{config.PROCESSED_LABEL_NAME} -label:{config.ERROR_LABEL_NAME}"
        
        results = srv.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []

        # --- 2. ロック (Lock) ---
        for msg in messages:
            msg_id = msg['id']
            try:
                # 処理済みラベル(PROCESSED)を付与することで「ロック」とする
                # ついでに未読(UNREAD)も外してあげる（親切心）
                srv.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={
                        'addLabelIds': [processed_label_id],
                        'removeLabelIds': ['UNREAD']
                    }
                ).execute()
                
                logger.info(f"メッセージをロック(処理済ラベル付与)しました: {msg_id}")
                locked_messages.append(msg)
                
            except Exception as e:
                # 競合などで失敗した場合はスキップ
                logger.warning(f"メッセージ {msg_id} のロックに失敗しました: {e}")
                continue
                
    except Exception as e:
        logger.error(f"lock_and_get_messages でエラーが発生しました: {e}")
        
    return locked_messages
