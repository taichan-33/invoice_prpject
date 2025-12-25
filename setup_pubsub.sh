#!/bin/bash

# ==========================================
# Invoice Project: Pub/Sub & DLQ Setup Script
# ==========================================
# このスクリプトは、Gmailからの通知を受け取るための Pub/Sub トピックと
# エラー時の受け皿となる Dead Letter Queue (DLQ) を自動構築します。

# --- 設定変数の定義 ---
# .env ファイルがあれば読み込む
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# 環境変数があればそれを使い、なければデフォルト値(プレースホルダー)を使う
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
TOPIC_NAME="gmail-notification"
SUBSCRIPTION_NAME="push-to-cloudrun"

# DLQ (死活監視) 用の設定
DLQ_TOPIC_NAME="gmail-notification-dlq"
DLQ_SUBSCRIPTION_NAME="pull-dlq"

# Push先のCloud Run URL
# .env に SERVICE_URL があれば使い、なければプレースホルダー
SERVICE_URL=${SERVICE_URL:-"https://your-cloud-run-url.run.app"}
# Push認証用のサービスアカウント
SERVICE_ACCOUNT_EMAIL="scheduler-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

# --- 実行 ---

echo "🚀 Pub/Sub Setup Starting..."

# 1. Main Topic の作成
echo "Creating Main Topic: $TOPIC_NAME"
gcloud pubsub topics create $TOPIC_NAME --project=$PROJECT_ID || echo "Topic already exists."

# 2. DLQ Topic の作成
echo "Creating DLQ Topic: $DLQ_TOPIC_NAME"
gcloud pubsub topics create $DLQ_TOPIC_NAME --project=$PROJECT_ID || echo "DLQ Topic already exists."

# 3. DLQ Subscription の作成 (Pull型で人間が確認できるようにする)
echo "Creating DLQ Subscription: $DLQ_SUBSCRIPTION_NAME"
gcloud pubsub subscriptions create $DLQ_SUBSCRIPTION_NAME \
    --topic=$DLQ_TOPIC_NAME \
    --project=$PROJECT_ID \
    || echo "DLQ Subscription already exists."

# 4. Main Subscription の作成 (Push型 + DLQ設定)
# 最大配信試行回数(max-delivery-attempts)を 5回 に設定
echo "Creating Main Subscription: $SUBSCRIPTION_NAME"
gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
    --topic=$TOPIC_NAME \
    --project=$PROJECT_ID \
    --push-endpoint=$SERVICE_URL \
    --push-auth-service-account=$SERVICE_ACCOUNT_EMAIL \
    --dead-letter-topic=$DLQ_TOPIC_NAME \
    --max-delivery-attempts=5 \
    || echo "Subscription already exists or failed. (Check if SERVICE_URL is correct)"

# 5. Gmail に通知権限を付与
echo "Granting permissions to Gmail..."
gcloud pubsub topics add-iam-policy-binding $TOPIC_NAME \
    --project=$PROJECT_ID \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

# 6. Pub/Sub サービスアカウントに DLQ への等号権限を付与 (DLQ転送に必要)
# プロジェクトの Pub/Sub サービスアカウントを取得
PUBSUB_SA_EMAIL="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
# ※ プロジェクト番号の取得が必要なので、簡易的にユーザーに手動確認を促すか、今回は権限付与コマンドのみ表示

echo "--------------------------------------------------------"
echo "✅ Setup Complete!"
echo "重要: もし DLQ への転送権限エラーが出る場合は、GCPコンソールで"
echo "Pub/Sub サービスアカウントに 'Pub/Sub Publisher' (DLQトピックに対して) と"
echo "'Pub/Sub Subscriber' (Mainサブスクリプションに対して) を付与してください。"
echo "--------------------------------------------------------"
