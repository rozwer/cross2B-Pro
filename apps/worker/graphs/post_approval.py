"""Post-approval LangGraph graph.

Handles steps 3.5-12 after human approval.
This graph runs automatically once approval signal is received.

Graph flow:
    step3_5 → step4 → step5 → step6 → step6_5 → step7a → step7b → step8 → step9 → step10 → step12 → END

Note: step11 (Image Generation) is handled separately via API.
step12 (WordPress HTML Generation) is the final step.
"""

# NOTE: LangGraph Studio loads this file directly, so we need to ensure
# the project root is on sys.path for absolute imports to work.
# ruff: noqa: E402
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent  # apps/worker/graphs -> project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.tools.registry import ToolRegistry
from apps.worker.graphs.wrapper import create_node_function

# ============================================================
# Step Node Functions
# ============================================================


async def step3_5_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 3.5: Human Touch Generation.

    Generates emotional analysis, human-touch patterns, and experience episodes
    to make content more relatable and engaging.
    Uses Gemini for natural, creative expression.
    """
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "gemini"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 4000),
        temperature=config.get("temperature", 0.7),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an expert at creating emotionally resonant, human-centered content.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
        emotional_analysis = parsed.get("emotional_analysis", {})
        human_touch_patterns = parsed.get("human_touch_patterns", [])
        experience_episodes = parsed.get("experience_episodes", [])
        emotional_hooks = parsed.get("emotional_hooks", [])
    except json.JSONDecodeError:
        emotional_analysis = {}
        human_touch_patterns = []
        experience_episodes = []
        emotional_hooks = []

    return {
        "step": "step3_5",
        "human_touch_elements": response.content,
        "emotional_analysis": emotional_analysis,
        "human_touch_patterns": human_touch_patterns,
        "experience_episodes": experience_episodes,
        "emotional_hooks": emotional_hooks,
        "model": response.model,
    }


async def step4_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 4: Strategic Outline."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 4000),
        temperature=config.get("temperature", 0.6),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content strategist.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"raw_content": response.content}

    return {
        "step": "step4",
        "outline": parsed,
        "model": response.model,
    }


async def step5_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 5: Primary Source Collection."""
    config = ctx.config
    registry = ToolRegistry()
    keyword = config.get("keyword", "")

    # Try to collect primary sources
    collector = registry.get("primary_collector")
    sources: list[dict[str, Any]] = []

    if collector:
        queries = [
            f"{keyword} research statistics",
            f"{keyword} official data",
        ]

        for query in queries:
            try:
                result = await collector.execute(query=query)
                if result.success and result.data:
                    sources.extend(result.data.get("evidence_refs", []))
            except Exception:
                continue

    return {
        "step": "step5",
        "sources": sources,
        "source_count": len(sources),
    }


async def step6_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 6: Enhanced Outline."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 5000),
        temperature=config.get("temperature", 0.6),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content outline specialist.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"raw_content": response.content}

    return {
        "step": "step6",
        "enhanced_outline": parsed,
        "model": response.model,
    }


async def step6_5_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 6.5: Integration Package."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 6000),
        temperature=config.get("temperature", 0.5),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content integration specialist.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
        integration_package = parsed.get("integration_package", "")
        outline_summary = parsed.get("outline_summary", "")
        section_count = parsed.get("section_count", 0)
        total_sources = parsed.get("total_sources", 0)
    except json.JSONDecodeError:
        integration_package = response.content
        outline_summary = ""
        section_count = 0
        total_sources = 0

    return {
        "step": "step6_5",
        "integration_package": integration_package,
        "outline_summary": outline_summary,
        "section_count": section_count,
        "total_sources": total_sources,
        "model": response.model,
    }


async def step7a_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 7A: Draft Generation (longest step)."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.7),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content writer.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
        draft = parsed.get("draft", "")
        section_count = parsed.get("section_count", 0)
        cta_positions = parsed.get("cta_positions", [])
    except json.JSONDecodeError:
        draft = response.content
        section_count = 0
        cta_positions = []

    return {
        "step": "step7a",
        "draft": draft,
        "word_count": len(draft.split()),
        "section_count": section_count,
        "cta_positions": cta_positions,
        "model": response.model,
    }


