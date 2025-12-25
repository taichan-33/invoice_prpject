import base64
import datetime
import logging
from typing import List, Optional, Dict, Any

import services.gmail
from services.filtering import is_allowed_email
import adapters
import config

# ロガー設定
logger = logging.getLogger(__name__)

def find_attachments(parts_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MIMEパーツの中から添付ファイルを再帰的に検索してリストアップします。
    """
    found_attachments = []
    for part in parts_list:
        # ファイル名があり、かつ attachmentId があれば添付ファイルとみなす
        if part.get('filename') and part.get('body', {}).get('attachmentId'):
            found_attachments.append(part)
        
        # ネストされたマルチパート（multipart/mixedなど）の場合、さらに中を探索
        if 'parts' in part:
            found_attachments.extend(find_attachments(part['parts']))
            
    return found_attachments

def get_header_value(headers: List[Dict[str, str]], name: str, default: str = "") -> str:
    """
    ヘッダーリストから指定した名前の値を取得します。
    見つからない場合は default 値を返します。
    
    例: headers=[{'name': 'Subject', 'value': '件名'}] -> '件名'
    """
    for header in headers:
        if header.get('name') == name:
            return header.get('value', default)
    return default

def parse_gmail_date(internal_date_ms: str) -> datetime.datetime:
    """
    Gmailの internalDate (ミリ秒文字列) を Python の datetime オブジェクトに変換します。
    """
    try:
        # 文字列を数値に変換し、ミリ秒なので1000で割って秒にする
        timestamp_sec = int(internal_date_ms) / 1000
        return datetime.datetime.fromtimestamp(timestamp_sec)
    except (ValueError, TypeError):
        # 万が一変換に失敗した場合は現在時刻を返す（あるいはエラーにする）
        logger.warning(f"日付の変換に失敗しました: {internal_date_ms}。現在時刻を使用します。")
        return datetime.datetime.now()

def process_email_task(message_data: dict):
    """
    1通のメール処理フローを実行します。
    1. 詳細取得 & パース
    2. 安全性フィルタリング
    3. 添付ファイルのアップロード (GCS)
    4. 処理結果の記録 (BigQuery)
    """
    msg_id = message_data.get('id')
    logger.info(f"メッセージを処理中: {msg_id}")
    
    try:
        srv = services.gmail.get_gmail_service()
        
        # --- 1. メール詳細の取得 ---
        # format='full' で本文やヘッダーを含む全データを取得
        msg_detail = srv.users().messages().get(userId='me', id=msg_id, format='full').execute()
        
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        # ヘッダー情報の抽出 (ヘルパー関数を使用)
        subject = get_header_value(headers, 'Subject', '(件名なし)')
        sender = get_header_value(headers, 'From', '(送信元不明)')
        
        # --- 2. 安全性フィルタリング ---
        # 許可されていない送信者や件名の場合はスキップ
        if not is_allowed_email(sender, subject):
            logger.info(f"メッセージ {msg_id} をスキップ: フィルターポリシーによりブロックされました。")
            return

        # 受信日時のパース (ヘルパー関数を使用)
        # internalDate は API から返される「受信した瞬間のタイムスタンプ」
        received_at = parse_gmail_date(msg_detail.get('internalDate', '0'))
        
        # --- 3. 添付ファイルの抽出 ---
        found_attachments = find_attachments([payload])
        
        if not found_attachments:
            logger.info(f"メッセージ {msg_id} に添付ファイルが見つかりません")
            return

        # --- 4. アダプターの準備 (保存先などの設定) ---
        storage_adapter = adapters.get_storage_adapter()
        bq_adapter = adapters.get_bigquery_adapter()
        bucket_name = config.BUCKET_NAME_TEMPLATE.format(config.PROJECT_ID)

        # --- 5. 文書の保存 & ログ記録 ---
        for part in found_attachments:
            filename = part['filename']
            attachment_id = part['body']['attachmentId']
            
            # 添付ファイルの実データをダウンロード
            att = srv.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=attachment_id
            ).execute()
            
            # Base64デコードしてバイナリデータに戻す
            file_data = base64.urlsafe_b64decode(att['data'].encode('UTF-8'))
            
            # GCS (またはローカル) へアップロード
            # 保存パス形式: YYYY/MM/DD/メッセージID_ファイル名
            blob_path = f"{received_at.strftime('%Y/%m/%d')}/{msg_id}_{filename}"
            
            gcs_url = storage_adapter.save_file(
                bucket_name=bucket_name,
                file_path=blob_path,
                data=file_data,
                content_type=part.get('mimeType')
            )
            logger.info(f"Storage にアップロードしました: {gcs_url}")
            
            # BigQuery (またはローカルログ) へ記録
            row = {
                "message_id": msg_id,
                "received_at": received_at.isoformat(),
                "sender_address": sender,
                "subject": subject,
                "filename": filename,
                "gcs_url": gcs_url,
                "gcs_path": f"gs://{bucket_name}/{blob_path}",
                "processed_at": datetime.datetime.now().isoformat()
            }
            
            # 重複挿入の防止キー (メッセージID + ファイル名)
            insert_id = f"{msg_id}_{filename}"
            errors = bq_adapter.insert_rows(config.BQ_TABLE_ID, [row], row_ids=[insert_id])
            
            if errors:
                logger.error(f"BigQuery への挿入エラー: {errors}")
            else:
                logger.info(f"BigQuery に挿入しました: {insert_id}")

    except Exception as e:
        logger.error(f"メッセージ {msg_id} の処理中にエラーが発生しました: {e}")
    
    logger.info(f"メッセージの処理が完了しました: {msg_id}")
