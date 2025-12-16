"""監査ログサービス

VULN-011: 監査ログの完全性保証
- チェーンハッシュによる改ざん検知
- 追記専用（UPDATE/DELETE禁止はDBトリガーで強制）
- ハッシュ検証機能

使用例:
    from apps.api.db.audit import AuditLogger

    async with tenant_db_manager.get_session(tenant_id) as session:
        audit = AuditLogger(session)
        await audit.log(
            user_id="user123",
            action="approve",
            resource_type="run",
            resource_id="run-456",
            details={"comment": "LGTM"}
        )

        # 整合性検証
        is_valid = await audit.verify_chain()
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogIntegrityError(Exception):
    """監査ログの整合性エラー"""

    def __init__(self, message: str, entry_id: int | None = None):
        self.message = message
        self.entry_id = entry_id
        super().__init__(message)


class AuditLogger:
    """監査ログサービス

    チェーンハッシュを使用して監査ログの整合性を保証。
    """

    def __init__(self, session: AsyncSession):
        """初期化

        Args:
            session: データベースセッション（テナントDB）
        """
        self.session = session

    def _compute_entry_hash(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None,
        created_at: datetime,
        prev_hash: str | None,
    ) -> str:
        """エントリーのハッシュを計算

        Args:
            各フィールド

        Returns:
            SHA256ハッシュ（16進数）
        """
        # 決定的なJSON文字列を生成
        data = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "created_at": created_at.isoformat(),
            "prev_hash": prev_hash,
        }
        # ソートされたキーで決定的なJSON
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def _get_last_entry(self) -> AuditLog | None:
        """最新の監査ログエントリーを取得"""
        result = await self.session.execute(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """監査ログを記録

        Args:
            user_id: 操作を行ったユーザーID
            action: アクション種別（approve, reject, create, delete等）
            resource_type: リソース種別（run, artifact等）
            resource_id: リソースID
            details: 追加詳細情報

        Returns:
            作成されたAuditLogエントリー
        """
        # 前のエントリーのハッシュを取得
        last_entry = await self._get_last_entry()
        prev_hash = last_entry.entry_hash if last_entry else None

        # タイムスタンプ
        created_at = datetime.now()

        # エントリーハッシュを計算
        entry_hash = self._compute_entry_hash(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            created_at=created_at,
            prev_hash=prev_hash,
        )

        # エントリー作成
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            created_at=created_at,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )

        self.session.add(entry)
        await self.session.flush()  # IDを取得

        logger.info(
            "Audit log created",
            extra={
                "audit_id": entry.id,
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "entry_hash": entry_hash[:16] + "...",
            },
        )

        return entry

    async def verify_chain(self, limit: int | None = None) -> bool:
        """監査ログのチェーンハッシュを検証

        Args:
            limit: 検証するエントリー数（None=全件）

        Returns:
            True: 整合性OK
            False: 改ざん検知

        Raises:
            AuditLogIntegrityError: 改ざんが検出された場合
        """
        query = select(AuditLog).order_by(AuditLog.id.asc())
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        entries = result.scalars().all()

        if not entries:
            return True

        prev_hash: str | None = None

        for entry in entries:
            # 前のハッシュの整合性チェック
            if entry.prev_hash != prev_hash:
                logger.error(
                    f"Audit log chain broken at id={entry.id}: "
                    f"expected prev_hash={prev_hash}, got {entry.prev_hash}"
                )
                raise AuditLogIntegrityError(
                    f"Chain broken at entry {entry.id}: prev_hash mismatch",
                    entry_id=entry.id,
                )

            # エントリーハッシュの再計算と比較
            computed_hash = self._compute_entry_hash(
                user_id=entry.user_id,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=entry.details,
                created_at=entry.created_at,
                prev_hash=entry.prev_hash,
            )

            if computed_hash != entry.entry_hash:
                logger.error(
                    f"Audit log tampered at id={entry.id}: "
                    f"computed hash={computed_hash}, stored hash={entry.entry_hash}"
                )
                raise AuditLogIntegrityError(
                    f"Entry {entry.id} has been tampered with",
                    entry_id=entry.id,
                )

            prev_hash = entry.entry_hash

        logger.info(f"Audit log chain verified: {len(entries)} entries OK")
        return True

    async def get_logs(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """監査ログを検索

        Args:
            resource_type: リソース種別でフィルター
            resource_id: リソースIDでフィルター
            user_id: ユーザーIDでフィルター
            action: アクションでフィルター
            limit: 取得件数上限
            offset: オフセット

        Returns:
            AuditLogのリスト
        """
        query = select(AuditLog).order_by(AuditLog.id.desc())

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())
