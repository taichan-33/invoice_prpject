import email.utils
import base64
import datetime
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Attachment:
    id: str
    filename: str
    mime_type: str
    size: int
    data_base64: Optional[str] = None 

@dataclass
class Email:
    id: str
    subject: str
    sender_name: str
    sender_address: str
    received_at: datetime.datetime
    attachments: List[Attachment]

def _get_header_value(headers: List[Dict[str, str]], name: str, default: str = "") -> str:
    """ヘッダーリストから指定した名前の値を取得します。"""
    for header in headers:
        if header.get('name') == name:
            return header.get('value', default)
    return default

def _parse_gmail_date(internal_date_ms: str) -> datetime.datetime:
    """Gmailの internalDate (ミリ秒文字列) を datetime に変換します。"""
    try:
        timestamp_sec = int(internal_date_ms) / 1000
        return datetime.datetime.fromtimestamp(timestamp_sec)
    except (ValueError, TypeError):
        logger.warning(f"日付変換失敗: {internal_date_ms}。現在時刻を使用します。")
        return datetime.datetime.now()

def _find_attachments_recursive(parts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """MIMEパーツから添付ファイルを再帰的に検索します。"""
    found = []
    for part in parts_list:
        if part.get('filename') and part.get('body', {}).get('attachmentId'):
            found.append(part)
        
        if 'parts' in part:
            found.extend(_find_attachments_recursive(part['parts']))
    return found

def parse_message_detail(msg_detail: Dict[str, Any]) -> Email:
    """
    Gmail API のメッセージ詳細JSONを解析し、扱いやすい Email オブジェクトに変換します。
    """
    msg_id = msg_detail.get('id')
    payload = msg_detail.get('payload', {})
    headers = payload.get('headers', [])
    
    # 基本情報の抽出
    subject = _get_header_value(headers, 'Subject', '(件名なし)')
    
    # 送信者情報のパース (From: "Amazon <info@amazon.co.jp>" -> name="Amazon", addr="info@amazon.co.jp")
    raw_sender = _get_header_value(headers, 'From', '(送信元不明)')
    sender_name, sender_address = email.utils.parseaddr(raw_sender)
    
    # 名前が空の場合はアドレスを名前にする (検索のため)
    if not sender_name:
        sender_name = sender_address

    received_at = _parse_gmail_date(msg_detail.get('internalDate', '0'))
    
    # 添付ファイルの抽出
    raw_attachments = _find_attachments_recursive([payload])
    attachments = []
    
    for att in raw_attachments:
        attachments.append(Attachment(
            id=att['body']['attachmentId'],
            filename=att['filename'],
            mime_type=att.get('mimeType', 'application/octet-stream'),
            size=att['body'].get('size', 0)
        ))
        
    return Email(
        id=msg_id,
        subject=subject,
        sender_name=sender_name,
        sender_address=sender_address,
        received_at=received_at,
        attachments=attachments
    )
