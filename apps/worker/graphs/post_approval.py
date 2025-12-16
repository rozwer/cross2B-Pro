"""Post-approval LangGraph graph.

Handles steps 4-10 after human approval.
This graph runs automatically once approval signal is received.

Graph flow:
    step4 → step5 → step6 → step6_5 → step7a → step7b → step8 → step9 → step10 → END
"""

from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry

from .wrapper import create_node_function


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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 4000),
        temperature=config.get("temperature", 0.6),
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
    collector = registry.get_tool("primary_collector")
    sources = []

    if collector:
        from apps.api.tools.schemas import ToolRequest

        queries = [
            f"{keyword} research statistics",
            f"{keyword} official data",
        ]

        for query in queries:
            try:
                request = ToolRequest(
                    tool_id="primary_collector",
                    input_data={"query": query},
                )
                result = await collector.execute(request)
                if result.success:
                    sources.extend(result.output_data.get("evidence_refs", []))
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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 5000),
        temperature=config.get("temperature", 0.6),
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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 6000),
        temperature=config.get("temperature", 0.5),
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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.7),
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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.8),
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

    # Fact check with grounding
    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 4000),
        temperature=0.3,
        grounding=True,
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

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.6),
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
    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=0.3,
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


def build_post_approval_graph() -> StateGraph:
    """Build the post-approval LangGraph graph.

    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(GraphState)

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
    graph.add_node("step4", step4_node)
    graph.add_node("step5", step5_node)
    graph.add_node("step6", step6_node)
    graph.add_node("step6_5", step6_5_node)
    graph.add_node("step7a", step7a_node)
    graph.add_node("step7b", step7b_node)
    graph.add_node("step8", step8_node)
    graph.add_node("step9", step9_node)
    graph.add_node("step10", step10_node)

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
