"""Planner Agent: understand the query, decompose it, create the execution plan. Uses no tools."""
from agents.base_agent import BaseAgent
from agents.query_parser import parse_requirements
from config import settings
from core.exceptions import InvalidInputError


class PlannerAgent(BaseAgent):
    name = "planner"
    next_agent = "router"

    def execute(self, task):
        s = self.state
        query = s.clean_query if s.clean_query is not None else s.user_query
        req = parse_requirements(query)
        if not req["category"]:
            raise InvalidInputError("Could not identify a product category in the query")
        if all(req[k] is None for k in ("max_budget", "min_ram_gb", "min_storage_gb", "min_rating")):
            raise InvalidInputError("No usable constraints (budget/RAM/storage/rating) found in the query")
        s.update(self.name, "requirements", req)
        plan = self._build_plan()
        s.update(self.name, "plan", plan)
        s.lock_requirements(self.name)               # requirements are now tamper-protected
        return f"{len(plan)} tasks planned; requirements locked: " + ", ".join(
            f"{k}={v}" for k, v in req.items() if v is not None and k != "currency")

    @staticmethod
    def _build_plan():
        plan = [{"id": f"search_{src}", "type": "search", "source": src, "depends_on": []}
                for src in settings.SEARCH_SOURCES]
        plan += [
            {"id": "validate_requirements", "type": "validate", "stage": "requirements", "depends_on": []},
            {"id": "filter", "type": "filter", "depends_on": [f"search_{s}" for s in settings.SEARCH_SOURCES]},
            {"id": "compare", "type": "compare", "depends_on": ["filter"]},
            {"id": "validate_filtering", "type": "validate", "stage": "filtering", "depends_on": ["filter"]},
            {"id": "rank", "type": "rank", "depends_on": ["compare"]},
            {"id": "validate_ranking", "type": "validate", "stage": "ranking", "depends_on": ["rank"]},
        ]
        return plan
