import pytest
from unittest.mock import MagicMock
from services.processor import process_email_task
from services.parser import Email, Attachment
import datetime

@pytest.fixture
def mock_config(monkeypatch):
    """機密情報をモック"""
    import config
    import services.filtering
    import importlib
    
    # Patch config
    monkeypatch.setattr(config, "ALLOWED_DOMAINS", ["example.com", "trusted.org"])
    monkeypatch.setattr(config, "SUBJECT_KEYWORDS", ["invoice", "bill", "請求書"])
    
    # Reload services.filtering to ensure it consumes new config if it did 'from config import ...'
    # Although code uses 'import config', reloading is safer if test runner cached old state.
    importlib.reload(services.filtering)

@pytest.fixture
def mock_dependencies(mocker):
    """依存関係のモックを一括設定"""
    # Gmail Service
    mock_service = MagicMock()
    mocker.patch("services.gmail.get_gmail_service", return_value=mock_service)
    
    # Adapters (Storage/BQ)
    mock_storage = MagicMock()
    mock_storage.save_file.return_value = "https://mock-storage-url"
    
    mock_bq = MagicMock()
    mock_bq.insert_rows.return_value = []
    
    mocker.patch("adapters.get_storage_adapter", return_value=mock_storage)
    mocker.patch("adapters.get_bigquery_adapter", return_value=mock_bq)
    
    # Filter (allow all)
    mocker.patch("services.processor.is_allowed_email", return_value=True)
    
    # Error Monitor
    mocker.patch("services.error_monitor.record_success")
    mocker.patch("services.error_monitor.record_error")
    
    return {
        "service": mock_service,
        "storage": mock_storage,
        "bq": mock_bq
    }

def test_process_email_task_success(mock_dependencies, mocker):
    """正常系のテスト: パース -> アップロード -> BQ記録"""
    service = mock_dependencies['service']
    storage = mock_dependencies['storage']
    bq = mock_dependencies['bq']
    
    # 1. メッセージ詳細のモック (parserが処理するデータ)
    msg_id = "msg123"
    # parser自体は本物を使うかモックするかだが、ここではparserの結果をモックする方が楽
    # services.parser.parse_message_detail をモック
    mock_email = Email(
        id=msg_id,
        subject="Invoice",
        sender_name="Amazon",
        sender_address="info@amazon.com",
        received_at=datetime.datetime.now(),
        attachments=[
            Attachment(id="att1", filename="invoice.pdf", mime_type="application/pdf", size=1024)
        ]
    )
    mocker.patch("services.parser.parse_message_detail", return_value=mock_email)
    
    # Mock `get().execute()` for message metadata (labels)
    # This must return a dict with 'id' and 'labelIds' to trigger label logic
    service.users().messages().get().execute.return_value = {
        'id': 'msg123', 
        'labelIds': ['TARGET'] # config.TARGET_LABEL default is TARGET
    }
    
    # 2. 添付ファイルダウンロードのモック
    service.users().messages().attachments().get().execute.return_value = {'data': 'VGhpcyBpcyBhIHRlc3Q='} # "This is a test" in base64

    # 実行
    # 実行
    process_email_task({'id': msg_id})
    
    # 検証
    # Storageに保存されたか
    assert storage.save_file.call_count == 1
    args, kwargs = storage.save_file.call_args
    file_path = kwargs.get('file_path')
    # Updated to expect NO index for single file
    assert file_path is not None and file_path.endswith("msg123_invoice.pdf") # path check
    
    # BigQueryに挿入されたか
    assert bq.insert_rows.call_count == 1
    args, _ = bq.insert_rows.call_args
    row = args[1][0]
    assert row['message_id'] == msg_id
    assert row['sender_name'] == "Amazon"
    
    # ラベル変更 (PROCESSED付与、TARGET削除)
    # The modify method return value's execute method should be called.
    # Check that modify was called with correct args
    # modify is called on the result of messages(), so service.users().messages.return_value.modify
    service.users().messages.return_value.modify.assert_called_once()
    
def test_process_email_multiple_attachments(mock_dependencies, mocker):
    """複数添付ファイルのテスト (ファイル名重複なし)"""
    service = mock_dependencies['service']
    storage = mock_dependencies['storage']
    bq = mock_dependencies['bq']
    
    # 1. 2つの添付ファイルを持つメール
    msg_id = "msg_multi"
    mock_email = Email(
        id=msg_id, # Correct field name
        received_at=datetime.datetime(2023, 1, 1, 10, 0, 0),
        sender_name="Amazon",
        sender_address="no-reply@amazon.com",
        subject="Invoice and Receipt",
        # body="Attached files.", # Removed unexpected arg
        attachments=[
            Attachment(id="att1", filename="invoice.pdf", mime_type="application/pdf", size=100),
            Attachment(id="att2", filename="receipt.jpg", mime_type="image/jpeg", size=200)
        ]
    )
    mocker.patch("services.parser.parse_message_detail", return_value=mock_email)
    
    # Mock label logic
    service.users().messages().get().execute.return_value = {'id': msg_id, 'labelIds': ['TARGET']}
    # Mock attachment content (same for both for simplicity)
    service.users().messages().attachments().get().execute.return_value = {'data': 'VGhpcyBpcyBhIHRlc3Q='}

    # Execute
    process_email_task({'id': msg_id})
    
    # Verify
    assert storage.save_file.call_count == 2
    assert bq.insert_rows.call_count == 2
    
