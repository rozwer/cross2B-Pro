"""Hearing template CRUD API endpoints.

This module provides endpoints for managing hearing templates -
reusable configurations for the article hearing wizard.

VULN-004: テナント分離必須
VULN-011: 監査ログ記録
"""

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db.audit import AuditLogger
from apps.api.db.models import HearingTemplate as HearingTemplateModel
from apps.api.db.tenant import get_tenant_manager
from apps.api.schemas.article_hearing import (
    HearingTemplate,
    HearingTemplateCreate,
    HearingTemplateList,
    HearingTemplateUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hearing", tags=["hearing"])


@router.post("/templates", response_model=HearingTemplate)
async def create_template(
    template: HearingTemplateCreate,
    user: AuthUser = Depends(get_current_user),
) -> HearingTemplate:
    """Create a new hearing template.

    Args:
        template: Template data to create
        user: Authenticated user

    Returns:
        Created template

    Raises:
        HTTPException: If template name already exists for this tenant
    """
    manager = get_tenant_manager()
    async with manager.get_session(user.tenant_id) as session:
        # Create new template
        db_template = HearingTemplateModel(
            id=str(uuid4()),
            tenant_id=user.tenant_id,
            name=template.name,
            description=template.description,
            data=template.data.model_dump(),
        )

        try:
            session.add(db_template)
            await session.flush()

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="create",
                resource_type="hearing_template",
                resource_id=db_template.id,
                details={
                    "name": template.name,
                    "description": template.description,
                },
            )

            await session.commit()

            logger.info(
                "Hearing template created",
                extra={
                    "tenant_id": user.tenant_id,
                    "user_id": user.user_id,
                    "template_id": db_template.id,
                    "template_name": template.name,
                },
            )

            return HearingTemplate.model_validate(db_template)

        except IntegrityError:
            # Note: session.rollback() is called automatically by context manager
            raise HTTPException(
                status_code=409,
                detail=f"Template with name '{template.name}' already exists",
            )


@router.get("/templates", response_model=HearingTemplateList)
async def list_templates(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> HearingTemplateList:
    """List all hearing templates for the current tenant.

    Args:
        limit: Maximum number of templates to return
        offset: Number of templates to skip
        user: Authenticated user

    Returns:
        Paginated list of templates
    """
    manager = get_tenant_manager()
    async with manager.get_session(user.tenant_id) as session:
        # Count total
        count_query = select(func.count()).select_from(HearingTemplateModel).where(HearingTemplateModel.tenant_id == user.tenant_id)
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get templates
        query = (
            select(HearingTemplateModel)
            .where(HearingTemplateModel.tenant_id == user.tenant_id)
            .order_by(HearingTemplateModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(query)
        templates = result.scalars().all()

        return HearingTemplateList(
            items=[HearingTemplate.model_validate(t) for t in templates],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/templates/{template_id}", response_model=HearingTemplate)
async def get_template(
    template_id: UUID,
    user: AuthUser = Depends(get_current_user),
) -> HearingTemplate:
    """Get a specific hearing template.

    Args:
        template_id: Template UUID
        user: Authenticated user

    Returns:
        Template details

    Raises:
        HTTPException: If template not found or belongs to different tenant
    """
    manager = get_tenant_manager()
    async with manager.get_session(user.tenant_id) as session:
        query = select(HearingTemplateModel).where(
            HearingTemplateModel.id == str(template_id),
            HearingTemplateModel.tenant_id == user.tenant_id,  # Tenant isolation
        )
        result = await session.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found",
            )

        return HearingTemplate.model_validate(template)


@router.put("/templates/{template_id}", response_model=HearingTemplate)
async def update_template(
    template_id: UUID,
    update: HearingTemplateUpdate,
    user: AuthUser = Depends(get_current_user),
) -> HearingTemplate:
    """Update a hearing template.

    Args:
        template_id: Template UUID
        update: Fields to update
        user: Authenticated user

    Returns:
        Updated template

    Raises:
        HTTPException: If template not found or name conflict
    """
    manager = get_tenant_manager()
    async with manager.get_session(user.tenant_id) as session:
        query = select(HearingTemplateModel).where(
            HearingTemplateModel.id == str(template_id),
            HearingTemplateModel.tenant_id == user.tenant_id,
        )
        result = await session.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found",
            )

        # Track changes for audit
        changes: dict[str, str | dict[str, str | None]] = {}

        # Update fields
        if update.name is not None:
            changes["name"] = {"old": template.name, "new": update.name}
            template.name = update.name

        if update.description is not None:
            changes["description"] = {
                "old": template.description,
                "new": update.description,
            }
            template.description = update.description

        if update.data is not None:
            changes["data"] = "updated"
            template.data = update.data.model_dump()

        try:
            await session.flush()

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="update",
                resource_type="hearing_template",
                resource_id=str(template_id),
                details={"changes": changes},
            )

            await session.commit()

            logger.info(
                "Hearing template updated",
                extra={
                    "tenant_id": user.tenant_id,
                    "user_id": user.user_id,
                    "template_id": str(template_id),
                    "changes": list(changes.keys()),
                },
            )

            return HearingTemplate.model_validate(template)

        except IntegrityError:
            # Note: session.rollback() is called automatically by context manager
            raise HTTPException(
                status_code=409,
                detail=f"Template with name '{update.name}' already exists",
            )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """Delete a hearing template.

    Args:
        template_id: Template UUID
        user: Authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If template not found
    """
    manager = get_tenant_manager()
    async with manager.get_session(user.tenant_id) as session:
        query = select(HearingTemplateModel).where(
            HearingTemplateModel.id == str(template_id),
            HearingTemplateModel.tenant_id == user.tenant_id,
        )
        result = await session.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found",
            )

        template_name = template.name

        # Audit log before deletion
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="delete",
            resource_type="hearing_template",
            resource_id=str(template_id),
            details={"name": template_name},
        )

        await session.delete(template)
        await session.commit()

        logger.info(
            "Hearing template deleted",
            extra={
                "tenant_id": user.tenant_id,
                "user_id": user.user_id,
                "template_id": str(template_id),
                "template_name": template_name,
            },
        )

        return {"success": True, "message": f"Template '{template_name}' deleted"}
