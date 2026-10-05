"""Structured (JSON-lines) workflow logger. Thread-safe."""
import json
import threading
from datetime import datetime
from pathlib import Path


class WorkflowLogger:
    def __init__(self, workflow_id, log_dir=None, echo=False):
        self.workflow_id = workflow_id
        self.echo = echo
        self.entries = []
        self._lock = threading.Lock()
        self._fh = None
        self.path = None
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            self.path = Path(log_dir) / f"workflow_{workflow_id}.jsonl"
            self._fh = open(self.path, "a", encoding="utf-8")

    def event(self, level, agent, task, status, **details):
        entry = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "workflow_id": self.workflow_id,
            "level": level,
            "agent": agent,
            "task": task,
            "status": status,
            "details": details,
        }
        with self._lock:
            self.entries.append(entry)
            if self._fh:
                self._fh.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
                self._fh.flush()
        if self.echo:
            print(f"[{level:<8}] {agent:<28} {str(task):<26} {status}")

    def close(self):
        with self._lock:
            if self._fh:
                self._fh.close()
                self._fh = None
