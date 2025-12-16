"""Pre-approval LangGraph graph.

Handles steps 0-3 (including parallel 3A/3B/3C) before human approval.
After this graph completes, workflow pauses for approval signal.

Graph flow:
    step0 → step1 → step2 → step3_parallel → END (waiting_approval state)
"""

import asyncio
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry

from .wrapper import create_node_function, step_wrapper


# ============================================================
# Step Node Functions
# ============================================================


async def step0_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 0: Keyword Selection."""
    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "gemini"),
        model=config.get("llm_model"),
    )

    response = await llm.generate(
        prompt=prompt,
        max_tokens=config.get("max_tokens", 2000),
        temperature=config.get("temperature", 0.7),
    )

    return {
        "step": "step0",
        "keyword": config.get("keyword"),
        "analysis": response.content,
        "model": response.model,
    }


async def step1_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 1: Competitor Fetch."""
    config = ctx.config
    registry = ToolRegistry()

    # SERP fetch
    serp_tool = registry.get_tool("serp_fetch")
    keyword = config.get("keyword", "")

    if not serp_tool:
        return {"step": "step1", "error": "serp_fetch tool not available", "competitors": []}

    from apps.api.tools.schemas import ToolRequest

    serp_request = ToolRequest(
        tool_id="serp_fetch",
        input_data={"query": keyword, "num_results": 10},
    )
    serp_result = await serp_tool.execute(serp_request)
    urls = serp_result.output_data.get("urls", []) if serp_result.success else []

    # Fetch pages
    page_tool = registry.get_tool("page_fetch")
    competitors = []

    if page_tool:
        for url in urls[:5]:  # Limit to top 5
            try:
                fetch_request = ToolRequest(
                    tool_id="page_fetch",
                    input_data={"url": url},
                )
                result = await page_tool.execute(fetch_request)
                if result.success:
                    competitors.append({
                        "url": url,
                        "title": result.output_data.get("title", ""),
                        "content": result.output_data.get("content", "")[:1000],
                    })
            except Exception:
                continue

    return {
        "step": "step1",
        "keyword": keyword,
        "competitors": competitors,
        "total_urls": len(urls),
    }


async def step2_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 2: CSV Validation."""
    step1_output = state.get("step_outputs", {}).get("step1")

    # In a real implementation, we'd load the artifact content
    # For now, mark as validated
    return {
        "step": "step2",
        "is_valid": True,
        "validated_at": datetime.now().isoformat(),
    }


async def step3_parallel_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 3 parallel tasks (3A, 3B, 3C)."""
    config = ctx.config
    loader = PromptPackLoader()
    pack_id = config.get("pack_id")

    if not pack_id:
        return {"step": "step3_parallel", "error": "pack_id required"}

    prompt_pack = loader.load(pack_id)
    keyword = config.get("keyword", "")

    async def run_step3a() -> dict[str, Any]:
        """Step 3A: Query Analysis."""
        llm = get_llm_client("gemini")
        try:
            template = prompt_pack.get_prompt("step3a")
            p = template.render(keyword=keyword, keyword_analysis="", competitor_count=0)
            response = await llm.generate(prompt=p, max_tokens=3000)
            return {"step": "step3a", "analysis": response.content}
        except Exception as e:
            return {"step": "step3a", "error": str(e)}

    async def run_step3b() -> dict[str, Any]:
        """Step 3B: Co-occurrence (heart)."""
        llm = get_llm_client("gemini")
        try:
            template = prompt_pack.get_prompt("step3b")
            p = template.render(keyword=keyword, competitor_summaries=[])
            response = await llm.generate(prompt=p, max_tokens=4000, grounding=True)
            return {"step": "step3b", "analysis": response.content}
        except Exception as e:
            return {"step": "step3b", "error": str(e)}

    async def run_step3c() -> dict[str, Any]:
        """Step 3C: Competitor Analysis."""
        llm = get_llm_client("gemini")
        try:
            template = prompt_pack.get_prompt("step3c")
            p = template.render(keyword=keyword, competitors=[])
            response = await llm.generate(prompt=p, max_tokens=3000)
            return {"step": "step3c", "analysis": response.content}
        except Exception as e:
            return {"step": "step3c", "error": str(e)}

    # Run all three in parallel
    results = await asyncio.gather(
        run_step3a(),
        run_step3b(),
        run_step3c(),
        return_exceptions=True,
    )

    # Process results
    step3a_result = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
    step3b_result = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
    step3c_result = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}

    # Check for failures
    failures = []
    if "error" in step3a_result:
        failures.append("step3a")
    if "error" in step3b_result:
        failures.append("step3b")
    if "error" in step3c_result:
        failures.append("step3c")

    return {
        "step": "step3_parallel",
        "step3a": step3a_result,
        "step3b": step3b_result,
        "step3c": step3c_result,
        "all_succeeded": len(failures) == 0,
        "failures": failures,
    }


# ============================================================
# Graph Builder
# ============================================================


def build_pre_approval_graph() -> StateGraph:
    """Build the pre-approval LangGraph graph.

    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(GraphState)

    # Create node functions with wrapper
    step0_node = create_node_function("step0", step0_execute)
    step1_node = create_node_function("step1", step1_execute)
    step2_node = create_node_function("step2", step2_execute)
    step3_parallel_node = create_node_function("step3_parallel", step3_parallel_execute)

    # Add nodes
    graph.add_node("step0", step0_node)
    graph.add_node("step1", step1_node)
    graph.add_node("step2", step2_node)
    graph.add_node("step3_parallel", step3_parallel_node)

    # Add edges (linear flow)
    graph.add_edge(START, "step0")
    graph.add_edge("step0", "step1")
    graph.add_edge("step1", "step2")
    graph.add_edge("step2", "step3_parallel")
    graph.add_edge("step3_parallel", END)

    # Set entry and finish points
    graph.set_entry_point("step0")
    graph.set_finish_point("step3_parallel")

    return graph.compile()


# Export compiled graph
pre_approval_graph = build_pre_approval_graph()
