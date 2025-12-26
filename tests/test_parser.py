import pytest
from services.parser import parse_message_detail

def test_parse_sender_with_name():
    """送信者名とアドレスが含まれる場合のパーステスト"""
    msg_detail = {
        'id': 'msg1',
        'internalDate': '1678886400000', # 2023-03-15 12:00:00 UTC (roughly)
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Invoice'},
                {'name': 'From', 'value': 'Amazon <info@amazon.co.jp>'}
            ]
        }
    }
    email = parse_message_detail(msg_detail)
    assert email.sender_name == 'Amazon'
    assert email.sender_address == 'info@amazon.co.jp'

def test_parse_sender_address_only():
    """アドレスのみの場合のパーステスト"""
    msg_detail = {
        'id': 'msg2',
        'internalDate': '1678886400000',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'no-reply@google.com'}
            ]
        }
    }
    email = parse_message_detail(msg_detail)
    # 名前がない場合はアドレスが名前になる仕様
    assert email.sender_name == 'no-reply@google.com'
    assert email.sender_address == 'no-reply@google.com'

def test_parse_attachments():
    """添付ファイル抽出のテスト"""
    msg_detail = {
        'id': 'msg3',
        'internalDate': '1678886400000',
        'payload': {
            'headers': [{'name': 'From', 'value': 'test@example.com'}],
            'parts': [
                {
                    'filename': '',
                    'body': {'size': 100},
                    'mimeType': 'text/plain'
                },
                {
                    'filename': 'invoice.pdf',
                    'body': {'attachmentId': 'att1', 'size': 5000},
                    'mimeType': 'application/pdf'
                }
            ]
        }
    }
    email = parse_message_detail(msg_detail)
    assert len(email.attachments) == 1
    assert email.attachments[0].filename == 'invoice.pdf'
    assert email.attachments[0].size == 5000
    assert email.attachments[0].mime_type == 'application/pdf'