def test_process_email_duplicate_filenames(mock_dependencies, mocker):
    """ファイル名重複時のテスト (上書きリスクの確認)"""
    service = mock_dependencies['service']
    storage = mock_dependencies['storage']
    bq = mock_dependencies['bq']
    
    msg_id = "msg_dup"
    mock_email = Email(
        id=msg_id, # Correct field name
        received_at=datetime.datetime(2023, 1, 1, 10, 0, 0),
        sender_name="Amazon",
        sender_address="no-reply@amazon.com",
        subject="Duplicate Files",
        # body="Check these.", # Removed unexpected arg
        attachments=[
            Attachment(id="att1", filename="data.pdf", mime_type="application/pdf", size=100),
            Attachment(id="att2", filename="data.pdf", mime_type="application/pdf", size=200) # Same name
        ]
    )
    mocker.patch("services.parser.parse_message_detail", return_value=mock_email)
    service.users().messages().get().execute.return_value = {'id': msg_id, 'labelIds': ['TARGET']}
    service.users().messages().attachments().get().execute.return_value = {'data': 'VGhpcyBpcyBhIHRlc3Q='}

    # Execute
    process_email_task({'id': msg_id})
    
    # Verify - Under current logic, save_file is called twice with SAME path
    assert storage.save_file.call_count == 2
    
    # Check paths
    calls = storage.save_file.call_args_list
    path1 = calls[0].kwargs.get('file_path') or calls[0].args[1] if len(calls[0].args)>1 else calls[0].kwargs['file_path']
    path2 = calls[1].kwargs.get('file_path') or calls[1].args[1] if len(calls[1].args)>1 else calls[1].kwargs['file_path']
    
    # Paths should be unique now (e.g. msg_dup_1_data.pdf and msg_dup_2_data.pdf)
    assert path1 != path2
    assert "_1_" in path1
    assert "_2_" in path2
    
def test_process_email_skip_denied_sender(mock_dependencies, mocker):
    """不許可送信者のスキップテスト"""
    # フィルターがFalseを返すように変更
    mocker.patch("services.processor.is_allowed_email", return_value=False)
    
    # ダミーのEmailオブジェクト
    mocker.patch("services.parser.parse_message_detail", return_value=Email(
        id="msg1", subject="Spam", sender_name="Spam", sender_address="spam@evil.com",
        received_at=datetime.datetime.now(), attachments=[]
    ))
    
    process_email_task({'id': 'msg1'})
    
    # 何も保存されないはず
    mock_dependencies['storage'].save_file.assert_not_called()
    mock_dependencies['bq'].insert_rows.assert_not_called()

def test_process_email_no_attachments(mock_dependencies, mocker):
    """添付ファイルなしのスキップテスト"""
    mocker.patch("services.parser.parse_message_detail", return_value=Email(
        id="msg1", subject="No Att", sender_name="Me", sender_address="me@test.com",
        received_at=datetime.datetime.now(), attachments=[] # 空
    ))
    
    process_email_task({'id': 'msg1'})
    
    mock_dependencies['storage'].save_file.assert_not_called()

def test_process_email_error_handling(mock_dependencies, mocker):
    """処理失敗時のエラーラベル付与テスト"""
    service = mock_dependencies['service']
    storage = mock_dependencies['storage']
    
    # 1. 正常なEmailオブジェクトを準備
    msg_id = "msg_error"
    mock_email = Email(
        id=msg_id,
        received_at=datetime.datetime(2023, 1, 1, 10, 0, 0),
        sender_name="Amazon",
        sender_address="no-reply@amazon.com",
        subject="Invoice",
        attachments=[
            Attachment(id="att1", filename="invoice.pdf", mime_type="application/pdf", size=100)
        ]
    )
    mocker.patch("services.parser.parse_message_detail", return_value=mock_email)
    
    # 2. Gmail APIのラベル情報をモック
    service.users().messages().get().execute.return_value = {'id': msg_id, 'labelIds': ['TARGET']}
    service.users().messages().attachments().get().execute.return_value = {'data': 'VGhpcyBpcyBhIHRlc3Q='}
    
    # 3. Storage の save_file で例外を発生させる
    storage.save_file.side_effect = Exception("Simulated GCS Error")
    
    # 4. 実行 (例外が発生するが、catch されるはず)
    process_email_task({'id': msg_id})
    
    # 5. エラー記録が呼ばれたか
    import services.error_monitor
    services.error_monitor.record_error.assert_called_once()
    
    # 6. ラベル変更 (ERROR_LABEL への変更) が呼ばれたか
    # modify は例外後のエラーハンドリングで呼ばれる
    service.users().messages.return_value.modify.assert_called()
