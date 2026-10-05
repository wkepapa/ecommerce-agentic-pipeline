"""Synchronization barrier: wait for ALL parallel search agents, then merge + resolve conflicts."""
from core.exceptions import WorkflowAbort
from orchestration.conflict_resolver import resolve_conflicts


class Synchronizer:
    name = "synchronizer"

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self, stage_results, stage_tasks):
        ctx, state = self.ctx, self.ctx.state
        span = ctx.tracer.start(self.name, "synchronize_search")
        search_tasks = [t for t in stage_tasks if t["type"] == "search"]
        ok = [t["source"] for t in search_tasks if stage_results[t["id"]][0].status == "success"]
        failed = [t["source"] for t in search_tasks if stage_results[t["id"]][0].status != "success"]
        ctx.logger.event("INFO", self.name, "barrier", "reached", ok_sources=ok, failed_sources=failed)

        if not ok:
            ctx.tracer.end(span, "failed", error="all search sources failed")
            raise WorkflowAbort("All search sources failed - nothing to synchronize")

        merged, conflicts = resolve_conflicts({s: state.raw_search_results[s] for s in ok})
        state.update(self.name, "search_results", merged)
        state.update(self.name, "conflicts", conflicts)
        for src in failed:
            state.append(self.name, "errors", {"agent": self.name, "task": f"search_{src}",
                                               "error": f"source '{src}' unavailable - continuing degraded"})
        ctx.metrics.add_ops(sum(len(v) for v in state.raw_search_results.values()))
        high = sum(c["severity"] == "high" for c in conflicts)
        ctx.tracer.end(span, "success", tools=[],
                       output=f"{len(ok)}/{len(search_tasks)} sources merged -> {len(merged)} unique products, "
                              f"{len(conflicts)} conflicts ({high} high)")
        return merged
