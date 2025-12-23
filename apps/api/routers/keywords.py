"""Keyword suggestion API endpoints.

This module provides endpoints for generating keyword suggestions using LLM.
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.schemas.article_hearing import (
    CompetitionLevel,
    KeywordSuggestion,
    KeywordSuggestionRequest,
    KeywordSuggestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keywords", tags=["keywords"])

# Fixed model for keyword suggestions (fast and cost-effective)
SUGGESTION_MODEL = os.getenv("KEYWORD_SUGGESTION_MODEL", "gemini-2.0-flash")
SUGGESTION_PLATFORM = os.getenv("KEYWORD_SUGGESTION_PLATFORM", "gemini")


async def generate_keywords_with_llm(
    theme_topics: str,
    business_description: str,
    target_audience: str,
) -> list[KeywordSuggestion]:
    """Generate keyword suggestions using LLM.

    Args:
        theme_topics: User's theme/topic description
        business_description: Business context
        target_audience: Target reader description

    Returns:
        List of keyword suggestions with estimated metrics
    """
    # TODO: Implement actual LLM call when API key is available
    # For now, return mock data based on input
    # The theme_topics parameter will be used when LLM integration is added
    _ = theme_topics  # Mark as intentionally unused for now

    suggestions = []
    base_keywords = [
        ("派遣社員 教育方法", "100-200", CompetitionLevel.MEDIUM, 0.95),
        ("派遣社員 研修プログラム", "50-100", CompetitionLevel.LOW, 0.88),
        ("派遣社員 定着率向上", "100-200", CompetitionLevel.MEDIUM, 0.92),
        ("派遣社員 eラーニング", "50-100", CompetitionLevel.LOW, 0.85),
        ("派遣社員 スキルアップ", "200-500", CompetitionLevel.HIGH, 0.80),
        ("派遣社員 OJT 方法", "10-50", CompetitionLevel.LOW, 0.90),
        ("派遣社員 教育体制", "10-50", CompetitionLevel.LOW, 0.87),
        ("派遣社員 離職率 改善", "50-100", CompetitionLevel.MEDIUM, 0.93),
        ("派遣会社 教育制度", "50-100", CompetitionLevel.MEDIUM, 0.82),
        ("派遣社員 モチベーション向上", "100-200", CompetitionLevel.MEDIUM, 0.78),
    ]

    for keyword, volume, competition, score in base_keywords[:10]:
        suggestions.append(
            KeywordSuggestion(
                keyword=keyword,
                estimated_volume=volume,
                estimated_competition=competition,
                relevance_score=score,
            )
        )

    return suggestions


@router.post("/suggest", response_model=KeywordSuggestionResponse)
async def suggest_keywords(
    request: KeywordSuggestionRequest,
    user: AuthUser = Depends(get_current_user),
) -> KeywordSuggestionResponse:
    """Generate keyword suggestions based on theme topics.

    This endpoint uses a fast LLM model to generate keyword suggestions
    with estimated search volume and competition level.

    Args:
        request: Theme topics and context information
        user: Authenticated user

    Returns:
        List of keyword suggestions
    """
    logger.info(
        "Generating keyword suggestions",
        extra={
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
            "theme_length": len(request.theme_topics),
        },
    )

    try:
        suggestions = await generate_keywords_with_llm(
            theme_topics=request.theme_topics,
            business_description=request.business_description,
            target_audience=request.target_audience,
        )

        return KeywordSuggestionResponse(
            suggestions=suggestions,
            model_used=f"{SUGGESTION_PLATFORM}/{SUGGESTION_MODEL}",
            generated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to generate keyword suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate keyword suggestions",
        ) from e