async def step7b_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 7B: Brush Up."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "gemini"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.8),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a content polishing expert.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
        polished = parsed.get("polished", "")
        changes_made = parsed.get("changes_made", [])
    except json.JSONDecodeError:
        polished = response.content
        changes_made = []

    return {
        "step": "step7b",
        "polished": polished,
        "word_count": len(polished.split()),
        "changes_made": changes_made,
        "model": response.model,
    }


async def step8_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 8: Fact Check."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "gemini"),
        model=config.get("llm_model"),
    )

    # Fact check
    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 4000),
        temperature=0.3,
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a fact-checking expert.",
        config=llm_config,
    )

    verification = response.content
    has_contradictions = "contradiction" in verification.lower()

    return {
        "step": "step8",
        "verification": verification,
        "has_contradictions": has_contradictions,
        "recommend_rejection": has_contradictions,
        "model": response.model,
    }


async def step9_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 9: Final Rewrite."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.6),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a content rewriting expert.",
        config=llm_config,
    )

    # Parse JSON response
    try:
        parsed = json.loads(response.content)
        final_content = parsed.get("final_content", "")
        meta_description = parsed.get("meta_description", "")
        internal_link_suggestions = parsed.get("internal_link_suggestions", [])
    except json.JSONDecodeError:
        final_content = response.content
        meta_description = ""
        internal_link_suggestions = []

    return {
        "step": "step9",
        "final_content": final_content,
        "word_count": len(final_content.split()),
        "meta_description": meta_description,
        "internal_link_suggestions": internal_link_suggestions,
        "model": response.model,
    }


async def step10_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 10: Final Output."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "anthropic"),
        model=config.get("llm_model"),
    )

    # Generate HTML
    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 8000),
        temperature=0.3,
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an HTML content generator.",
        config=llm_config,
    )

    html_content = response.content

    # Basic HTML validation
    html_valid = "<html" in html_content.lower() and "<body" in html_content.lower() and "</html>" in html_content.lower()

    return {
        "step": "step10",
        "html": html_content,
        "html_valid": html_valid,
        "completed_at": datetime.now().isoformat(),
        "model": response.model,
    }


