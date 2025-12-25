import services.gmail
import config

def debug_query():
    srv = services.gmail.get_gmail_service()
    
    target = config.TARGET_LABEL
    processed = config.PROCESSED_LABEL_NAME
    
    print(f"Target Label (from config): {target}")
    print(f"Processed Label (from config): {processed}")
    
    # Try searching by NAME "TARGET"
    query = "label:TARGET"
    print(f"Generated Query: '{query}'")
    
    print("Executing list()...")
    try:
        results = srv.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        print(f"Found {len(messages)} messages.")
        for msg in messages:
            print(f" - Msg ID: {msg['id']}, Thread ID: {msg['threadId']}")
            
            # Get details to see labels
            detail = srv.users().messages().get(userId='me', id=msg['id']).execute()
            print(f"   Labels: {detail.get('labelIds')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_query()
