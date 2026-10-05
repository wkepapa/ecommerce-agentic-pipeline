"""Workflow orchestration: security screen -> plan -> route -> staged execution (parallel where
independent) -> synchronize -> supervise -> human approval -> final recommendation."""
import time

from agents.comparison_agent import ComparisonAgent
from agents.filter_agent import FilterAgent
from agents.planner_agent import PlannerAgent
from agents.ranking_agent import RankingAgent
from agents.router_agent import RouterAgent
from agents.search_agent import SearchAgent
from agents.supervisor_agent import SupervisorAgent
from agents.validator_agent import ValidatorAgent
from config import settings
from core.context import WorkflowContext
from core.exceptions import WorkflowAbort, WorkflowError
from core.logger import WorkflowLogger
from core.metrics import MetricsCollector
from core.state import SharedWorkflowState
from core.tracer import Tracer
from mcp_layer.authorization import ToolAuthorizer
from mcp_layer.executor import MCPToolExecutor
from mcp_layer.registry import ToolRegistry
from mcp_layer.tools import register_all_tools
from mcp_layer.tools.search_tool import FaultInjector
from orchestration.executor import run_tasks
from orchestration.human_approval import HumanApprovalGate
from orchestration.synchronizer import Synchronizer
from security.input_sanitizer import sanitize_query

AGENT_CLASSES = {
    "search_agent": SearchAgent,
    "filter_agent": FilterAgent,
    "comparison_agent": ComparisonAgent,
    "ranking_agent": RankingAgent,
    "validator_agent": ValidatorAgent,
}


def create_context(query, mode="parallel", faults=None, max_retries=None, search_latency=None,
                   tool_timeout=None, verbose=False, write_files=True):
    """Build state + services. Also used directly by the security tests."""
    state = SharedWorkflowState(query)
    metrics = MetricsCollector(settings.COST_UNITS, mode)
    logger = WorkflowLogger(state.workflow_id, settings.LOG_DIR if write_files else None, echo=verbose)
    registry = ToolRegistry()
    register_all_tools(registry, FaultInjector(faults),
                       settings.SEARCH_LATENCY if search_latency is None else search_latency)
    executor = MCPToolExecutor(registry, ToolAuthorizer(), metrics, logger, state, timeout=tool_timeout)
    return WorkflowContext(state=state, tracer=Tracer(state.workflow_id), metrics=metrics, logger=logger,
                           executor=executor, registry=registry,
                           max_retries=settings.MAX_RETRIES if max_retries is None else max_retries,
                           mode=mode)


class ECommerceWorkflow:
    def __init__(self, query, mode="parallel", approval_gate=None, faults=None, max_retries=None,
                 search_latency=None, tool_timeout=None, verbose=False, write_files=True):
        self.mode = mode
        self.ctx = create_context(query, mode, faults, max_retries, search_latency, tool_timeout,
                                  verbose, write_files)
        self.gate = approval_gate or HumanApprovalGate("auto")
        self.supervisor = SupervisorAgent(self.ctx, self.gate)

    # ------------------------------------------------------------------------------
    def run(self):
        ctx, state = self.ctx, self.ctx.state
        ctx.metrics.start()
        state.update("orchestrator", "status", "running")
        try:
            self._security_screen()
            self._plan_and_route()
            attempts = 0
            while True:
                self._execute_stages()
                self._final_review()
                if state.human_approval.get("decision") == "reanalyse" and attempts < settings.MAX_REANALYSIS:
                    attempts += 1
                    ctx.logger.event("INFO", "orchestrator", "reanalysis", "started", attempt=attempts)
                    state.reset_derived()
                    continue
                break
        except WorkflowAbort as exc:
            ctx.logger.event("ERROR", "orchestrator", "workflow", exc.status, reason=str(exc))
            state.append("orchestrator", "errors", {"agent": "orchestrator", "error": str(exc)})
            state.update("orchestrator", "status", exc.status)
        except WorkflowError as exc:
            state.append("orchestrator", "errors", {"agent": "orchestrator", "error": str(exc)})
            state.update("orchestrator", "status", "aborted")
        finally:
            ctx.metrics.stop()
            state.update("orchestrator", "trace", ctx.tracer.to_list())
            state.update("orchestrator", "metrics", ctx.metrics.summary())
            ctx.logger.event("INFO", "orchestrator", "workflow", state.status)
            ctx.logger.close()
            ctx.executor.close()
        return ctx

    # ------------------------------------------------------------------------------
    def _security_screen(self):
        state, ctx = self.ctx.state, self.ctx
        result = sanitize_query(state.user_query)
        state.update("orchestrator", "clean_query", result["clean_query"])
        if result["flagged"]:
            state.record_security_event("prompt_injection_detected", findings=result["findings"])
            ctx.logger.event("SECURITY", "orchestrator", "input_screening", "injection_removed",
                             findings=result["findings"])

    def _plan_and_route(self):
        for agent in (PlannerAgent(self.ctx), RouterAgent(self.ctx)):
            msg = agent.run()
            if msg.status != "success":
                status = "failed_invalid_input" if msg.error_type == "InvalidInputError" else "aborted"
                raise WorkflowAbort(msg.error, status=status)

    def _execute_stages(self):
        ctx, state = self.ctx, self.ctx.state
        tasks = {t["id"]: t for t in state.plan}
        for stage in state.routing["stages"]:
            stage_tasks = [tasks[tid] for tid in stage["tasks"]]
            jobs = []
            for task in stage_tasks:
                agent_cls = AGENT_CLASSES[state.routing["assignments"][task["id"]]]
                agent = agent_cls(ctx, instance=task.get("source"))
                jobs.append((task["id"], lambda a=agent, t=task: a.run(t)))

            t0 = time.perf_counter()
            results = run_tasks(jobs, parallel=(self.mode == "parallel"))
            wall = time.perf_counter() - t0
            ctx.metrics.record_stage(f"stage_{stage['index']}", wall, [d for _, d in results.values()])
            ctx.logger.event("INFO", "orchestrator", f"stage_{stage['index']}", "finished",
                             tasks=stage["tasks"], parallel=stage["parallel"] and self.mode == "parallel",
                             wall_ms=round(wall * 1000, 1))

            if stage["synchronize"]:
                Synchronizer(ctx).run(results, stage_tasks)
            if self.supervisor.on_stage_complete(stage["index"], stage_tasks, results) == "abort":
                raise WorkflowAbort(f"Supervisor aborted the workflow at stage {stage['index']}")

    def _final_review(self):
        msg = self.supervisor.run({"id": "final_review", "type": "supervise"})
        if msg.status != "success":
            raise WorkflowAbort(f"Supervisor failed: {msg.error}")
