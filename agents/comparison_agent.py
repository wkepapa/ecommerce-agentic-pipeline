"""Comparison Agent: compares products that passed filtering."""
from agents.base_agent import BaseAgent


class ComparisonAgent(BaseAgent):
    name = "comparison_agent"
    next_agent = "ranking_agent"

    def execute(self, task):
        result = self.use_tool("comparison_tool", products=self.state.filtered_results)
        self.state.update(self.name, "comparison", result)
        return f"compared {result['summary']['count']} products"
