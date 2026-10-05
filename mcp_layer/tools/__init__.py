"""Registers every tool with the MCP-style registry (tool registration)."""
from mcp_layer.tools.search_tool import FaultInjector, make_search_tool
from mcp_layer.tools.filter_tool import filter_products
from mcp_layer.tools.comparison_tool import compare_products
from mcp_layer.tools.ranking_tool import rank_products
from mcp_layer.tools.validation_tool import validate_recommendation
from mcp_layer.tools.workflow_control_tool import assess_workflow


def register_all_tools(registry, fault_injector, search_latency):
    registry.register("search_tool", make_search_tool(fault_injector, search_latency),
                      "Search one product source and return candidate products",
                      {"source": "str", "category": "str|None"})
    registry.register("filter_tool", filter_products,
                      "Remove products that violate the structured requirements",
                      {"products": "list", "requirements": "dict", "require_in_stock": "bool"})
    registry.register("comparison_tool", compare_products,
                      "Compare filtered products across price/RAM/storage/rating",
                      {"products": "list"})
    registry.register("ranking_tool", rank_products,
                      "Score and sort products with explainable, requirement-aware scoring",
                      {"products": "list", "requirements": "dict", "weights": "dict"})
    registry.register("validation_tool", validate_recommendation,
                      "Validate requirements / filtered / ranked output at a checkpoint",
                      {"stage": "str", "requirements": "dict"})
    registry.register("workflow_control_tool", assess_workflow,
                      "Assess workflow health for the Supervisor",
                      {"statuses": "list", "validation": "dict", "conflicts": "list"})
