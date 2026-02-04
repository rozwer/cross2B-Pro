"""Authentication router.

Handles login, token refresh, and logout endpoints.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.auth import get_current_user
from apps.api.auth.middleware import (
    AuthError,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.schemas import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """ログイン処理

    TODO: 実際のユーザー認証ロジックを実装
    現在はスタブ実装
    """
    if os.getenv("ENVIRONMENT") == "development":
        user = AuthUser(
            user_id="dev-user",
            tenant_id="dev-tenant-001",
            email=request.email,
            roles=["user"],
        )
        access_token = create_access_token(user.user_id, user.tenant_id, user.roles)
        refresh_token = create_refresh_token(user.user_id, user.tenant_id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=15 * 60,
            user=user,
        )

    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(request: RefreshRequest) -> RefreshResponse:
    """トークンリフレッシュ"""
    try:
        token_data = verify_token(request.refresh_token, expected_type="refresh")

        new_access_token = create_access_token(
            token_data.sub,
            token_data.tenant_id,
            token_data.roles,
        )

        new_refresh_token = create_refresh_token(
            token_data.sub,
            token_data.tenant_id,
        )

        return RefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=15 * 60,
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e


@router.post("/logout")
async def logout(user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """ログアウト処理

    TODO: トークンの無効化リストへの追加（Redis等）
    """
    logger.info(f"User logged out: {user.user_id}")
    return {"success": True}
