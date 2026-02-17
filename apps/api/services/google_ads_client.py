"""Google Ads API client factory.

Provides a shared GoogleAdsClient instance for Keyword Planner operations.
Supports configuration from environment variables.

Required env vars:
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_CUSTOMER_ID
"""

import logging
import os

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException  # noqa: F401 (re-export)

logger = logging.getLogger(__name__)

GOOGLE_ADS_ENV_VARS = {
    "developer_token": "GOOGLE_ADS_DEVELOPER_TOKEN",
    "client_id": "GOOGLE_ADS_CLIENT_ID",
    "client_secret": "GOOGLE_ADS_CLIENT_SECRET",
    "refresh_token": "GOOGLE_ADS_REFRESH_TOKEN",
    "login_customer_id": "GOOGLE_ADS_CUSTOMER_ID",
}

REQUIRED_FIELDS = list(GOOGLE_ADS_ENV_VARS.keys())

_cached_client: GoogleAdsClient | None = None
_cached_customer_id: str | None = None


class GoogleAdsConfigError(Exception):
    """Raised when Google Ads configuration is missing or invalid."""

    pass


def _load_credentials_from_env() -> dict[str, str]:
    """Load all 5 Google Ads credentials from environment variables."""
    credentials: dict[str, str] = {}
    missing: list[str] = []
    for field, env_var in GOOGLE_ADS_ENV_VARS.items():
        value = os.getenv(env_var, "").strip()
        if value:
            credentials[field] = value
        else:
            missing.append(env_var)

    if missing:
        raise GoogleAdsConfigError(
            f"Missing Google Ads environment variables: {', '.join(missing)}. "
            "Set USE_MOCK_GOOGLE_ADS=true or provide all required credentials."
        )
    return credentials


def get_google_ads_client(
    credentials: dict[str, str] | None = None,
) -> tuple[GoogleAdsClient, str]:
    """Get or create a GoogleAdsClient instance.

    Args:
        credentials: Optional dict with keys matching REQUIRED_FIELDS.
                     If None, loads from environment variables (with caching).

    Returns:
        Tuple of (GoogleAdsClient, customer_id)

    Raises:
        GoogleAdsConfigError: If credentials are missing or invalid.
    """
    global _cached_client, _cached_customer_id

    if _cached_client is not None and credentials is None:
        return _cached_client, _cached_customer_id  # type: ignore[return-value]

    creds = credentials or _load_credentials_from_env()

    missing = [f for f in REQUIRED_FIELDS if not creds.get(f)]
    if missing:
        raise GoogleAdsConfigError(f"Missing required Google Ads fields: {', '.join(missing)}")

    # Strip hyphens from customer_id (API requires plain numeric ID)
    customer_id = creds["login_customer_id"].replace("-", "")

    client_config = {
        "developer_token": creds["developer_token"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "login_customer_id": customer_id,
        "use_proto_plus": True,
    }

    try:
        client = GoogleAdsClient.load_from_dict(client_config)
    except Exception as e:
        raise GoogleAdsConfigError(f"Failed to initialize Google Ads client: {e}") from e

    # Cache only for env-var path (shared credentials)
    if credentials is None:
        _cached_client = client
        _cached_customer_id = customer_id

    return client, customer_id


def reset_client_cache() -> None:
    """Reset the cached client. For testing."""
    global _cached_client, _cached_customer_id
    _cached_client = None
    _cached_customer_id = None
