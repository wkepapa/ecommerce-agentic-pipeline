"""Controlled tool execution: authorize -> count -> run with timeout -> log."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from config import settings
from core.exceptions import ToolTimeoutError, UnauthorizedToolAccess


class MCPToolExecutor:
    def __init__(self, registry, authorizer, metrics, logger, state, timeout=None):
        self.registry = registry
        self.authorizer = authorizer
        self.metrics = metrics
        self.logger = logger
        self.state = state
        self.timeout = timeout if timeout is not None else settings.TOOL_TIMEOUT
        self._pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="mcp-tool")

    def call(self, agent, tool_name, **kwargs):
        try:
            self.authorizer.check(agent, tool_name)
        except UnauthorizedToolAccess as exc:
            self.logger.event("SECURITY", agent, tool_name, "access_denied", reason=str(exc))
            self.state.record_security_event("unauthorized_tool_access", agent=agent, tool=tool_name)
            raise

        spec = self.registry.get(tool_name)
        self.metrics.count_tool_call()
        self.logger.event("INFO", agent, tool_name, "tool_call")
        future = self._pool.submit(spec.func, **kwargs)
        try:
            output = future.result(timeout=self.timeout)
        except FutureTimeout:
            self.logger.event("ERROR", agent, tool_name, "timeout", timeout=self.timeout)
            raise ToolTimeoutError(f"Tool '{tool_name}' timed out after {self.timeout}s")
        self.metrics.add_ops(output.get("ops", 0))
        return output["data"]

    def close(self):
        self._pool.shutdown(wait=False)
