# データ抽出・分析手順書

本システムに蓄積された請求書データ（BigQuery）とファイル実体（Cloud Storage）を、業務で活用するための抽出手順まとめです。

---

## 1. BigQuery (SQL) によるデータ抽出

Google スプレッドシートの「コネクテッドシート」機能を使えば、SQL を書かずにピボットテーブルで分析したり、以下の SQL を使ってカスタム抽出したりできます。

### 基本: 全データの確認

```sql
SELECT *
FROM `your-project-id.invoice_data.invoice_log`
ORDER BY received_at DESC
LIMIT 100;
```

### ケース 1: 特定のメールアドレス（取引先）からの請求書を出す

「Amazon からの請求書だけ欲しい」場合など。

```sql
SELECT
  received_at,
  sender_address,
  subject,
  filename
FROM `your-project-id.invoice_data.invoice_log`
WHERE sender_address = 'no-reply@amazon.com'
ORDER BY received_at DESC;
```

### ケース 2: 特定の期間（今月分）を抽出

「先月の経費精算のために、先月 1 ヶ月分のリストが欲しい」場合。

```sql
SELECT *
FROM `your-project-id.invoice_data.invoice_log`
WHERE received_at BETWEEN '2025-11-01' AND '2025-11-30'
ORDER BY received_at;
```

### ケース 3: 件名に特定のキーワードを含むもの

「件名に"見積書"と入っているファイルだけ探したい」場合。

```sql
SELECT *
FROM `your-project-id.invoice_data.invoice_log`
WHERE subject LIKE '%見積書%'
ORDER BY received_at DESC;
```

### ケース 4: 月ごとの受信件数集計

「毎月どれくらい請求書が来ているか推移が見たい」場合。

```sql
SELECT
  FORMAT_DATE('%Y-%m', DATE(received_at)) AS month,
  COUNT(*) AS total_count,
  COUNT(DISTINCT message_id) AS email_count -- メールの通数（添付ファイル重複なし）
FROM `your-project-id.invoice_data.invoice_log`
GROUP BY month
ORDER BY month DESC;
```

---

## 2. Google スプレッドシート連携

SQL が苦手な方でも、スプレッドシートから直接 BigQuery データに接続できます。

1.  Google スプレッドシートを新規作成。
2.  メニューの **[データ] > [データコネクタ] > [BigQuery に接続]** を選択。
3.  プロジェクト `your-project-id` > データセット `invoice_data` > テーブル `invoice_log` を選択。
4.  **[接続]** をクリック。
5.  これでシート上にデータが表示されます。「抽出」機能を使って、Excel のようなフィルタリング操作でデータを絞り込めます。

---

## 3. Cloud Storage (ファイル実体) のダウンロード

コマンドラインツール (`gcloud` CLI) を使って、保存された PDF などを手元の PC に一括ダウンロードする方法です。

### 事前準備

Google Cloud SDK がインストールされている必要があります。

```bash
# ログイン（初回のみ）
gcloud auth login
```

### パターン 1: 特定のファイルをダウンロード

GCS 上のパスが分かっている場合（BigQuery などで確認）。

```bash
# 書式: gcloud storage cp [GCSパス] [保存先パス]
gcloud storage cp gs://invoice-archive-your-project-id/2025/12/26/msg123_invoice.pdf ./
```

### パターン 2: ある日付のフォルダごと一括ダウンロード

「2025 年 12 月 26 日のファイルを全部くれ」という場合。

```bash
# -r オプションで再帰的に（フォルダの中身も）ダウンロード
gcloud storage cp -r gs://invoice-archive-your-project-id/2025/12/26/ ./2025_12_26_data/
```

### パターン 3: 全データをバックアップとしてダウンロード

バケットの中身をまるごと手元に同期します。

```bash
# sync コマンドを使うと、差分だけダウンロードできて効率的です
gcloud storage rsync -r gs://invoice-archive-your-project-id/ ./my_backup_folder/
```

### パターン 4: ファイル名検索でダウンロード (ワイルドカード)

「"Amazon" という名前がついたファイルだけ全部欲しい」場合。

```bash
# ** で階層を無視し、ファイル名に Amazon が含まれるものを検索
gcloud storage cp "gs://invoice-archive-your-project-id/**/*Amazon*.pdf" ./downloads/
# 注意: ファイル数が膨大だと時間がかかります
```
