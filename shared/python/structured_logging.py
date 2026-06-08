"""
STAR
Situation: Distributed jobs are difficult to debug when logs are inconsistent.
Task: Standardize log fields across AWS, Azure, GCP, OCI, and local jobs.
Action: Create a small structured logger factory with pipeline metadata.
Result: Pipeline logs can be indexed and filtered by cloud, job name, run id, and stage.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pythonjsonlogger import jsonlogger


@dataclass(frozen=True)
class PipelineContext:
    cloud: str
    pipeline: str
    run_id: str
    environment: str = "local"


def get_logger(context: PipelineContext) -> logging.LoggerAdapter:
    """Return a JSON logger adapter with stable pipeline fields."""
    logger = logging.getLogger(context.pipeline)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(cloud)s %(pipeline)s %(run_id)s %(environment)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logging.LoggerAdapter(
        logger,
        {
            "cloud": context.cloud,
            "pipeline": context.pipeline,
            "run_id": context.run_id,
            "environment": context.environment,
        },
    )
