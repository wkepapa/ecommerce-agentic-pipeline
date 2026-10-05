"""Supervisor Agent: monitors the workflow, handles failures, coordinates the final decision
and escalates to a human."""
from agents.base_agent import BaseAgent
from config import settings


class SupervisorAgent(BaseAgent):
    name = "supervisor_agent"
    next_agent = "human"

    def __init__(self, ctx, approval_gate, instance=None):
        super().__init__(ctx, instance)
        self.gate = approval_gate

    # ---- continuous monitoring (called by the orchestrator after every stage) -----------
    def on_stage_complete(self, stage_index, stage_tasks, results):
        log = self.ctx.logger
        for task in stage_tasks:
            msg, _duration = results[task["id"]]
            if msg.status != "success":
                if task["type"] == "search":
                    log.event("WARNING", self.name, task["id"], "degraded_continue",
                              note="search source failed; continuing with remaining sources")
                    continue
                log.event("ERROR", self.name, task["id"], "abort", reason=msg.error)
                self.state.append(self.name, "errors", {"agent": self.name, "task": task["id"],
                                                        "error": f"critical task failed: {msg.error}"})
                return "abort"
            if task["type"] == "validate":
                res = self.state.validation.get(task["stage"])
                if res and not res["passed"]:
                    log.event("ERROR", self.name, task["id"], "abort", reason=res["issues"])
                    self.state.append(self.name, "errors", {
                        "agent": self.name, "task": task["id"],
                        "error": f"{task['stage']} validation failed: {res['issues']}"})
                    return "abort"
        return "continue"

    # ---- final decision stage ----------------------------------------------------
    def execute(self, task):
        s = self.state
        statuses = [{"sender": m["sender"], "task": m["task"], "status": m["status"]}
                    for m in s.messages if not m["sender"].startswith(self.name)]
        assessment = self.use_tool("workflow_control_tool", statuses=statuses,
                                   validation=s.validation, conflicts=s.conflicts)

        if not s.ranking:
            s.update(self.name, "human_approval",
                     {"decision": "not_required", "comment": "no product satisfied the requirements"})
            s.update(self.name, "final_recommendation",
                     {"status": "no_results", "message": "No products satisfy all requirements."})
            s.update(self.name, "status", "no_results")
            return "no products to recommend"

        context = {
            "requirements": s.requirements,
            "ranking": s.ranking[:settings.TOP_N],
            "validation": {k: v["passed"] for k, v in s.validation.items()},
            "escalation_reasons": assessment["escalation_reasons"],
            "conflicts": s.conflicts,
        }
        decision = self.gate.request(context)
        s.update(self.name, "human_approval", decision)

        outcome = {"approve": ("completed", "approved"),
                   "reject": ("rejected_by_human", "withheld"),
                   "flag": ("flagged_by_human", "withheld"),
                   "reanalyse": ("reanalysis_requested", "pending")}[decision["decision"]]
        final = {"status": outcome[1], "human_decision": decision["decision"],
                 "validation_passed": assessment["validation_ok"],
                 "notes": assessment["escalation_reasons"]}
        if outcome[1] == "approved":
            final.update({"top_pick": s.ranking[0], "ranked_products": s.ranking[:settings.TOP_N],
                          "selection_reasoning": s.ranking[0]["reasoning"]})
        s.update(self.name, "final_recommendation", final)
        s.update(self.name, "status", outcome[0])
        return f"human decision = {decision['decision']} -> workflow {outcome[0]}"
