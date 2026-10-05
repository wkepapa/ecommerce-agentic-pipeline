"""Bundle of shared services handed to every agent."""
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowContext:
    state: Any
    tracer: Any
    metrics: Any
    logger: Any
    executor: Any
    registry: Any
    max_retries: int = 2
    mode: str = "parallel"
