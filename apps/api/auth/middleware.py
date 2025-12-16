"""Authentication middleware for FastAPI.

Security requirements:
- JWT tokens for API authentication
- tenant_id extracted from JWT payload (not URL/body parameters)
- Authentication failures logged to audit log
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .schemas import TokenPayload

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

security = HTTPBearer(auto_error=False)


def create_access_token(
    tenant_id: str,
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new JWT access token.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    tenant_id: str,
    user_id: str,
) -> str:
    """Create a new refresh token.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier

    Returns:
        Encoded refresh token string
    """
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid
    """
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return TokenPayload(
        tenant_id=payload["tenant_id"],
        user_id=payload["user_id"],
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        jti=payload.get("jti"),
    )


async def get_current_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    """Extract and validate tenant_id from JWT token.

    Security requirements:
    - tenant_id is extracted from JWT payload (URL/Body parameters are NOT trusted)
    - Validation failures are logged for audit

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Validated tenant_id

    Raises:
        HTTPException: 401 if authentication fails
    """
    if credentials is None:
        logger.warning("Authentication failed: No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        tenant_id = payload.tenant_id

        if not tenant_id:
            logger.warning(
                "Authentication failed: Missing tenant_id in token",
                extra={"token_fragment": credentials.credentials[:10]},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing tenant_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return tenant_id

    except JWTError as e:
        logger.warning(
            f"Authentication failed: Invalid token - {e}",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_optional_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """Extract tenant_id from JWT token if provided.

    Same as get_current_tenant but returns None instead of raising
    an exception when no credentials are provided.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        tenant_id if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_tenant(credentials)
    except HTTPException:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TokenPayload:
    """Get the full token payload for the current user.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Full token payload including user_id, tenant_id, etc.

    Raises:
        HTTPException: 401 if authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_token(credentials.credentials)
    except JWTError as e:
        logger.warning(f"Authentication failed: Invalid token - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
