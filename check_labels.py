import services.gmail
import config

def check_labels():
    print("Authenticate and list labels...")
    try:
        srv = services.gmail.get_gmail_service()
        results = srv.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        print(f"\nFound {len(labels)} labels.")
        print("-" * 40)
        target_found = False
        for label in labels:
            # Print System labels only if arguably relevant, usually we skip them to reduce noise
            # but here we show all to be sure.
            if 'TARGET' in label['name']:
                print(f"NAME: {label['name']:<20} | ID: {label['id']}")
                if label['name'] == config.TARGET_LABEL:
                    target_found = True
        print("-" * 40)
        
        if target_found:
            print(f"✅ Label '{config.TARGET_LABEL}' found.")
        else:
            print(f"❌ Label '{config.TARGET_LABEL}' NOT found in the list.")
            print("Current labels:")
            for label in labels:
                 print(f" - {label['name']} ({label['id']})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check_labels()
