from google_auth_oauthlib.flow import InstalledAppFlow
import os

# 許可を求める権限の範囲（Gmailの読み書き・ラベル変更）
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    print("--- Gmail API Refresh Token Getter ---")
    
    # credentials.json の存在確認
    if not os.path.exists('credentials.json'):
        print("Error: 'credentials.json' が見つかりません。")
        print("GCPコンソールからOAuthクライアントIDのJSONをダウンロードし、")
        print("このスクリプトと同じ場所に 'credentials.json' という名前で保存してください。")
        return

    try:
        # OAuthフローの開始
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        # ローカルサーバーを立ち上げてブラウザ認証を行う
        creds = flow.run_local_server(port=0)
        
        print("\n" + "="*60)
        print("★ 認証成功！以下の情報を Cloud Run の環境変数に設定してください")
        print("="*60)
        print(f"GMAIL_CLIENT_ID:     {creds.client_id}")
        print(f"GMAIL_CLIENT_SECRET: {creds.client_secret}")
        print(f"GMAIL_REFRESH_TOKEN: {creds.refresh_token}")
        print("="*60 + "\n")
        
        print("※ 注意: これらの値は機密情報です。第三者に共有しないでください。")

    except Exception as e:
        print(f"\nError: 認証中にエラーが発生しました。\n{e}")

if __name__ == '__main__':
    main()
