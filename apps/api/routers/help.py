"""Help content router.

Handles context-sensitive help content for UI components.
Help content is stored in the common DB (help_contents table).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.db.models import HelpContent
from apps.api.db.tenant import TenantDBManager, get_tenant_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/help", tags=["help"])


# =============================================================================
# Pydantic Models
# =============================================================================


class HelpContentResponse(BaseModel):
    """Response model for a single help content item."""

    id: int
    help_key: str
    title: str
    content: str
    category: str | None
    display_order: int


class HelpContentListResponse(BaseModel):
    """Response model for help content list."""

    items: list[HelpContentResponse]
    total: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=HelpContentListResponse)
async def list_help_contents(
    category: str | None = Query(default=None, description="Filter by category"),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> HelpContentListResponse:
    """List all active help contents.

    Optionally filter by category.
    """
    async with tenant_manager.get_common_session() as session:
        # Build query
        query = select(HelpContent).where(HelpContent.is_active == True)  # noqa: E712

        if category:
            query = query.where(HelpContent.category == category)

        query = query.order_by(HelpContent.display_order, HelpContent.help_key)

        result = await session.execute(query)
        items = result.scalars().all()

        return HelpContentListResponse(
            items=[
                HelpContentResponse(
                    id=item.id,
                    help_key=item.help_key,
                    title=item.title,
                    content=item.content,
                    category=item.category,
                    display_order=item.display_order,
                )
                for item in items
            ],
            total=len(items),
        )


@router.get("/{help_key:path}", response_model=HelpContentResponse)
async def get_help_content(
    help_key: str,
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> HelpContentResponse:
    """Get a single help content by key.

    Returns 404 if not found or not active.
    """
    async with tenant_manager.get_common_session() as session:
        query = select(HelpContent).where(
            HelpContent.help_key == help_key,
            HelpContent.is_active == True,  # noqa: E712
        )
        result = await session.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Help content not found: {help_key}",
            )

        return HelpContentResponse(
            id=item.id,
            help_key=item.help_key,
            title=item.title,
            content=item.content,
            category=item.category,
            display_order=item.display_order,
        )
