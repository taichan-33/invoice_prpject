import logging
from typing import List, Dict, Any
import services.gmail
import config

logger = logging.getLogger(__name__)

def lock_and_get_messages() -> List[Dict[str, Any]]:
    """
    【Claim Check パターン】の実装:
    
    1. 検索: 「TARGET」ラベルかつ「未読」のメールを探します。
    2. ロック: 見つかったメールから「未読」ラベルを外します（これで他プロセスからは見えなくなります）。
    3. 返却: ロックに成功したメールだけをリストとして返します。
    
    Returns:
        List[Dict]: 処理対象となるメールのリスト(Gmail APIのメッセージオブジェクト)
    """
    locked_messages = []
    
    try:
        srv = services.gmail.get_gmail_service()
        
        # --- 1. 検索 (Search) ---
        # 自分(me)のメールボックスから、指定ラベル & 未読 のものを探す
        results = srv.users().messages().list(
            userId='me',
            labelIds=[config.TARGET_LABEL, 'UNREAD'],
            maxResults=10 # 一度に処理する最大件数
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []

        # --- 2. ロック (Lock) ---
        for msg in messages:
            msg_id = msg['id']
            try:
                # 未読ラベル(UNREAD)を外すことで「処理中」または「処理済み」状態にする
                srv.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                
                logger.info(f"メッセージをロックしました: {msg_id}")
                locked_messages.append(msg)
                
            except Exception as e:
                # 競合などでロック失敗（既に誰かが処理したなど）の場合はスキップ
                logger.warning(f"メッセージ {msg_id} のロックに失敗しました: {e}")
                continue
                
    except Exception as e:
        logger.error(f"lock_and_get_messages でエラーが発生しました: {e}")
        
    return locked_messages
