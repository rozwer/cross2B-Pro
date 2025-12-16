"""FastAPI application entry point.

SEO Article Generator API server with endpoints for:
- Run management (create, list, get, approve, reject, retry, cancel)
- Artifact retrieval
- WebSocket progress streaming

VULN-005/006/008: セキュリティ強化
- 認証ミドルウェア
- WebSocket認証
- CORS設定強化
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel

from apps.api.auth import get_current_tenant, get_current_user
from apps.api.auth.middleware import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    create_refresh_token,
    verify_token,
    AuthError,
)
from apps.api.auth.schemas import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Environment Validation
# =============================================================================

def validate_environment() -> list[str]:
    """Validate required environment variables.

    Returns:
        List of warning messages for missing optional variables
    """
    warnings = []

    # Check LLM API keys (at least one should be set for production)
    llm_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    has_llm_key = any(os.getenv(key) for key in llm_keys)

    if not has_llm_key and os.getenv("USE_MOCK_LLM", "false").lower() != "true":
        warnings.append(
            "No LLM API key set. Set at least one of: "
            f"{', '.join(llm_keys)} or set USE_MOCK_LLM=true"
        )

    return warnings


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("=" * 60)
    logger.info("SEO Article Generator - API Server Starting")
    logger.info("=" * 60)

    # Validate environment
    warnings = validate_environment()
    for warning in warnings:
        logger.warning(warning)

    # Log configuration
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS', '*')}")

    yield

    logger.info("API Server shutting down...")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="SEO Article Generator API",
    description="API for managing SEO article generation workflows",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (VULN-008: 許可オリジンを明示的に指定)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# 空文字列を除去
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
if not cors_origins:
    cors_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)


# =============================================================================
# Health Check
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


# =============================================================================
# Authentication Endpoints (VULN-005)
# =============================================================================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """ログイン処理

    TODO: 実際のユーザー認証ロジックを実装
    現在はスタブ実装
    """
    # スタブ: 開発用のダミー認証
    # TODO: データベースからユーザー検証
    if os.getenv("ENVIRONMENT") == "development":
        # 開発環境ではダミートークンを返す
        user = AuthUser(
            user_id="dev-user",
            tenant_id="dev-tenant",
            email=request.email,
            roles=["user"],
        )
        access_token = create_access_token(user.user_id, user.tenant_id, user.roles)
        refresh_token = create_refresh_token(user.user_id, user.tenant_id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=15 * 60,  # 15分
            user=user,
        )

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/auth/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(request: RefreshRequest) -> RefreshResponse:
    """トークンリフレッシュ"""
    try:
        token_data = verify_token(request.refresh_token, expected_type="refresh")

        # 新しいアクセストークンを発行
        new_access_token = create_access_token(
            token_data.sub,
            token_data.tenant_id,
            token_data.roles,
        )

        # 新しいリフレッシュトークンを発行（オプション）
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


@app.post("/api/auth/logout")
async def logout(user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """ログアウト処理

    TODO: トークンの無効化リストへの追加（Redis等）
    """
    logger.info(f"User logged out: {user.user_id}")
    return {"success": True}


# =============================================================================
# Run Management Endpoints (認証必須)
# =============================================================================

class RunCreateRequest(BaseModel):
    """Request to create a new run."""
    input_data: dict[str, object]
    config: dict[str, object] | None = None


class RunResponse(BaseModel):
    """Run response model."""
    id: str
    tenant_id: str
    status: str
    current_step: str | None
    config: dict[str, object]
    created_at: str


@app.post("/api/runs", response_model=RunResponse)
async def create_run(
    request: RunCreateRequest,
    tenant_id: str = Depends(get_current_tenant),  # 認証必須、tenant_id は JWT から取得
) -> RunResponse:
    """Create a new workflow run.

    セキュリティ要件:
    - tenant_id は JWT から取得（リクエストボディは信用しない）
    """
    # TODO: Implement run creation with Temporal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/api/runs")
async def list_runs(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    tenant_id: str = Depends(get_current_tenant),  # 認証必須
) -> dict[str, object]:
    """List runs with optional filtering.

    セキュリティ要件:
    - tenant_id は JWT から取得（クエリパラメータは無視）
    """
    # TODO: Implement with database query
    return {"runs": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    """Get run details."""
    # TODO: Implement with database query
    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, comment: str | None = None) -> dict[str, object]:
    """Approve a run waiting for approval.

    Sends approval signal to Temporal workflow.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/reject")
