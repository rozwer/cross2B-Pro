"""Pre-approval LangGraph graph.

Handles steps 0-3 (including parallel 3A/3B/3C) before human approval.
After this graph completes, workflow pauses for approval signal.

Graph flow:
    step0 → step1 → step2 → step3_parallel → END (waiting_approval state)
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

import asyncio
import logging
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

# ===== DEBUG_LOG_START =====
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)
# ===== DEBUG_LOG_END =====

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry
from apps.worker.graphs.wrapper import create_node_function

# ============================================================
# Step Node Functions
# ============================================================


async def step0_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 0: Keyword Selection.

    REVIEW-002: LLMCallMetadata必須化
    """
    # ===== DEBUG_LOG_START =====
    logger.debug(f"[STEP0] Starting step0_execute with state: {state}")
    logger.debug(f"[STEP0] Context: run_id={ctx.run_id}, tenant_id={ctx.tenant_id}")
    # ===== DEBUG_LOG_END =====

    config = ctx.config
    llm = get_llm_client(
        config.get("llm_provider", "gemini"),
        model=config.get("llm_model"),
    )

    # REVIEW-002: LLMCallMetadata を必須で注入
    metadata = LLMCallMetadata(
        run_id=ctx.run_id,
        step_id="step0",
        attempt=ctx.attempt,
        tenant_id=ctx.tenant_id,
    )

    llm_config = LLMRequestConfig(
        max_tokens=config.get("max_tokens", 2000),
        temperature=config.get("temperature", 0.7),
    )
    response = await llm.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a keyword analysis assistant.",
        config=llm_config,
        metadata=metadata,  # REVIEW-002: metadata 必須
    )

    # ===== DEBUG_LOG_START =====
    logger.debug(f"[STEP0] Completed. Model: {response.model}, Tokens: {response.token_usage}")
    # ===== DEBUG_LOG_END =====

    return {
        "step": "step0",
        "keyword": config.get("keyword"),
        "analysis": response.content,
        "model": response.model,
        "usage": {
            "input_tokens": response.token_usage.input,
            "output_tokens": response.token_usage.output,
        },
    }


async def step1_execute(
    prompt: str,
    state: GraphState,
    ctx: ExecutionContext,
) -> dict[str, Any]:
    """Execute step 1: Competitor Fetch."""
    # ===== DEBUG_LOG_START =====
    logger.debug("[STEP1] Starting step1_execute")
    # ===== DEBUG_LOG_END =====

    config = ctx.config
    registry = ToolRegistry()

    # SERP fetch
    serp_tool = registry.get("serp_fetch")
    keyword = config.get("keyword", "")

    if not serp_tool:
        return {"step": "step1", "error": "serp_fetch tool not available", "competitors": []}

    serp_result = await serp_tool.execute(query=keyword, num_results=10)
    urls = serp_result.data.get("urls", []) if serp_result.success and serp_result.data else []

    # Fetch pages
    page_tool = registry.get("page_fetch")
    competitors: list[dict[str, Any]] = []

    if page_tool:
        for url in urls[:5]:  # Limit to top 5
            try:
                result = await page_tool.execute(url=url)
                if result.success and result.data:
                    competitors.append(
                        {
                            "url": url,
                            "title": result.data.get("title", ""),
                            "content": result.data.get("content", "")[:1000],
                        }
                    )
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
    # step1_output will be used for validation once artifact loading is implemented
    _ = state.get("step_outputs", {}).get("step1")  # Mark as future use

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
    keyword_analysis = config.get("keyword_analysis", "")
    competitor_count = config.get("competitor_count", 0)
    competitor_summaries = config.get("competitor_summaries", [])
    competitors = config.get("competitors", [])

    async def run_step3a() -> dict[str, Any]:
        """Step 3A: Query Analysis. REVIEW-002: metadata必須化"""
        llm = get_llm_client("gemini")
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id="step3a",
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )
        try:
            template = prompt_pack.get_prompt("step3a")
            p = template.render(
                keyword=keyword,
                keyword_analysis=keyword_analysis,
                competitor_count=competitor_count,
            )
            llm_config = LLMRequestConfig(max_tokens=3000)
            response = await llm.generate(
                messages=[{"role": "user", "content": p}],
                system_prompt="You are a search query analysis expert.",
                config=llm_config,
                metadata=metadata,  # REVIEW-002: metadata 必須
            )
            return {
                "step": "step3a",
                "analysis": response.content,
                "usage": {
                    "input_tokens": response.token_usage.input,
                    "output_tokens": response.token_usage.output,
                },
            }
        except Exception as e:
            return {"step": "step3a", "error": str(e)}

    async def run_step3b() -> dict[str, Any]:
        """Step 3B: Co-occurrence (heart). REVIEW-002: metadata必須化"""
        llm = get_llm_client("gemini")
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id="step3b",
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )
        try:
            template = prompt_pack.get_prompt("step3b")
            p = template.render(
                keyword=keyword,
                competitor_summaries=competitor_summaries,
            )
            llm_config = LLMRequestConfig(max_tokens=4000)
            response = await llm.generate(
                messages=[{"role": "user", "content": p}],
                system_prompt="You are a co-occurrence keyword analysis expert.",
                config=llm_config,
                metadata=metadata,  # REVIEW-002: metadata 必須
            )
            return {
                "step": "step3b",
                "analysis": response.content,
                "usage": {
                    "input_tokens": response.token_usage.input,
                    "output_tokens": response.token_usage.output,
                },
            }
        except Exception as e:
            return {"step": "step3b", "error": str(e)}

    async def run_step3c() -> dict[str, Any]:
        """Step 3C: Competitor Analysis. REVIEW-002: metadata必須化"""
        llm = get_llm_client("gemini")
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id="step3c",
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )
        try:
            template = prompt_pack.get_prompt("step3c")
            p = template.render(
                keyword=keyword,
                competitors=competitors,
            )
            llm_config = LLMRequestConfig(max_tokens=3000)
            response = await llm.generate(
                messages=[{"role": "user", "content": p}],
                system_prompt="You are a competitor analysis expert.",
                config=llm_config,
                metadata=metadata,  # REVIEW-002: metadata 必須
            )
            return {
                "step": "step3c",
                "analysis": response.content,
                "usage": {
                    "input_tokens": response.token_usage.input,
                    "output_tokens": response.token_usage.output,
                },
            }
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
    def result_or_error(r: Any) -> dict[str, Any]:
        return r if not isinstance(r, Exception) else {"error": str(r)}

    step3a_result = result_or_error(results[0])
    step3b_result = result_or_error(results[1])
    step3c_result = result_or_error(results[2])

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


def build_pre_approval_graph() -> Any:
    """Build the pre-approval LangGraph graph.

    Returns:
        Compiled StateGraph ready for execution
    """
    graph: StateGraph[Any, Any, Any, Any] = StateGraph(GraphState)

    # Create node functions with wrapper
    step0_node = create_node_function("step0", step0_execute)
    step1_node = create_node_function("step1", step1_execute)
    step2_node = create_node_function("step2", step2_execute)
    step3_parallel_node = create_node_function("step3_parallel", step3_parallel_execute)

    # Add nodes
    graph.add_node("step0", step0_node)  # type: ignore[call-overload]
    graph.add_node("step1", step1_node)  # type: ignore[call-overload]
    graph.add_node("step2", step2_node)  # type: ignore[call-overload]
    graph.add_node("step3_parallel", step3_parallel_node)  # type: ignore[call-overload]

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
