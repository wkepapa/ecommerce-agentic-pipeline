"""Structured inter-agent message: Agent -> Task -> Input -> Output -> Status."""
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    task: str
    status: str                      # "success" | "failed"
    input_summary: str = ""
    output_summary: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    retries: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)
