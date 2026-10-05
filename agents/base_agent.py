"""Base class: tracing, logging, metrics, messaging and controlled retry for every agent."""
import time

from core.exceptions import WorkflowError
from core.messages import AgentMessage
from core.retry import run_with_retry


class BaseAgent:
    name = "base_agent"
    next_agent = "supervisor_agent"

    def __init__(self, ctx, instance=None):
        self.ctx = ctx
        self.state = ctx.state
        self.instance = instance
        self._tools_used = []

    @property
    def label(self):
        return f"{self.name}[{self.instance}]" if self.instance else self.name

    def use_tool(self, tool_name, **kwargs):
        """Only way an agent touches a tool -> always authorized + counted + logged."""
        self._tools_used.append(tool_name)
        return self.ctx.executor.call(self.name, tool_name, **kwargs)

    def execute(self, task):
        """Return a one-line output summary. Subclasses implement this."""
        raise NotImplementedError

    def run(self, task=None):
        task = task or {"id": self.name, "type": "run"}
        ctx, task_id = self.ctx, task.get("id")
        ctx.metrics.count_agent_call()
        span = ctx.tracer.start(self.name, task_id, self.instance)
        ctx.logger.event("INFO", self.label, task_id, "started")
        started = time.perf_counter()
        retry_count = {"n": 0}

        def on_retry(attempt, exc):
            retry_count["n"] = attempt
            ctx.metrics.count_retry()
            ctx.logger.event("WARNING", self.label, task_id, "retry", attempt=attempt, error=str(exc))

        summary, error, error_type, status = "", None, None, "success"
        try:
            summary, _ = run_with_retry(lambda: self.execute(task), ctx.max_retries, on_retry)
        except WorkflowError as exc:
            status, error, error_type = "failed", str(exc), type(exc).__name__
            retry_count["n"] = getattr(exc, "attempts", retry_count["n"])
        except Exception as exc:                      # unexpected bug -> treated as non-recoverable
            status, error, error_type = "failed", f"{type(exc).__name__}: {exc}", "UnexpectedError"

        duration = time.perf_counter() - started
        ctx.metrics.record_agent_time(self.label, duration)
        ctx.tracer.end(span, status, retries=retry_count["n"], error=error,
                       tools=self._tools_used, output=summary or None)
        ctx.logger.event("INFO" if status == "success" else "ERROR", self.label, task_id, status,
                         duration_ms=round(duration * 1000, 1), retries=retry_count["n"], error=error)
        if error:
            self.state.append(self.name, "errors", {"agent": self.label, "task": task_id,
                                                    "error_type": error_type, "error": error})
        msg = AgentMessage(sender=self.label, receiver=self.next_agent, task=str(task_id), status=status,
                           input_summary=task.get("type", ""), output_summary=summary,
                           error=error, error_type=error_type, retries=retry_count["n"])
        self.state.append(self.name, "messages", msg.to_dict())
        return msg
