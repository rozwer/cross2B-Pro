"""Content suggestion API endpoints.

This module provides endpoints for generating AI suggestions for various input fields
in the article hearing form. Uses Gemini 2.5 Flash for cost-effective suggestions.
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.llm import GeminiClient, LLMError, sanitize_user_input
from apps.worker.helpers import OutputParser
from apps.api.schemas.article_hearing import (
    ChildTopicSuggestion,
    ChildTopicSuggestionRequest,
    ChildTopicSuggestionResponse,
    RelatedKeywordSuggestionItem,
    RelatedKeywordSuggestionRequest,
    RelatedKeywordSuggestionResponse,
    TargetAudienceSuggestion,
    TargetAudienceSuggestionRequest,
    TargetAudienceSuggestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])

# Fixed model for suggestions (fast and cost-effective)
SUGGESTION_MODEL = os.getenv("SUGGESTION_MODEL", "gemini-2.5-flash")

# Singleton LLM client
_llm_client: GeminiClient | None = None


def get_llm_client() -> GeminiClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiClient(model=SUGGESTION_MODEL)
    return _llm_client


_parser = OutputParser()


def extract_json_from_response(content: str) -> dict[str, object]:
    """Extract JSON from LLM response using OutputParser.

    Handles code blocks, embedded JSON, trailing commas, JS comments,
    and control characters.
    """
    result = _parser.parse_json(content)
    if not result.success or not isinstance(result.data, dict):
        raise ValueError(f"Failed to parse JSON from LLM response: format={result.format_detected}")
    return result.data


# =============================================================================
# Target Audience Suggestions
# =============================================================================

TARGET_AUDIENCE_PROMPT = """あなたはSEOとマーケティングの専門家です。
以下の事業内容と目標CVに基づいて、最適なターゲット読者像を5つ提案してください。

## 入力情報

### 事業内容
{business_description}

### 目標CV
{target_cv}

## 出力形式

以下のJSON形式で厳密に出力してください。他の文章は含めないでください。

```json
{{
  "suggestions": [
    {{
      "audience": "ターゲット読者像（役職、年齢層、課題などを含む具体的な記述）",
      "rationale": "この読者像を提案する理由"
    }}
  ]
}}
```

## 提案のポイント

1. 役職・立場を明確に（例: 人事部長、経営者、現場マネージャー）
2. 具体的な課題や悩みを含める
3. 年齢層やキャリアステージを考慮
4. CVにつながりやすいセグメントを優先
5. 多様な角度から5つの異なるペルソナを提案"""


@router.post("/target-audience", response_model=TargetAudienceSuggestionResponse)
async def suggest_target_audience(
    request: TargetAudienceSuggestionRequest,
    user: AuthUser = Depends(get_current_user),
) -> TargetAudienceSuggestionResponse:
    """Generate target audience suggestions based on business description.

    Args:
        request: Business description and target CV
        user: Authenticated user

    Returns:
        List of target audience suggestions
    """
    logger.info(
        "Generating target audience suggestions",
        extra={
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
        },
    )

    try:
        client = get_llm_client()

        safe_business = sanitize_user_input(request.business_description)
        cv_labels = {
            "inquiry": "問い合わせ獲得",
            "document_request": "資料請求",
            "free_consultation": "無料相談申込",
            "other": "その他",
        }
        safe_cv = cv_labels.get(request.target_cv, request.target_cv)

        prompt = TARGET_AUDIENCE_PROMPT.format(
            business_description=safe_business,
            target_cv=safe_cv,
        )

        response = await client.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a marketing expert. Always respond with valid JSON only.",
        )

        data = extract_json_from_response(response.content)
        suggestions = [
            TargetAudienceSuggestion(
                audience=s.get("audience", ""),
                rationale=s.get("rationale", ""),
            )
            for s in data.get("suggestions", [])[:5]
        ]

        return TargetAudienceSuggestionResponse(
            suggestions=suggestions,
            model_used=f"gemini/{SUGGESTION_MODEL}",
            generated_at=datetime.now().isoformat(),
        )

    except LLMError as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"LLM service error: {e}") from e
    except ValueError as e:
        logger.error(f"JSON parse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse response: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions") from e


# =============================================================================
# Related Keyword Suggestions
# =============================================================================

RELATED_KEYWORD_PROMPT = """あなたはSEOキーワード分析の専門家です。
以下のメインキーワードに関連するキーワードを10個提案してください。

## 入力情報

### メインキーワード
{main_keyword}

### 事業内容（コンテキスト）
{business_description}

## 出力形式

以下のJSON形式で厳密に出力してください。他の文章は含めないでください。

```json
{{
  "suggestions": [
    {{
      "keyword": "関連キーワード",
      "volume": "推定月間検索ボリューム（例: 100-200）",
      "relation_type": "関連タイプ（synonym/long_tail/question/related_topic）"
    }}
  ]
}}
```

