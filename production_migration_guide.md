# 本番移行（Production Migration）設定指示書

ローカルでの検証が完了し、本番環境（Google Cloud Run）へデプロイするための完全な手順書です。
これに従って設定を行えば、自動デプロイと Pub/Sub 連携が完了します。

## 1. 修正・確認が必要なファイル

### `config.py` / `.env` (環境変数)

コード自体の修正は不要です。`main.py` や `services/` は `APP_ENV` 環境変数によって挙動を自動的に切り替えます。
本番環境への設定値の注入は **GitHub Secrets** を通じて行います。

---

## 2. GitHub Secrets の設定 (必須)

GitHub Actions がデプロイ時に使用する機密情報を設定します。
GitHub リポジトリの **Settings > Secrets and variables > Actions** に移動し、以下を追加してください。

| Secret 名               | 設定すべき値                         | 取得元                                          |
| :---------------------- | :----------------------------------- | :---------------------------------------------- |
| **GCP_PROJECT_ID**      | あなたの GCP プロジェクト ID         | `gcp_setup_guide.md` 手順 1                     |
| **GCP_SA_KEY**          | サービスアカウントの JSON キーの中身 | GCP コンソール (IAM > サービスアカウント)       |
| **GMAIL_CLIENT_ID**     | OAuth クライアント ID                | `.env` または `config.py`                       |
| **GMAIL_CLIENT_SECRET** | OAuth クライアントシークレット       | `.env` または `config.py`                       |
| **GMAIL_REFRESH_TOKEN** | OAuth リフレッシュトークン           | `.env` または `get_refresh_token.py` の実行結果 |

> [!IMPORTANT] > `GCP_SA_KEY` はファイルの中身をそのまま（改行を含めて）貼り付けてください。

---

## 3. デプロイ設定の最終確認 (`.github/workflows/deploy.yml`)

デプロイ時に Cloud Run に渡される環境変数が定義されています。
デフォルトで以下のようになっていますが、必要に応じて変更してください。

```yaml
env_vars: |
  APP_ENV=production
  GOOGLE_CLOUD_PROJECT=${{ secrets.GCP_PROJECT_ID }}
  TARGET_LABEL=Label_4713097559777965986  <-- ★ここを確認！
  ALLOWED_DOMAINS=                        <-- 空欄なら制限なし
  SUBJECT_KEYWORDS=                       <-- 空欄なら制限なし
  # (以下略)
```

> [!WARNING] > **TARGET_LABEL の注意点:**
> ローカル検証で判明した **「Label ID (例: Label_4713097559777965986)」** を設定することを推奨します。
> 単なる名前（`TARGET`）だと、Gmail API が認識できない場合があります。

---

## 4. Pub/Sub 通知のフィルタリング設定

Cloud Run が「全てのメール」で起動してしまうのを防ぎ、「特定のラベル」がついた時だけ起動するようにします。

### 手順

1.  ローカルの `setup_watch.py` を開きます。
2.  `WATCH_LABEL_IDS` 変数を編集し、**通知させたいラベルの ID** を指定します。

```python
# 悪い例（全ての未読のみ）
# WATCH_LABEL_IDS = ['UNREAD']

# 良い例（TARGETラベルがついたものだけ通知）
# ※ check_labels.py で確認したIDを使ってください
WATCH_LABEL_IDS = ['Label_4713097559777965986']
```

3.  設定を反映させるためにスクリプトを実行します。
    ```bash
    python3 setup_watch.py
    ```
    - 成功すると `History ID` が返ってきます。
    - これで Gmail 側でフィルタリングされ、指定したラベルが付いた時だけ Cloud Run が呼び出されるようになります。

---

## 5. 初回デプロイと動作確認

1.  変更を GitHub に Push します。
    ```bash
    git add .
    git commit -m "Prepare for production deployment"
    git push origin main
    ```
2.  GitHub の「Actions」タブを開き、ワークフローが緑色（Success）になるのを待ちます。
3.  GCP コンソールの「Cloud Run」を開き、緑色のチェックがついていることを確認します。
4.  Gmail にテストメールを送信し、ラベルを付与します。
5.  Cloud Run の「ログ」タブを見て、`INFO: メッセージを処理中...` と出れば成功です！

---

### トラブルシューティング

- **デプロイが失敗する:** `GCP_SA_KEY` が正しいか、IAM 権限（Cloud Run 管理者、Service Account User など）が足りているか確認してください。
- **メールが処理されない:** `setup_watch.py` のトピック名が間違っていないか、Gmail への権限付与（Publisher）ができているか確認してください。
