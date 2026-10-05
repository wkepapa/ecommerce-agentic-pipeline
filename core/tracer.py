"""Execution tracer: who ran, when, which task, tools used, retries, outcome."""
import threading
import time
from datetime import datetime


def _fmt(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3] if ts else "-"


class Tracer:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self._spans = []
        self._seq = 0
        self._lock = threading.Lock()

    def start(self, agent, task, instance=None):
        with self._lock:
            self._seq += 1
            span = {
                "seq": self._seq, "agent": agent, "instance": instance, "task": task,
                "start": time.time(), "end": None, "duration_ms": None,
                "status": "running", "tools": [], "retries": 0, "error": None,
                "output": None, "thread": threading.current_thread().name,
            }
            self._spans.append(span)
            return span

    def end(self, span, status, retries=0, error=None, tools=None, output=None):
        with self._lock:
            span["end"] = time.time()
            span["duration_ms"] = round((span["end"] - span["start"]) * 1000, 1)
            span["status"] = status
            span["retries"] = retries
            span["error"] = error
            span["tools"] = list(tools or [])
            span["output"] = output

    def to_list(self):
        with self._lock:
            out = []
            for s in sorted(self._spans, key=lambda x: x["start"]):
                c = dict(s)
                c["start"], c["end"] = _fmt(s["start"]), _fmt(s["end"])
                out.append(c)
            return out

    def flow(self):
        seen, order = set(), []
        for s in sorted(self._spans, key=lambda x: x["start"]):
            if s["agent"] not in seen:
                seen.add(s["agent"])
                order.append(s["agent"])
        return " -> ".join(order)

    def render_text(self):
        lines = [f"{'#':>3}  {'start':<12} {'agent':<30} {'task':<24} {'ms':>8}  {'status':<8} tools / retries"]
        for i, s in enumerate(self.to_list(), 1):
            name = s["agent"] + (f"[{s['instance']}]" if s["instance"] else "")
            tools = ",".join(s["tools"]) or "-"
            lines.append(f"{i:>3}  {s['start']:<12} {name:<30} {str(s['task']):<24} "
                         f"{s['duration_ms'] or 0:>8}  {s['status']:<8} {tools} / r={s['retries']}")
            if s["error"]:
                lines.append(f"       ERROR: {s['error']}")
        return "\n".join(lines)