async def step12_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 12: WordPress HTML Generation.

    Converts final articles to WordPress Gutenberg block format.
    Processes step10 output and step11 images (if available).
    """

    # Get step10 articles from state
    step10_output = state.step_outputs.get("step10", {})
    step11_output = state.step_outputs.get("step11", {})

    articles_data = step10_output.get("articles", [])
    _ = step11_output.get("images", [])  # Reserved for future image integration

    # If no articles array, check for single article (backward compatibility)
    if not articles_data and step10_output.get("html"):
        articles_data = [
            {
                "article_number": 1,
                "html_content": step10_output.get("html", ""),
                "title": step10_output.get("article_title", ""),
            }
        ]

    wordpress_articles = []

    for article in articles_data:
        article_number = article.get("article_number", 1)
        html_content = article.get("html_content", "")
        title = article.get("title", "")

        # Convert to Gutenberg blocks
        gutenberg_html = _convert_to_gutenberg(html_content)

        wordpress_articles.append(
            {
                "article_number": article_number,
                "filename": f"article_{article_number}.html",
                "html_content": html_content,
                "gutenberg_blocks": gutenberg_html,
                "metadata": {
                    "title": title,
                    "word_count": len(html_content),
                },
                "images": [],
            }
        )

    return {
        "step": "step12",
        "articles": wordpress_articles,
        "common_assets": {
            "css_classes": [
                "wp-block-paragraph",
                "wp-block-heading",
                "wp-block-image",
                "wp-block-list",
            ],
            "recommended_plugins": ["Yoast SEO"],
        },
        "generation_metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": ctx.config.get("llm_model", ""),
            "wordpress_version_target": "6.0+",
            "total_articles": len(wordpress_articles),
        },
        "model": ctx.config.get("llm_model", ""),
    }


def _convert_to_gutenberg(html_content: str) -> str:
    """Convert HTML to WordPress Gutenberg block format."""

    lines = html_content.split("\n")
    gutenberg_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Heading blocks
        if line.startswith("<h1"):
            gutenberg_lines.append('<!-- wp:heading {"level":1} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        elif line.startswith("<h2"):
            gutenberg_lines.append("<!-- wp:heading -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        elif line.startswith("<h3"):
            gutenberg_lines.append('<!-- wp:heading {"level":3} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        # Paragraph blocks
        elif line.startswith("<p"):
            gutenberg_lines.append("<!-- wp:paragraph -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:paragraph -->")
        # List blocks
        elif line.startswith("<ul"):
            gutenberg_lines.append("<!-- wp:list -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:list -->")
        elif line.startswith("<ol"):
            gutenberg_lines.append('<!-- wp:list {"ordered":true} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:list -->")
        # Image blocks
        elif line.startswith("<img") or line.startswith("<figure"):
            gutenberg_lines.append("<!-- wp:image -->")
            gutenberg_lines.append(f'<figure class="wp-block-image">{line}</figure>')
            gutenberg_lines.append("<!-- /wp:image -->")
        else:
            gutenberg_lines.append(line)

    return "\n".join(gutenberg_lines)


# ============================================================
# Graph Builder
# ============================================================


def build_post_approval_graph() -> Any:
    """Build the post-approval LangGraph graph.

    Returns:
        Compiled StateGraph ready for execution
    """
    graph: StateGraph[Any, Any, Any, Any] = StateGraph(GraphState)

    # Create node functions with wrapper
    step3_5_node = create_node_function("step3_5", step3_5_execute)
    step4_node = create_node_function("step4", step4_execute)
    step5_node = create_node_function("step5", step5_execute)
    step6_node = create_node_function("step6", step6_execute)
    step6_5_node = create_node_function("step6_5", step6_5_execute)
    step7a_node = create_node_function("step7a", step7a_execute)
    step7b_node = create_node_function("step7b", step7b_execute)
    step8_node = create_node_function("step8", step8_execute)
    step9_node = create_node_function("step9", step9_execute)
    step10_node = create_node_function("step10", step10_execute)
    step12_node = create_node_function("step12", step12_execute)

    # Add nodes
    graph.add_node("step3_5", step3_5_node)  # type: ignore[call-overload]
    graph.add_node("step4", step4_node)  # type: ignore[call-overload]
    graph.add_node("step5", step5_node)  # type: ignore[call-overload]
    graph.add_node("step6", step6_node)  # type: ignore[call-overload]
    graph.add_node("step6_5", step6_5_node)  # type: ignore[call-overload]
    graph.add_node("step7a", step7a_node)  # type: ignore[call-overload]
    graph.add_node("step7b", step7b_node)  # type: ignore[call-overload]
    graph.add_node("step8", step8_node)  # type: ignore[call-overload]
    graph.add_node("step9", step9_node)  # type: ignore[call-overload]
    graph.add_node("step10", step10_node)  # type: ignore[call-overload]
    graph.add_node("step12", step12_node)  # type: ignore[call-overload]

    # Add edges (linear flow)
    # Note: step11 (Image Generation) is handled separately via API
    graph.add_edge(START, "step3_5")
    graph.add_edge("step3_5", "step4")
    graph.add_edge("step4", "step5")
    graph.add_edge("step5", "step6")
    graph.add_edge("step6", "step6_5")
    graph.add_edge("step6_5", "step7a")
    graph.add_edge("step7a", "step7b")
    graph.add_edge("step7b", "step8")
    graph.add_edge("step8", "step9")
    graph.add_edge("step9", "step10")
    graph.add_edge("step10", "step12")
    graph.add_edge("step12", END)

    # Set entry and finish points
    graph.set_entry_point("step3_5")
    graph.set_finish_point("step12")

    return graph.compile()


# Export compiled graph
post_approval_graph = build_post_approval_graph()
