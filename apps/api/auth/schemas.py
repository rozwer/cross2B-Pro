"""Authentication-related schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    exp: datetime = Field(..., description="Token expiration time")
    iat: datetime = Field(..., description="Token issued at time")
    jti: str | None = Field(default=None, description="JWT ID for token tracking")


class TokenResponse(BaseModel):
    """Token response for login/refresh endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class LoginRequest(BaseModel):
    """Login request for development/testing."""

    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    secret: str = Field(..., description="Authentication secret")
