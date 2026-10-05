"""Filter Agent: removes products that violate the user's constraints."""
from agents.base_agent import BaseAgent
from config import settings


class FilterAgent(BaseAgent):
    name = "filter_agent"
    next_agent = "comparison_agent"

    def execute(self, task):
        s = self.state
        out = self.use_tool("filter_tool", products=s.search_results, requirements=s.requirements,
                            require_in_stock=settings.REQUIRE_IN_STOCK)
        s.update(self.name, "filtered_results", out["passed"])
        s.update(self.name, "rejected_results", out["rejected"])
        return f"{len(out['passed'])} passed, {len(out['rejected'])} rejected of {len(s.search_results)}"