## 関連タイプの説明

- synonym: 同義語・類義語
- long_tail: ロングテールキーワード（より具体的な派生）
- question: 疑問形キーワード（〜とは、〜方法）
- related_topic: 関連トピック

## 提案のポイント

1. メインキーワードとの関連性が高いものを優先
2. 検索ボリュームと競合性のバランスを考慮
3. 記事内で自然に使えるキーワードを選ぶ
4. 事業内容に適したキーワードを優先
5. 様々な関連タイプをバランスよく含める"""


@router.post("/related-keywords", response_model=RelatedKeywordSuggestionResponse)
async def suggest_related_keywords(
    request: RelatedKeywordSuggestionRequest,
    user: AuthUser = Depends(get_current_user),
) -> RelatedKeywordSuggestionResponse:
    """Generate related keyword suggestions based on main keyword.

    Args:
        request: Main keyword and business context
        user: Authenticated user

    Returns:
        List of related keyword suggestions
    """
    logger.info(
        "Generating related keyword suggestions",
        extra={
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
            "main_keyword": request.main_keyword,
        },
    )

    try:
        client = get_llm_client()

        safe_keyword = sanitize_user_input(request.main_keyword)
        safe_business = sanitize_user_input(request.business_description)

        prompt = RELATED_KEYWORD_PROMPT.format(
            main_keyword=safe_keyword,
            business_description=safe_business,
        )

        response = await client.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an SEO keyword expert. Always respond with valid JSON only.",
        )

        data = extract_json_from_response(response.content)
        suggestions = [
            RelatedKeywordSuggestionItem(
                keyword=s.get("keyword", ""),
                volume=s.get("volume", "10-50"),
                relation_type=s.get("relation_type", "related_topic"),
            )
            for s in data.get("suggestions", [])[:10]
        ]

        return RelatedKeywordSuggestionResponse(
            suggestions=suggestions,
            model_used=f"gemini/{SUGGESTION_MODEL}",
            generated_at=datetime.now().isoformat(),
        )

    except LLMError as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"LLM service error: {e}") from e
    except ValueError as e:
        logger.error(f"JSON parse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse response: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions") from e


# =============================================================================
# Child Topic Suggestions
# =============================================================================

CHILD_TOPIC_PROMPT = """あなたはSEOコンテンツ戦略の専門家です。
トピッククラスター戦略に基づいて、以下の親記事に対する子記事トピックを5つ提案してください。

## 入力情報

### 親記事のメインキーワード
{main_keyword}

### 事業内容
{business_description}

### ターゲット読者
{target_audience}

## 出力形式

以下のJSON形式で厳密に出力してください。他の文章は含めないでください。

```json
{{
  "suggestions": [
    {{
      "topic": "子記事のトピック・タイトル案",
      "target_keyword": "この子記事でターゲットするキーワード",
      "rationale": "このトピックを提案する理由"
    }}
  ]
}}
```

## 提案のポイント

1. 親記事を補完する詳細トピックを選ぶ
2. 各子記事が独立して価値を持つ内容にする
3. ターゲット読者の検索意図を考慮
4. 事業のCVにつながりやすいトピックを優先
5. SEO的に狙いやすいキーワードを設定"""


@router.post("/child-topics", response_model=ChildTopicSuggestionResponse)
async def suggest_child_topics(
    request: ChildTopicSuggestionRequest,
    user: AuthUser = Depends(get_current_user),
) -> ChildTopicSuggestionResponse:
    """Generate child topic suggestions for topic cluster strategy.

    Args:
        request: Main keyword, business description, and target audience
        user: Authenticated user

    Returns:
        List of child topic suggestions
    """
    logger.info(
        "Generating child topic suggestions",
        extra={
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
            "main_keyword": request.main_keyword,
        },
    )

    try:
        client = get_llm_client()

        safe_keyword = sanitize_user_input(request.main_keyword)
        safe_business = sanitize_user_input(request.business_description)
        safe_audience = sanitize_user_input(request.target_audience)

        prompt = CHILD_TOPIC_PROMPT.format(
            main_keyword=safe_keyword,
            business_description=safe_business,
            target_audience=safe_audience,
        )

        response = await client.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an SEO content strategist. Always respond with valid JSON only.",
        )

        data = extract_json_from_response(response.content)
        suggestions = [
            ChildTopicSuggestion(
                topic=s.get("topic", ""),
                target_keyword=s.get("target_keyword", ""),
                rationale=s.get("rationale", ""),
            )
            for s in data.get("suggestions", [])[:5]
        ]

        return ChildTopicSuggestionResponse(
            suggestions=suggestions,
            model_used=f"gemini/{SUGGESTION_MODEL}",
            generated_at=datetime.now().isoformat(),
        )

    except LLMError as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"LLM service error: {e}") from e
    except ValueError as e:
        logger.error(f"JSON parse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse response: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions") from e
