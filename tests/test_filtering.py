import pytest
from services.filtering import is_allowed_email # Using import here but ensuring to reload or use module reference if possible. 
# Better: Import inside the function as planned.
# Re-writing file to remove top-level import of is_allowed_email?
# Actually simpler: just import services.filtering and use services.filtering.is_allowed_email
import services.filtering

# モック用の設定値
# 実際には環境変数やconfig.pyから読み込まれるが、
# テスト分離のため、環境変数をモックするか、あるいはロジックだけテストする。
# ここでは環境変数をセットアップ時に注入するか、
# is_allowed_email が config.ALLOWED_DOMAINS などを参照している点に注意。

@pytest.fixture
def mock_config():
    """機密情報をモック"""
    import services.filtering
    
    # Save original values
    original_domains = getattr(services.filtering.config, "ALLOWED_DOMAINS", [])
    original_keywords = getattr(services.filtering.config, "SUBJECT_KEYWORDS", [])
    
    # Inject test values directly
    services.filtering.config.ALLOWED_DOMAINS = ["example.com", "trusted.org"]
    services.filtering.config.SUBJECT_KEYWORDS = ["invoice", "bill", "請求書"]
    
    yield
    
    # Restore original values
    services.filtering.config.ALLOWED_DOMAINS = original_domains
    services.filtering.config.SUBJECT_KEYWORDS = original_keywords

def test_is_allowed_domain(mock_config):
    # 許可ドメイン AND 許可キーワード
    assert services.filtering.is_allowed_email("user@example.com", "Invoice") == True
    assert services.filtering.is_allowed_email("admin@trusted.org", "Monthly Bill") == True
    
    # 不許可ドメインだが Subject で許可 (ORロジック)
    assert services.filtering.is_allowed_email("spam@evil.com", "Invoice") == True
    
    # 完全拒否 (Domain NG + Subject NG)
    assert services.filtering.is_allowed_email("spam@evil.com", "Unknown Spam") == False

def test_is_allowed_subject(mock_config):
    # 不許可ドメインだが、件名がキーワードを含む場合
    assert services.filtering.is_allowed_email("unknown@random.com", "Please find the Invoice attached") == True
    assert services.filtering.is_allowed_email("unknown@random.com", "[請求書] 12月分") == True
    
    # 不許可ドメイン かつ キーワードなし
    assert services.filtering.is_allowed_email("unknown@random.com", "Hello World") == False

def test_case_insensitivity(mock_config):
    # 大文字小文字の無視
    assert services.filtering.is_allowed_email("user@EXAMPLE.COM", "Invoice") == True
    assert services.filtering.is_allowed_email("u@x.com", "INVOICE") == True