async def reject_run(run_id: str, reason: str) -> dict[str, object]:
    """Reject a run waiting for approval.

    Sends rejection signal to Temporal workflow.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/retry/{step}")
async def retry_step(run_id: str, step: str) -> dict[str, object]:
    """Retry a failed step.

    Same conditions only - no fallback to different model/tool.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.delete("/api/runs/{run_id}")
async def cancel_run(run_id: str) -> dict[str, object]:
    """Cancel a running workflow."""
    # TODO: Implement with Temporal cancellation
    raise HTTPException(status_code=501, detail="Not implemented")


# =============================================================================
# Artifact Endpoints
# =============================================================================

@app.get("/api/runs/{run_id}/files")
async def list_artifacts(run_id: str) -> dict[str, object]:
    """List all artifacts for a run."""
    # TODO: Implement with database/storage query
    return {"artifacts": []}


@app.get("/api/runs/{run_id}/files/{step}")
async def get_step_artifact(run_id: str, step: str) -> dict[str, object]:
    """Get artifact for a specific step."""
    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


# =============================================================================
# WebSocket Progress Streaming (VULN-006: 認証対応)
# =============================================================================

# 認証タイムアウト（秒）
WS_AUTH_TIMEOUT = 10.0


@app.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates.

    VULN-006: WebSocket認証
    - 接続後に認証メッセージを待機
    - 認証失敗時は code=1008 で切断
    - テナント越境チェック
    """
    await websocket.accept()

    try:
        # 認証メッセージを待機（タイムアウト付き）
        try:
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=WS_AUTH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket auth timeout for run {run_id}")
            await websocket.close(code=1008, reason="Auth timeout")
            return

        # 認証メッセージのパース
        try:
            auth_msg = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "auth_error", "reason": "Invalid message format"})
            await websocket.close(code=1008, reason="Invalid auth message")
            return

        # 認証タイプの確認
        if auth_msg.get("type") != "auth":
            await websocket.send_json({"type": "auth_error", "reason": "Authentication required"})
            await websocket.close(code=1008, reason="Auth required")
            return

        # トークン検証
        token = auth_msg.get("token")
        if not token:
            await websocket.send_json({"type": "auth_error", "reason": "Missing token"})
            await websocket.close(code=1008, reason="Missing token")
            return

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            tenant_id = payload.get("tenant_id")
            user_id = payload.get("sub")

            if not tenant_id:
                await websocket.send_json({"type": "auth_error", "reason": "Invalid token"})
                await websocket.close(code=1008, reason="Invalid token")
                return

        except JWTError as e:
            logger.warning(f"WebSocket JWT error for run {run_id}: {e}")
            await websocket.send_json({"type": "auth_error", "reason": "Invalid token"})
            await websocket.close(code=1008, reason="Invalid token")
            return

        # テナント越境チェック
        # TODO: データベースから run の tenant_id を取得して比較
        # run = await get_run_from_db(run_id)
        # if run.tenant_id != tenant_id:
        #     await websocket.send_json({"type": "auth_error", "reason": "Access denied"})
        #     await websocket.close(code=1008, reason="Access denied")
        #     return

        # 認証成功
        await websocket.send_json({"type": "auth_success"})
        logger.info(f"WebSocket authenticated for run {run_id}, user {user_id}, tenant {tenant_id}")

        # 通常の進捗ストリーミング
        while True:
            # Wait for messages (keep connection alive)
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")


# =============================================================================
# Error Handlers (VULN-009: 内部情報を隠蔽)
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler.

    VULN-009: エラーメッセージ改善
    - 本番環境では内部情報を隠蔽
    - 開発環境ではデバッグ情報を表示
    - リクエストIDを含めてトレーサビリティを確保
    """
    import uuid

    # リクエストIDを生成（トレーサビリティ用）
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]

    # ログには詳細を記録
    logger.error(
        f"Unhandled exception [request_id={request_id}]: {exc}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # レスポンス内容は環境に応じて変更
    is_development = os.getenv("ENVIRONMENT", "development") == "development"

    if is_development:
        # 開発環境ではエラー詳細を表示（デバッグ用）
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": request_id,
            },
        )
    else:
        # 本番環境では内部情報を隠蔽
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )
