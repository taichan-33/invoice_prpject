# GCP Environment Setup Guide

このドキュメントでは、請求書自動処理システムを動作させるための Google Cloud Platform (GCP) の設定手順を説明します。

## 1. プロジェクトの作成

1.  [GCP コンソール](https://console.cloud.google.com/) にアクセスします。
2.  左上のプロジェクト選択プルダウンをクリックし、「**新しいプロジェクト**」を選択します。
3.  プロジェクト名（例: `invoice-processing-dev`）を入力し、「**作成**」をクリックします。
4.  作成完了後、そのプロジェクトを選択します。

## 2. 必要な API の有効化

以下の API を有効にする必要があります。

1.  左メニューの「**API とサービス**」>「**ライブラリ**」を選択します。
2.  検索バーで以下の API を検索し、それぞれ「**有効にする**」をクリックしてください。
    - **Gmail API** (メール取得・操作用)
    - **Cloud Pub/Sub API** (通知受信用)
    - **Cloud Storage** (本来はデフォルト有効ですが確認)
    - **BigQuery API** (本来はデフォルト有効ですが確認)

## 3. ローカル検証用の認証設定 (`verify_real_gmail.py` 用)企業アカウント用

ローカルから実際の Gmail API を叩くために、あなたの Google アカウントの権限をローカル PC に一時的に付与します。

### 前提

- [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/docs/install) がインストールされていること。

### 手順

ターミナルで以下のコマンドを実行します。

```bash
# 1. 作成したプロジェクトを使用するように設定
gcloud config set project [YOUR_PROJECT_ID]

# 2. アプリケーションデフォルト認証(ADC)でログイン
# ※ Gmailの操作権限(Modify)をスコープに指定します
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/gmail.modify
```

コマンド実行後、ブラウザが起動します。

1.  **テストに使用したい Google アカウント**を選択してログインします。
2.  許可画面が表示されるので「**許可**」または「**Allow**」をクリックします。
3.  ターミナルに `Credentials saved to file: [...]` と表示されれば成功です。

## 4. Gmail API 認証設定 (個人アカウント用)

個人の Gmail (`@gmail.com`) を Cloud Run から操作するには、**OAuth 2.0 クライアント ID** を作成し、リフレッシュトークンを取得する必要があります。

### 4.1 OAuth 同意画面の設定

1.  GCP コンソールで「**API とサービス**」>「**OAuth 同意画面**」を開きます。
2.  User Type で「**外部 (External)**」を選択し、「作成」をクリックします。
3.  **アプリ情報:**
    - アプリ名: `Invoice Processor` (任意)
    - ユーザーサポートメール: 自分のメールアドレス
    - デベロッパーの連絡先情報: 自分のメールアドレス
    - 「保存して次へ」
4.  **スコープ:**
    - 「スコープを追加または削除」をクリック。
    - `https://www.googleapis.com/auth/gmail.modify` を検索してチェックを入れる。
    - 「更新」>「保存して次へ」
5.  **テストユーザー:**
    - **重要:** 「ADD USERS」をクリックし、**自分自身の Gmail アドレス** を追加します。
    - これを行わないと、認証時にエラーになります。
    - 「保存して次へ」

### 4.2 認証情報の作成

1.  「**API とサービス**」>「**認証情報**」を開きます。
2.  「**認証情報を作成**」>「**OAuth クライアント ID**」を選択します。
3.  **アプリケーションの種類:** 「**デスクトップ アプリ**」を選択します。
    - ※ Cloud Run は Web サーバーですが、最初のトークン取得はローカル PC(CLI)で行うため、ここでは「デスクトップ」として作成するのが一番簡単です。
4.  名前: `Remote Authenticator` (任意) と入力し、「作成」をクリックします。
5.  **クライアント ID** と **クライアント シークレット** が表示されるので、メモするか「JSON をダウンロード」してください。

### 4.3 リフレッシュトークンの取得 (ローカル作業)

Cloud Run 上で永続的に API を叩けるように、リフレッシュトークンを取得して環境変数に埋め込みます。

1.  ダウンロードした JSON ファイルを `credentials.json` という名前でプロジェクトフォルダ (`/Users/username/invoice-project/`) に置きます。
2.  以下の Python スクリプトを作成して実行します。

**`get_refresh_token.py` の作成:**

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n--- 以下の情報を Cloud Run の環境変数に設定してください ---")
    print(f"GMAIL_CLIENT_ID: {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET: {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN: {creds.refresh_token}")

if __name__ == '__main__':
    main()
```

3.  実行: `python3 get_refresh_token.py`
    - ※ 事前に `pip install google-auth-oauthlib` が必要です。
4.  ブラウザが開くのでログインし、許可します。
5.  ターミナルに表示された `GMAIL_REFRESH_TOKEN` などを控えておきます。
    - **注意:** `credentials.json` は機密情報なので、Git にはコミットしないでください。

## 5. Gmail 側の準備

テスト対象のメールを準備します。

1.  Gmail を開きます（上記で認証したアカウント）。
2.  自分宛てなどにテストメールを送信します（件名: `Invoice`, 本文: テスト, 添付: PDF など）。
3.  受信したメールに **`TARGET`** という新しいラベルを作成して付与します。
4.  そのメールを **「未読」** にします（既読の場合は「未読にする」を選択）。

## 6. 環境変数の設定

プロジェクトルートの `.env` ファイルを編集し、実際のプロジェクト ID を設定してください。

## 6. 環境変数の設定

プロジェクトルートの `.env` ファイルを編集し、実際のプロジェクト ID と、**取得した OAuth 認証情報** を設定してください。
これにより、ローカル環境でも本番環境(Cloud Run)と同じ仕組みで認証が行われます。

```bash
# .env
APP_ENV=local
GOOGLE_CLOUD_PROJECT=[YOUR_PROJECT_ID] # 作成したプロジェクトID (例: invoice-processing-dev)
TARGET_LABEL=TARGET

# フィルタリング設定 (テスト時は空推奨)
ALLOWED_DOMAINS=
SUBJECT_KEYWORDS=

# OAuth認証情報 (get_refresh_token.py で取得した値)
GMAIL_CLIENT_ID=[ここに貼り付け]
GMAIL_CLIENT_SECRET=[ここに貼り付け]
GMAIL_REFRESH_TOKEN=[ここに貼り付け]
```

## 7. 検証スクリプトの実行

```bash
python3 verify_real_gmail.py
```

成功すると、Gmail 上の該当メールの既読化が行われ、ローカルの `local_storage/` にファイルが保存されます。

## 8. コスト最適化プラン & テーブル作成 (BigQuery)

本システムのような「ログ記録」用途における、BigQuery の推奨設定です。

### 8.1 テーブル作成コマンド (推奨設定)

以下のコマンドを実行して、パーティショニング(日付分割)とクラスタリング(高速検索)が効いたテーブルを作成します。
これを行うことで、**クエリ料金を数百分の一に抑えつつ、爆速で検索**できるようになります。

```bash
# データセット作成 (未作成の場合)
bq mk --location=asia-northeast1 invoice_data

# テーブル作成 (スキーマ定義 + 最適化設定)
bq mk --table \
  --location=asia-northeast1 \
  --time_partitioning_field=received_at \
  --time_partitioning_type=DAY \
  --clustering_fields="sender_address,subject,extension" \
  invoice_data.invoice_log \
  message_id:STRING,\
received_at:TIMESTAMP,\
sender_name:STRING,\
sender_address:STRING,\
subject:STRING,\
extension:STRING,\
filename:STRING,\
file_size_bytes:INTEGER,\
content_type:STRING,\
gcs_path:STRING,\
gcs_url:STRING,\
processed_at:TIMESTAMP,\
event_id:STRING,\
attachment_id:STRING
```

### 8.2 コスト最適化のポイント

1.  **オンデマンド料金（推奨）**
    - データ量は非常に小さいため、月額定額（Slot）よりもオンデマンド（従量課金）が圧倒的に安価です。
    - **無料枠:** 毎月 1TB までのクエリ、10GB までのストレージが無料です。請求書ログ程度であれば、この無料枠内に収まる可能性が高いです。
2.  **テーブル有効期限の設定**
    - ログを永久保存する必要がない場合、データセットまたはテーブルに「有効期限（例: 3 年）」を設定することで、古いデータが自動削除され、ストレージコストの増大を防げます。

### 8.3 自動バックアップ設定 (推奨)

BigQuery 上のデータを誤操作から守るため、1 日 1 回バックアップテーブルへデータをコピーする「定期クエリ」の設定を推奨します。

**1. バックアップ用テーブルの作成 (初回のみ)**

```bash
# 本番テーブルと同じ構造で空のテーブルを作成
bq query --use_legacy_sql=false \
"CREATE TABLE invoice_data.invoice_log_backup LIKE invoice_data.invoice_log"
```

**2. 定期クエリ (Scheduled Query) の設定**
BigQuery コンソールの「スケジュールされたクエリ」から、以下の SQL を **毎日 00:00** に実行するよう設定します。

```sql
INSERT INTO `プロジェクトID.invoice_data.invoice_log_backup`
SELECT *
FROM `プロジェクトID.invoice_data.invoice_log`
# 日本時間で「昨日」のデータだけを抽出してコピー
WHERE DATE(received_at, 'Asia/Tokyo') = DATE_SUB(CURRENT_DATE('Asia/Tokyo'), INTERVAL 1 DAY)
```

これにより、サーバーレス＆追加コストほぼゼロで永久バックアップが構築できます。

## 9. 本番環境の Pub/Sub 連携設定

Cloud Run へのデプロイ完了後、Gmail の受信をトリガーにする設定を行います。

### 9. 本番環境の Pub/Sub 連携設定 (自動化スクリプト)

Cloud Run へのデプロイ完了後、以下のスクリプトを実行して Gmail 通知設定とエラーハンドリング (DLQ) 用のインフラを構築します。

1.  `setup_pubsub.sh` を開き、以下の変数をあなたの環境に合わせて編集します。

    - `PROJECT_ID`: プロジェクト ID
    - `SERVICE_URL`: Cloud Run の URL
    - `SERVICE_ACCOUNT_EMAIL`: Cloud Scheduler 用に作成した SA (または新しい SA)

2.  スクリプトを実行します。

```bash
chmod +x setup_pubsub.sh
./setup_pubsub.sh
```

これにより、以下のリソースが自動作成されます。

- `gmail-notification` (Main Topic)
- `push-to-cloudrun` (Main Subscription / Push / **DLQ 有効**)
- `gmail-notification-dlq` (Dead Letter Topic)
- `pull-dlq` (Failed Message Inspection Subscription)

### 9.4 Gmail Watch の実行 (通知の開始)

### 9.4 Gmail Watch の実行 (通知の開始)

最後に、Gmail API に「このトピックに通知を送ってくれ」と命令します。これは **1 回実行すれば OK** ですが、有効期限(通常 7 日)があるため、定期実行または Cloud Scheduler での実行が推奨されます（今回は手動実行の方法を記載します）。

ローカルで以下のスクリプト `setup_watch.py` を作成し、実行してください。

```python
import services.gmail
import config

def setup_watch():
    print("Setting up Gmail Watch...")
    srv = services.gmail.get_gmail_service()

    request = {
        'labelIds': ['UNREAD'], # 未読メールが来たら通知
        'topicName': f'projects/{config.PROJECT_ID}/topics/gmail-notification',
        'labelFilterAction': 'include'
    }

    response = srv.users().watch(userId='me', body=request).execute()
    print(f"Watch Response: {response}")

if __name__ == '__main__':
    setup_watch()
```

※ `.env` に OAuth 情報が入った状態で `python3 setup_watch.py` を実行します。`historyId` が返ってくれば成功です。
