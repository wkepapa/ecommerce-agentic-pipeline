"""Search Agent: obtains candidate products from ONE source. Never recommends."""
from agents.base_agent import BaseAgent


class SearchAgent(BaseAgent):
    name = "search_agent"
    next_agent = "synchronizer"

    def execute(self, task):
        source = task["source"]
        products = self.use_tool("search_tool", source=source, category=self.state.requirements["category"])
        self.state.put_item(self.name, "raw_search_results", source, products)
        return f"{len(products)} candidates from {source}"
