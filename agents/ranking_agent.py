"""Ranking Agent: transparent scoring + sorting."""
from agents.base_agent import BaseAgent
from config import settings


class RankingAgent(BaseAgent):
    name = "ranking_agent"
    next_agent = "validator_agent"

    def execute(self, task):
        s = self.state
        ranked = self.use_tool("ranking_tool", products=s.filtered_results,
                               requirements=s.requirements, weights=settings.RANKING_WEIGHTS)
        s.update(self.name, "ranking", ranked)
        top = ranked[0]["name"] if ranked else "n/a"
        return f"ranked {len(ranked)} products; top = {top}"
