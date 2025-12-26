import base64
import datetime
import logging
import os
from typing import List, Optional, Dict, Any

import services.gmail
import services.parser
import services.error_monitor
from services.filtering import is_allowed_email
import adapters
import config

# ロガー設定
logger = logging.getLogger(__name__)

def process_email_task(message_data: dict):
    """
    1通のメール処理フローを実行します。
    1. 詳細取得 & パース (services.parser)
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
        
        # ★ パース処理を parser.py に委譲 ★
        email = services.parser.parse_message_detail(msg_detail)
        
        # --- 2. 安全性フィルタリング ---
        # 許可されていない送信者や件名の場合はスキップ
        if not is_allowed_email(email.sender_address, email.subject):
            logger.info(f"メッセージ {msg_id} をスキップ: フィルターポリシーによりブロックされました。")
            return
        
        # --- 3. 添付ファイルの有無チェック ---
        if not email.attachments:
            logger.info(f"メッセージ {msg_id} に添付ファイルが見つかりません")
            return

        # --- 4. アダプターの準備 ---
        storage_adapter = adapters.get_storage_adapter()
        bq_adapter = adapters.get_bigquery_adapter()
        bucket_name = config.BUCKET_NAME_TEMPLATE.format(config.PROJECT_ID)

        # --- 5. 文書の保存 & ログ記録 ---
        for att in email.attachments:
            # 添付ファイルの実データをダウンロード
            # (Emailオブジェクトにはメタデータしか入っていないため)
            att_data_res = srv.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=att.id
            ).execute()
            
            # Base64デコード
            file_data = base64.urlsafe_b64decode(att_data_res['data'].encode('UTF-8'))
            
            # GCS (またはローカル) へアップロード
            # 保存パス形式: YYYY/MM/DD/メッセージID_ファイル名
            blob_path = f"{email.received_at.strftime('%Y/%m/%d')}/{msg_id}_{att.filename}"
            
            gcs_url = storage_adapter.save_file(
                bucket_name=bucket_name,
                file_path=blob_path,
                data=file_data,
                content_type=att.mime_type
            )
            logger.info(f"Storage にアップロードしました: {gcs_url}")
            
            # BigQuery (またはローカルログ) へ記録
            row = {
                "message_id": msg_id,
                "received_at": email.received_at.isoformat(),
                "sender_name": email.sender_name,           # 送信者名(New)
                "sender_address": email.sender_address,     # アドレス(New)
                "subject": email.subject,
                "filename": att.filename,
                "file_size_bytes": att.size,                # サイズ(New)
                "content_type": att.mime_type,              # MIME(New)
                "extension": os.path.splitext(att.filename)[1].lower(), # 拡張子(New)
                "gcs_url": gcs_url,
                "gcs_path": f"gs://{bucket_name}/{blob_path}",
                "processed_at": datetime.datetime.now().isoformat()
            }
            
            # 重複挿入の防止キー (メッセージID + ファイル名)
            insert_id = f"{msg_id}_{att.filename}"
            errors = bq_adapter.insert_rows(config.BQ_TABLE_ID, [row], row_ids=[insert_id])
            
            if errors:
                logger.error(f"BigQuery への挿入エラー: {errors}")
            else:
                logger.info(f"BigQuery に挿入しました: {insert_id}")
    
        # 成功を記録（閾値監視用）
        services.error_monitor.record_success()

    except Exception as e:
        logger.error(f"メッセージ {msg_id} の処理中にエラーが発生しました: {e}")
        
        # エラーを記録（閾値監視用）
        services.error_monitor.record_error()
        
        # エラー発生時のラベル貼り替え処理
        try:
            # ラベルIDの解決
            processed_label_id = services.gmail.get_or_create_label_id(config.PROCESSED_LABEL_NAME)
            error_label_id = services.gmail.get_or_create_label_id(config.ERROR_LABEL_NAME)
            
            # 処理済みラベルを剥がし、エラーラベルを貼る
            srv.users().messages().modify(
                userId='me',
                id=msg_id,
                body={
                    'removeLabelIds': [processed_label_id],
                    'addLabelIds': [error_label_id]
                }
            ).execute()
            logger.info(f"メッセージ {msg_id} にエラーラベル({config.ERROR_LABEL_NAME})を付与しました。")
            
        except Exception as label_err:
            logger.error(f"エラーラベルの付与にも失敗しました: {label_err}")

    logger.info(f"メッセージの処理が完了しました: {msg_id}")
