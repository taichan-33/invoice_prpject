import os
import shutil
import asyncio
from unittest.mock import MagicMock, patch
from fastapi import BackgroundTasks

# 1. Set environment to LOCAL before importing main
os.environ["APP_ENV"] = "local"
os.environ["ALLOWED_DOMAINS"] = "trustworthy.com"
os.environ["SUBJECT_KEYWORDS"] = "Invoice,請求書"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

# 2. Mock Google things (Gmail only!)
# We do NOT mock storage/bigquery because we want to test Local Adapters
import sys
sys.modules['google'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
# Mock default auth to return a tuple (creds, project_id)
sys.modules['google.auth'].default.return_value = (MagicMock(), 'test-project')

# 3. Import main
import main
from main import receive_gmail_notification, PubSubBody, PubSubMessage

async def run_local_emulation_test():
    print("Running LOCAL EMULATION test...")
    
    # Cleanup previous run
    if os.path.exists("local_storage"):
        shutil.rmtree("local_storage")
    if os.path.exists("local_bq_log.jsonl"):
        os.remove("local_bq_log.jsonl")

    # Setup Mock Gmail Service
    mock_service = MagicMock()
    
    # Mock list/modify (Claim Check)
    mock_messages = mock_service.users.return_value.messages.return_value
    mock_messages.list.return_value.execute.return_value = {
        'messages': [{'id': 'msg_valid', 'threadId': 'th1'}]
    }
    mock_messages.modify.return_value.execute.return_value = {'id': 'msg_valid'}
    
    # Mock Email Content (Valid Case)
    mock_messages.get.return_value.execute.return_value = {
        'id': 'msg_valid',
        'internalDate': '1672531200000', # 2023-01-01
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Monthly Invoice'},
                {'name': 'From', 'value': 'accounting@trustworthy.com'}
            ],
            'parts': [
                {
                    'filename': 'invoice.pdf',
                    'body': {'attachmentId': 'att1'},
                    'mimeType': 'application/pdf'
                }
            ]
        }
    }
    mock_messages.attachments.return_value.get.return_value.execute.return_value = {
        'data': 'REVNTyBQREY=' # "DEMO PDF"
    }

    # Patch get_gmail_service in both locking and processor paths
    with patch('services.gmail.get_gmail_service', return_value=mock_service):
        
        # --- TEST 1: Valid Email ---
        print("\n--- Testing Valid Email ---")
        bg_tasks = BackgroundTasks()
        body = PubSubBody(
            message=PubSubMessage(data="...", messageId="pubsub1"),
            subscription="sub1"
        )
        resp = await receive_gmail_notification(body, bg_tasks)
        print(f"Response: {resp}")
        
        # Run background task
        for task in bg_tasks.tasks:
            await task()
            
        # Verify File Existence
        expected_file = "local_storage/invoice-archive-test-project/2023/01/01/msg_valid_invoice.pdf"
        if os.path.exists(expected_file):
            print(f"SUCCESS: File created at {expected_file}")
            with open(expected_file, 'rb') as f:
                print(f"Content: {f.read()}")
        else:
            print(f"FAILURE: File not found at {expected_file}")
            
        # Verify BQ Log
        if os.path.exists("local_bq_log.jsonl"):
            print("SUCCESS: BQ log file created.")
            with open("local_bq_log.jsonl") as f:
                print(f"Log content: {f.read().strip()}")
        else:
            print("FAILURE: BQ log file not found.")

        # --- TEST 2: Filtered Email (Invalid Domain) ---
        print("\n--- Testing Filtered Email (Invalid Domain) ---")
        # Change mock return to invalid sender
        mock_messages.list.return_value.execute.return_value = {'messages': [{'id': 'msg_spam'}]}
        mock_messages.get.return_value.execute.side_effect = None # adjust side effect if needed
        mock_messages.get.return_value.execute.return_value = {
            'id': 'msg_spam',
            'internalDate': '1672531200000', 
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Invoice'},
                    {'name': 'From', 'value': 'spammer@evil.com'} # Not in allowed list
                ]
            }
        }
        
        bg_tasks = BackgroundTasks()
        await receive_gmail_notification(body, bg_tasks) # logic runs, claim check passes
        
        # Run processing
        for task in bg_tasks.tasks:
            await task()
            
        # Check logs (manually verify console or check absence of file)
        # Note: In real test we'd capture logs. Here we trust the previous success and console output.
        print("Test 2 Completed (Check console for 'Skipping message... blocked by filter policy')")

if __name__ == "__main__":
    asyncio.run(run_local_emulation_test())
