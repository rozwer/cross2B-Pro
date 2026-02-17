"""
Google Ads クライアントファクトリのテスト
"""

import os

import pytest
from unittest.mock import MagicMock, patch

from apps.api.services.google_ads_client import (
    GoogleAdsConfigError,
    get_google_ads_client,
    reset_client_cache,
    GOOGLE_ADS_ENV_VARS,
)


# Full set of valid credentials for testing
VALID_CREDENTIALS = {
    "developer_token": "test-dev-token",
    "client_id": "test-client-id.apps.googleusercontent.com",
    "client_secret": "test-client-secret",
    "refresh_token": "test-refresh-token",
    "login_customer_id": "123-456-7890",
}

VALID_ENV = {
    "GOOGLE_ADS_DEVELOPER_TOKEN": "test-dev-token",
    "GOOGLE_ADS_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "GOOGLE_ADS_CLIENT_SECRET": "test-client-secret",
    "GOOGLE_ADS_REFRESH_TOKEN": "test-refresh-token",
    "GOOGLE_ADS_CUSTOMER_ID": "123-456-7890",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset client cache before each test."""
    reset_client_cache()
    yield
    reset_client_cache()


class TestGoogleAdsConfigError:
    def test_is_exception(self):
        err = GoogleAdsConfigError("missing field")
        assert isinstance(err, Exception)
        assert str(err) == "missing field"


class TestLoadCredentials:
    def test_missing_all_env_vars(self):
        """全環境変数が未設定の場合"""
        env_clear = {v: "" for v in GOOGLE_ADS_ENV_VARS.values()}
        with patch.dict(os.environ, env_clear, clear=False):
            with pytest.raises(GoogleAdsConfigError, match="Missing Google Ads environment variables"):
                get_google_ads_client()

    def test_missing_partial_env_vars(self):
        """一部の環境変数が未設定の場合"""
        partial_env = {
            "GOOGLE_ADS_DEVELOPER_TOKEN": "token",
            "GOOGLE_ADS_CLIENT_ID": "",
            "GOOGLE_ADS_CLIENT_SECRET": "secret",
            "GOOGLE_ADS_REFRESH_TOKEN": "",
            "GOOGLE_ADS_CUSTOMER_ID": "123",
        }
        with patch.dict(os.environ, partial_env, clear=False):
            with pytest.raises(GoogleAdsConfigError, match="GOOGLE_ADS_CLIENT_ID"):
                get_google_ads_client()


class TestGetGoogleAdsClient:
    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_with_explicit_credentials(self, mock_gads_class):
        """明示的な認証情報で初期化"""
        mock_client = MagicMock()
        mock_gads_class.load_from_dict.return_value = mock_client

        client, customer_id = get_google_ads_client(credentials=VALID_CREDENTIALS)

        assert client is mock_client
        # Customer ID hyphens should be stripped
        assert customer_id == "1234567890"
        mock_gads_class.load_from_dict.assert_called_once()

        # Verify config passed to load_from_dict
        config = mock_gads_class.load_from_dict.call_args[0][0]
        assert config["developer_token"] == "test-dev-token"
        assert config["login_customer_id"] == "1234567890"
        assert config["use_proto_plus"] is True

    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_with_env_vars(self, mock_gads_class):
        """環境変数から初期化"""
        mock_client = MagicMock()
        mock_gads_class.load_from_dict.return_value = mock_client

        with patch.dict(os.environ, VALID_ENV, clear=False):
            client, customer_id = get_google_ads_client()

        assert client is mock_client
        assert customer_id == "1234567890"

    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_caching_for_env_vars(self, mock_gads_class):
        """環境変数パスではキャッシュが効く"""
        mock_client = MagicMock()
        mock_gads_class.load_from_dict.return_value = mock_client

        with patch.dict(os.environ, VALID_ENV, clear=False):
            client1, _ = get_google_ads_client()
            client2, _ = get_google_ads_client()

        # Should be called only once (cached)
        assert mock_gads_class.load_from_dict.call_count == 1
        assert client1 is client2

    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_no_caching_for_explicit_credentials(self, mock_gads_class):
        """明示的な認証情報ではキャッシュしない"""
        mock_gads_class.load_from_dict.return_value = MagicMock()

        get_google_ads_client(credentials=VALID_CREDENTIALS)
        get_google_ads_client(credentials=VALID_CREDENTIALS)

        # Should be called twice (no caching)
        assert mock_gads_class.load_from_dict.call_count == 2

    def test_missing_required_fields_in_credentials(self):
        """必須フィールドが空の場合"""
        incomplete = {**VALID_CREDENTIALS, "developer_token": ""}
        with pytest.raises(GoogleAdsConfigError, match="Missing required"):
            get_google_ads_client(credentials=incomplete)

    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_client_init_failure(self, mock_gads_class):
        """GoogleAdsClient 初期化失敗"""
        mock_gads_class.load_from_dict.side_effect = ValueError("invalid config")

        with pytest.raises(GoogleAdsConfigError, match="Failed to initialize"):
            get_google_ads_client(credentials=VALID_CREDENTIALS)


class TestResetClientCache:
    @patch("apps.api.services.google_ads_client.GoogleAdsClient")
    def test_reset_forces_recreation(self, mock_gads_class):
        """キャッシュリセット後は再生成される"""
        mock_gads_class.load_from_dict.return_value = MagicMock()

        with patch.dict(os.environ, VALID_ENV, clear=False):
            get_google_ads_client()
            reset_client_cache()
            get_google_ads_client()

        assert mock_gads_class.load_from_dict.call_count == 2
