#!/bin/bash

# Cloud Scheduler 設定用コマンド
# このスクリプトはデプロイ後に一度だけ実行してください。

# 変数設定
# .env ファイルがあれば読み込む
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION="asia-northeast1"
SERVICE_NAME="invoice-processor"
SCHEDULER_JOB_NAME="refresh-gmail-watch"
SERVICE_ACCOUNT_NAME="scheduler-invoker"

# 1. Cloud Scheduler 用のサービスアカウントを作成
echo "Creating Service Account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name "Cloud Scheduler Invoker"

# 2. サービスアカウントに Cloud Run を起動する権限を付与
echo "Granting permissions..."
gcloud run services add-iam-policy-binding $SERVICE_NAME \
    --member=serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/run.invoker \
    --region=$REGION

# 3. Cloud Run の URL を取得
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"

# 4. 毎日朝9時に /refresh-watch を叩くジョブを作成
echo "Creating Scheduler Job..."
gcloud scheduler jobs create http $SCHEDULER_JOB_NAME \
    --schedule="0 9 * * *" \
    --uri="${SERVICE_URL}/refresh-watch" \
    --http-method=POST \
    --oidc-service-account-email=${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --location=$REGION

echo "✅ Setup Complete!"

# 5. 毎朝09:00に日次レポートを送るジョブを作成
REPORT_JOB_NAME="send-daily-report"
echo "Creating Report Job..."
gcloud scheduler jobs create http $REPORT_JOB_NAME \
    --schedule="0 9 * * *" \
    --uri="${SERVICE_URL}/report" \
    --http-method=POST \
    --oidc-service-account-email=${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --location=$REGION
