import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any

# Optional imports for GCP (only needed if in production/GCP mode)
try:
    from google.cloud import storage
    from google.cloud import bigquery
except ImportError:
    storage = None
    bigquery = None

logger = logging.getLogger(__name__)

class StorageAdapter(ABC):
    @abstractmethod
    def save_file(self, bucket_name: str, file_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Saves a file and returns its access URL.
        """
        pass

class BigQueryAdapter(ABC):
    @abstractmethod
    def insert_rows(self, table_id: str, rows: List[dict], row_ids: Optional[List[str]] = None) -> List[dict]:
        """
        Inserts rows and returns a list of errors (empty if success).
        """
        pass

    @abstractmethod
    def get_processed_count(self, target_date_iso: str) -> int:
        """
        Returns the number of processed items for a given date (YYYY-MM-DD).
        """
        pass

# --- GCP Implementations ---

class GCPStorageAdapter(StorageAdapter):
    def __init__(self):
        if not storage:
            raise ImportError("google-cloud-storage is not installed.")
        self.client = storage.Client()

    def save_file(self, bucket_name: str, file_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"https://storage.cloud.google.com/{bucket_name}/{file_path}"

class GCPBigQueryAdapter(BigQueryAdapter):
    def __init__(self):
        if not bigquery:
            raise ImportError("google-cloud-bigquery is not installed.")
        self.client = bigquery.Client()

    def insert_rows(self, table_id: str, rows: List[dict], row_ids: Optional[List[str]] = None) -> List[dict]:
        return self.client.insert_rows_json(table_id, rows, row_ids=row_ids)

    def get_processed_count(self, target_date_iso: str) -> int:
        import config
        query = f"""
            SELECT COUNT(*) as count
            FROM `{config.BQ_TABLE_ID}`
            WHERE DATE(processed_at) = '{target_date_iso}'
        """
        job = self.client.query(query)
        result = job.result()
        for row in result:
            return row.count
        return 0

# --- Local Emulation Implementations ---

class LocalStorageAdapter(StorageAdapter):
    def __init__(self, base_dir: str = "local_storage"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def save_file(self, bucket_name: str, file_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        # Construct full local path: local_storage/bucket_name/file_path
        # file_path is likely "YYYY/MM/DD/filename"
        full_path = os.path.join(self.base_dir, bucket_name, file_path)
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(data)
            
        logger.info(f"[ローカルエミュレーション] ファイルを保存しました: {full_path}")
        return f"file://{os.path.abspath(full_path)}"

class LocalBigQueryAdapter(BigQueryAdapter):
    def __init__(self, log_file: str = "local_bq_log.jsonl"):
        self.log_file = log_file

    def insert_rows(self, table_id: str, rows: List[dict], row_ids: Optional[List[str]] = None) -> List[dict]:
        # Append rows to a JSONL file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for i, row in enumerate(rows):
                    record = {
                        "table_id": table_id,
                        "row_id": row_ids[i] if row_ids and i < len(row_ids) else None,
                        "data": row,
                        "inserted_at": str(import_datetime().datetime.now())
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            logger.info(f"[ローカルエミュレーション] {len(rows)} 行を {self.log_file} に追記しました")
            return [] # Success
        except Exception as e:
            logger.error(f"[ローカルエミュレーション] BQログの書き込みに失敗しました: {e}")
            return [{"error": str(e)}]

    def get_processed_count(self, target_date_iso: str) -> int:
        if not os.path.exists(self.log_file):
            return 0
        
        count = 0
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        # data.processed_at をチェック
                        processed_at = record.get('data', {}).get('processed_at', '')
                        if processed_at.startswith(target_date_iso):
                            count += 1
                    except:
                        pass
        except Exception as e:
            logger.error(f"[ローカルエミュレーション] ログ読み込みエラー: {e}")
        return count

def import_datetime():
    import datetime
    return datetime

# --- Factory ---

def get_storage_adapter() -> StorageAdapter:
    env = os.getenv("APP_ENV", "production")
    if env == "local":
        return LocalStorageAdapter()
    return GCPStorageAdapter()

def get_bigquery_adapter() -> BigQueryAdapter:
    env = os.getenv("APP_ENV", "production")
    if env == "local":
        return LocalBigQueryAdapter()
    return GCPBigQueryAdapter()
