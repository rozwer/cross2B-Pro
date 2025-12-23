"""Authentication middleware for FastAPI.

VULN-005/006: 認証ミドルウェア
- JWT トークン検証
- tenant_id 抽出（JWT ペイロードから取得、URL/Body パラメータは信用しない）
- 監査ログ連携
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .schemas import AuthFailureLog, AuthUser, TokenPayload

# プロジェクトルートの .env を読み込む
_project_root = Path(__file__).resolve().parents[3]
load_dotenv(_project_root / ".env")

logger = logging.getLogger(__name__)

# JWT設定
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 開発モード設定（認証スキップ）
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SKIP_AUTH = ENVIRONMENT == "development"
DEV_TENANT_ID = os.getenv("DEV_TENANT_ID", "dev-tenant-001")

# HTTPBearer スキーム
security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """認証エラー"""

    def __init__(self, message: str, reason: str = "unknown"):
        self.message = message
        self.reason = reason
        super().__init__(message)


def create_access_token(
    user_id: str,
    tenant_id: str,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """アクセストークンを生成"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = TokenPayload(
        sub=user_id,
        tenant_id=tenant_id,
        exp=int(expire.timestamp()),
        iat=int(now.timestamp()),
        type="access",
        roles=roles or [],
    )

    return str(jwt.encode(payload.model_dump(), JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """リフレッシュトークンを生成"""
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.utcnow()
    expire = now + expires_delta

    payload = TokenPayload(
        sub=user_id,
        tenant_id=tenant_id,
        exp=int(expire.timestamp()),
        iat=int(now.timestamp()),
        type="refresh",
        roles=[],
    )

    return str(jwt.encode(payload.model_dump(), JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))


def verify_token(token: str, expected_type: str = "access") -> TokenPayload:
    """JWT トークンを検証

    Args:
        token: JWT トークン
        expected_type: 期待するトークンタイプ ("access" or "refresh")

    Returns:
        TokenPayload: 検証済みペイロード

    Raises:
        AuthError: 検証失敗時
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        token_data = TokenPayload(**payload)

        # トークンタイプの検証
        if token_data.type != expected_type:
            raise AuthError(
                f"Invalid token type: expected {expected_type}, got {token_data.type}",
                reason="invalid_token_type",
            )

        # 有効期限の検証（jose が自動で行うが、明示的にも確認）
        if datetime.utcnow().timestamp() > token_data.exp:
            raise AuthError("Token has expired", reason="token_expired")

        # tenant_id の存在確認
        if not token_data.tenant_id:
            raise AuthError("Missing tenant_id in token", reason="missing_tenant_id")

        return token_data

    except JWTError as e:
        raise AuthError(f"Token validation failed: {e}", reason="invalid_token") from e


async def log_auth_failure(
    request: Request,
    reason: str,
    token_fragment: str | None = None,
) -> None:
    """認証失敗を監査ログに記録

    TODO: VULN-011 で完全な監査ログ実装後に連携
    """
    log_entry = AuthFailureLog(
        reason=reason,
        token_fragment=token_fragment[:10] if token_fragment else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.warning(
        f"Auth failure: {reason}",
        extra={
            "auth_failure": log_entry.model_dump(),
        },
    )


async def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """tenant_id を取得

    NOTE: 開発段階では認証を無効化し、固定の tenant_id を返す
    """
    # 開発モード: 認証スキップ
    if SKIP_AUTH:
        return DEV_TENANT_ID

    if credentials is None:
        await log_auth_failure(request, "missing_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(credentials.credentials)
        return token_data.tenant_id

    except AuthError as e:
        await log_auth_failure(
            request,
            e.reason,
            credentials.credentials[:10] if credentials.credentials else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser:
    """認証ユーザー情報を取得

    NOTE: 開発段階では認証を無効化し、固定のユーザー情報を返す
    """
    # 開発モード: 認証スキップ
    if SKIP_AUTH:
        return AuthUser(
            user_id="dev-user-001",
            tenant_id=DEV_TENANT_ID,
            roles=["admin"],
        )

    if credentials is None:
        await log_auth_failure(request, "missing_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(credentials.credentials)
        return AuthUser(
            user_id=token_data.sub,
            tenant_id=token_data.tenant_id,
            roles=token_data.roles,
        )

    except AuthError as e:
        await log_auth_failure(
            request,
            e.reason,
            credentials.credentials[:10] if credentials.credentials else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthUser | None:
    """オプショナルな認証（ログインしていなくてもOK）

    公開エンドポイント向け
    """
    if credentials is None:
        return None

    try:
        token_data = verify_token(credentials.credentials)
        return AuthUser(
            user_id=token_data.sub,
            tenant_id=token_data.tenant_id,
            roles=token_data.roles,
        )
    except AuthError:
        return None
