"""Temporal Worker entry point.

Starts the Temporal worker with all registered workflows and activities.
Worker connects to Temporal server and executes article generation workflows.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import NoReturn

from temporalio.client import Client
from temporalio.worker import Worker

# Workflow and Activity imports
from .activities import (
    step0_keyword_selection,
    step1_competitor_fetch,
    step2_csv_validation,
    step3a_query_analysis,
    step3b_cooccurrence_extraction,
    step3c_competitor_analysis,
    step4_strategic_outline,
    step5_primary_collection,
    step6_5_integration_package,
    step6_enhanced_outline,
    step7a_draft_generation,
    step7b_brush_up,
    step8_fact_check,
    step9_final_rewrite,
    step10_final_output,
)
from .workflows import ArticleWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Configuration from environment
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost")
TEMPORAL_PORT = os.getenv("TEMPORAL_PORT", "7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "seo-article-generation")

# All activities to register
ACTIVITIES = [
    step0_keyword_selection,
    step1_competitor_fetch,
    step2_csv_validation,
    step3a_query_analysis,
    step3b_cooccurrence_extraction,
    step3c_competitor_analysis,
    step4_strategic_outline,
    step5_primary_collection,
    step6_enhanced_outline,
    step6_5_integration_package,
    step7a_draft_generation,
    step7b_brush_up,
    step8_fact_check,
    step9_final_rewrite,
    step10_final_output,
]

# All workflows to register
WORKFLOWS = [
    ArticleWorkflow,
]


async def create_temporal_client() -> Client:
    """Create and return a Temporal client.

    Returns:
        Connected Temporal Client

    Raises:
        Exception: If connection fails
    """
    temporal_address = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
    logger.info(f"Connecting to Temporal at {temporal_address}")

    client = await Client.connect(
        temporal_address,
        namespace=TEMPORAL_NAMESPACE,
    )

    logger.info(f"Connected to Temporal namespace '{TEMPORAL_NAMESPACE}'")
    return client


async def run_worker() -> None:
    """Run the Temporal worker.

    Connects to Temporal and starts processing workflows and activities.
    Handles graceful shutdown on SIGTERM/SIGINT.
    """
    client = await create_temporal_client()

    # Create worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
    )

    logger.info(f"Starting worker on task queue '{TASK_QUEUE}'")
    logger.info(f"Registered workflows: {[w.__name__ for w in WORKFLOWS]}")
    logger.info(f"Registered activities: {[a.__name__ for a in ACTIVITIES]}")

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}, shutting down...")
        shutdown_event.set()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler, sig)

    # Run worker until shutdown
    async with worker:
        logger.info("Worker is running. Press Ctrl+C to stop.")
        await shutdown_event.wait()

    logger.info("Worker shutdown complete")


def main() -> NoReturn:
    """Entry point for the worker."""
    logger.info("=" * 60)
    logger.info("SEO Article Generation - Temporal Worker")
    logger.info("=" * 60)

    # Validate required environment variables
    required_env: list[str] = []
    missing = [var for var in required_env if not os.getenv(var)]

    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)

    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  TEMPORAL_HOST: {TEMPORAL_HOST}")
    logger.info(f"  TEMPORAL_PORT: {TEMPORAL_PORT}")
    logger.info(f"  TEMPORAL_NAMESPACE: {TEMPORAL_NAMESPACE}")
    logger.info(f"  TASK_QUEUE: {TASK_QUEUE}")

    # Run worker
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
