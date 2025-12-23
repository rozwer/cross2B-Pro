"""Authentication schemas.

VULN-005/006: 認証データ構造
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT トークンペイロード"""

    sub: str = Field(..., description="Subject (user_id)")
    tenant_id: str = Field(..., description="Tenant identifier")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field(default="access", description="Token type: access or refresh")
    roles: list[str] = Field(default_factory=list, description="User roles")


class AuthUser(BaseModel):
    """認証済みユーザー情報"""

    user_id: str = Field(..., description="User identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    email: str | None = Field(default=None, description="User email")
    roles: list[str] = Field(default_factory=list, description="User roles")


class LoginRequest(BaseModel):
    """ログインリクエスト"""

    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password")


class LoginResponse(BaseModel):
    """ログインレスポンス"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: AuthUser


class RefreshRequest(BaseModel):
    """トークンリフレッシュリクエスト"""

    refresh_token: str


class RefreshResponse(BaseModel):
    """トークンリフレッシュレスポンス"""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class AuthFailureLog(BaseModel):
    """認証失敗ログ"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    token_fragment: str | None = None  # 最初の10文字のみ（セキュリティ）
    ip_address: str | None = None
    user_agent: str | None = None
