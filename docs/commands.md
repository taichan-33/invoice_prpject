# ローカル開発コマンド集

ローカル環境で開発・実行・テストを行うためによく使うコマンドのまとめです。

## 1. 仮想環境 (venv)

### 有効化 (Activate)

作業を開始する前に必ず実行してください。

```bash
# Mac / Linux
source .venv/bin/activate

# Windows (Git Bash など)
source .venv/Scripts/activate
```

### 無効化 (Deactivate)

作業が終わったら実行します。

```bash
deactivate
```

---

## 2. セットアップ

### 依存ライブラリのインストール

`requirements.txt` に記載されたライブラリを一括インストールします。

```bash
pip install -r requirements.txt
```

### 環境変数の準備

`.env.example` をコピーして `.env` を作成します（初回のみ）。

```bash
cp .env.example .env
# その後、vim やエディタで .env を編集して認証情報などを入力
```

---

## 3. アプリケーション実行

### Gmail 監視 (ポーリングモード)

ローカルで Gmail を定期チェックし、処理を実行します。

```bash
python watch_gmail.py
```

- 停止するには `Ctrl + C` を押します。

---

## 4. テスト

### 全テストの実行

```bash
pytest tests/
```

### 特定のファイルのみテスト

```bash
pytest tests/test_processor.py
```

### 詳細表示 (Verbose)

どのテストが実行されたか詳しく表示します。

```bash
pytest -v tests/
```

---

## 5. その他便利コマンド

### キャッシュの削除 (トラブルシュート)

Python のキャッシュファイル (`__pycache__` 等) を削除してクリーンにします。

```bash
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type d -name ".pytest_cache" -exec rm -r {} +
```

### Slack 通知テスト

#### 日次レポートの手動送信

昨日の処理件数を集計してレポートを送ります。

```bash
python report_daily.py
```

#### テストメッセージの送信 (ワンライナー)

Webhook が正しく設定されているか確認するための簡単なテストです。

```bash
python -c "import services.slack; services.slack.send_slack_alert('これはテスト通知です', level='success')"
```
