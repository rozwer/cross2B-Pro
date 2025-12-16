"""Post-approval LangGraph graph.

Handles steps 4-10 after human approval.
This graph runs automatically once approval signal is received.

Graph flow:
    step4 → step5 → step6 → step6_5 → step7a → step7b → step8 → step9 → step10 → END
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

    return {
        "step": "step4",
        "outline": response.content,
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

    return {
        "step": "step6",
        "enhanced_outline": response.content,
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

    return {
        "step": "step6_5",
        "integration_package": response.content,
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

    draft = response.content
    return {
        "step": "step7a",
        "draft": draft,
        "word_count": len(draft.split()),
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

    polished = response.content
    return {
        "step": "step7b",
        "polished": polished,
        "word_count": len(polished.split()),
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

    final_content = response.content
    return {
        "step": "step9",
        "final_content": final_content,
        "word_count": len(final_content.split()),
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
    html_valid = (
        "<html" in html_content.lower()
        and "<body" in html_content.lower()
        and "</html>" in html_content.lower()
    )

    return {
        "step": "step10",
        "html": html_content,
        "html_valid": html_valid,
        "completed_at": datetime.now().isoformat(),
        "model": response.model,
    }


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
    step4_node = create_node_function("step4", step4_execute)
    step5_node = create_node_function("step5", step5_execute)
    step6_node = create_node_function("step6", step6_execute)
    step6_5_node = create_node_function("step6_5", step6_5_execute)
    step7a_node = create_node_function("step7a", step7a_execute)
    step7b_node = create_node_function("step7b", step7b_execute)
    step8_node = create_node_function("step8", step8_execute)
    step9_node = create_node_function("step9", step9_execute)
    step10_node = create_node_function("step10", step10_execute)

    # Add nodes
    graph.add_node("step4", step4_node)  # type: ignore[call-overload]
    graph.add_node("step5", step5_node)  # type: ignore[call-overload]
    graph.add_node("step6", step6_node)  # type: ignore[call-overload]
    graph.add_node("step6_5", step6_5_node)  # type: ignore[call-overload]
    graph.add_node("step7a", step7a_node)  # type: ignore[call-overload]
    graph.add_node("step7b", step7b_node)  # type: ignore[call-overload]
    graph.add_node("step8", step8_node)  # type: ignore[call-overload]
    graph.add_node("step9", step9_node)  # type: ignore[call-overload]
    graph.add_node("step10", step10_node)  # type: ignore[call-overload]

    # Add edges (linear flow)
    graph.add_edge(START, "step4")
    graph.add_edge("step4", "step5")
    graph.add_edge("step5", "step6")
    graph.add_edge("step6", "step6_5")
    graph.add_edge("step6_5", "step7a")
    graph.add_edge("step7a", "step7b")
    graph.add_edge("step7b", "step8")
    graph.add_edge("step8", "step9")
    graph.add_edge("step9", "step10")
    graph.add_edge("step10", END)

    # Set entry and finish points
    graph.set_entry_point("step4")
    graph.set_finish_point("step10")

    return graph.compile()


# Export compiled graph
post_approval_graph = build_post_approval_graph()
