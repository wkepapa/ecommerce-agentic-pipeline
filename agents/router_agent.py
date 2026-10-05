"""Router Agent: assign each task to a specialised agent and compute dependency-aware stages."""
from agents.base_agent import BaseAgent
from core.exceptions import InvalidInputError

TASK_AGENT_MAP = {
    "search": "search_agent",
    "filter": "filter_agent",
    "compare": "comparison_agent",
    "rank": "ranking_agent",
    "validate": "validator_agent",
}


class RouterAgent(BaseAgent):
    name = "router"
    next_agent = "search_agent"

    def execute(self, task):
        plan = self.state.plan
        ids = {t["id"] for t in plan}
        assignments = {}
        for t in plan:
            if t["type"] not in TASK_AGENT_MAP:
                raise InvalidInputError(f"No agent can handle task type '{t['type']}'")
            for dep in t["depends_on"]:
                if dep not in ids:
                    raise InvalidInputError(f"Task '{t['id']}' depends on unknown task '{dep}'")
            assignments[t["id"]] = TASK_AGENT_MAP[t["type"]]

        # Layer the DAG: tasks whose dependencies are done form one stage (-> can run in parallel).
        by_id = {t["id"]: t for t in plan}
        remaining = {t["id"]: set(t["depends_on"]) for t in plan}
        done, stages = set(), []
        while remaining:
            ready = [tid for tid, deps in remaining.items() if deps <= done]
            if not ready:
                raise InvalidInputError("Cyclic dependency in plan")
            stages.append({
                "index": len(stages), "tasks": ready, "parallel": len(ready) > 1,
                "synchronize": any(by_id[t]["type"] == "search" for t in ready),
            })
            done |= set(ready)
            for tid in ready:
                del remaining[tid]
        self.state.update(self.name, "routing", {"assignments": assignments, "stages": stages})
        return f"{len(assignments)} tasks routed into {len(stages)} stages " \
               f"({sum(s['parallel'] for s in stages)} parallel)"
