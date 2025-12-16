"""Authentication module for SEO Article Generator API.

VULN-005/006: 認証基盤
- JWT 検証ミドルウェア
- テナント ID 抽出
- 監査ログ連携
"""

from .middleware import (
    AuthError,
    get_current_tenant,
    get_current_user,
    verify_token,
)
from .schemas import TokenPayload, AuthUser

__all__ = [
    "AuthError",
    "get_current_tenant",
    "get_current_user",
    "verify_token",
    "TokenPayload",
    "AuthUser",
]
