"""Validator Agent: checkpoint validation so invalid output never becomes the recommendation."""
from agents.base_agent import BaseAgent
from config import settings


class ValidatorAgent(BaseAgent):
    name = "validator_agent"
    next_agent = "supervisor_agent"

    def execute(self, task):
        s, stage = self.state, task["stage"]
        result = self.use_tool(
            "validation_tool", stage=stage, requirements=s.requirements,
            integrity_ok=s.verify_requirements_integrity(),
            products=s.filtered_results if stage == "filtering" else None,
            ranking=s.ranking if stage == "ranking" else None,
            filtered=s.filtered_results, require_in_stock=settings.REQUIRE_IN_STOCK)
        s.put_item(self.name, "validation", stage, result)
        verdict = "PASSED" if result["passed"] else "FAILED: " + "; ".join(result["issues"])
        return f"{stage} checkpoint {verdict}"
