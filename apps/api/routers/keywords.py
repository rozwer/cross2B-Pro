"""Keyword suggestion API endpoints.

This module provides endpoints for generating keyword suggestions using LLM.
"""

import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.llm import GeminiClient, LLMError, sanitize_user_input
from apps.api.schemas.article_hearing import (
    CompetitionLevel,
    KeywordSuggestion,
    KeywordSuggestionRequest,
    KeywordSuggestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keywords", tags=["keywords"])

# Fixed model for keyword suggestions (fast and cost-effective)
SUGGESTION_MODEL = os.getenv("KEYWORD_SUGGESTION_MODEL", "gemini-2.5-flash")
SUGGESTION_PLATFORM = os.getenv("KEYWORD_SUGGESTION_PLATFORM", "gemini")

# Singleton LLM client
_llm_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiClient(model=SUGGESTION_MODEL)
    return _llm_client


KEYWORD_SUGGESTION_PROMPT = """あなたはSEOキーワード提案の専門家です。
ユーザーが書きたいテーマ・トピック、事業内容、ターゲット読者の情報をもとに、
SEO記事に最適なキーワード候補を10個提案してください。

## 入力情報

### 書きたいテーマ・トピック
{theme_topics}

### 事業内容
{business_description}

### ターゲット読者
{target_audience}

## 出力形式

以下のJSON形式で厳密に出力してください。他の文章は含めないでください。

```json
{{
  "keywords": [
    {{
      "keyword": "キーワード（2-4語程度の複合キーワード）",
      "estimated_volume": "推定月間検索ボリューム（例: 100-200）",
      "competition": "high" | "medium" | "low",
      "relevance_score": 0.0〜1.0の関連度スコア
    }}
  ]
}}
```

## 提案のポイント

1. メインキーワードは2-4語の複合キーワード（ロングテール）を優先
2. 検索意図が明確なキーワードを選ぶ
3. 事業内容とターゲット読者に関連性が高いものを優先
4. 競合性が低〜中程度のキーワードを多く含める
5. 関連度スコアは、テーマとの関連性で評価（1.0が最も関連性が高い）

10個のキーワードを提案してください。"""


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
    client = get_llm_client()

    # Sanitize user inputs
    safe_theme = sanitize_user_input(theme_topics)
    safe_business = sanitize_user_input(business_description)
    safe_audience = sanitize_user_input(target_audience)

    prompt = KEYWORD_SUGGESTION_PROMPT.format(
        theme_topics=safe_theme.escaped,
        business_description=safe_business.escaped,
        target_audience=safe_audience.escaped,
    )

    logger.info(
        "Calling LLM for keyword suggestions",
        extra={"theme_length": len(theme_topics), "model": SUGGESTION_MODEL},
    )

    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO keyword suggestion expert. Always respond with valid JSON only.",
    )

    # Parse JSON response
    content = response.content.strip()

    # Extract JSON from markdown code block if present
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        content = content[start:end].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}", extra={"content": content[:500]})
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

    keywords_data = data.get("keywords", [])
    suggestions = []

    for kw in keywords_data[:10]:
        competition_str = kw.get("competition", "medium").lower()
        if competition_str == "high":
            competition = CompetitionLevel.HIGH
        elif competition_str == "low":
            competition = CompetitionLevel.LOW
        else:
            competition = CompetitionLevel.MEDIUM

        suggestions.append(
            KeywordSuggestion(
                keyword=kw.get("keyword", ""),
                estimated_volume=kw.get("estimated_volume", "10-50"),
                estimated_competition=competition,
                relevance_score=float(kw.get("relevance_score", 0.5)),
            )
        )

    logger.info(f"Generated {len(suggestions)} keyword suggestions")
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

    except LLMError as e:
        logger.error(f"LLM error generating keyword suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {e}",
        ) from e
    except ValueError as e:
        logger.error(f"Invalid LLM response for keyword suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse keyword suggestions: {e}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error generating keyword suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate keyword suggestions",
        ) from e
