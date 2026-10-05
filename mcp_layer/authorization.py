"""Role-based tool authorization (least privilege)."""
from core.exceptions import UnauthorizedToolAccess

ROLE_TOOL_PERMISSIONS = {
    "planner": set(),                              # planning only, no tools
    "router": set(),                               # routing only, no tools
    "search_agent": {"search_tool"},
    "filter_agent": {"filter_tool"},
    "comparison_agent": {"comparison_tool"},
    "ranking_agent": {"ranking_tool"},
    "validator_agent": {"validation_tool"},
    "supervisor_agent": {"workflow_control_tool"},
}


class ToolAuthorizer:
    def __init__(self, permissions=None):
        self.permissions = permissions or ROLE_TOOL_PERMISSIONS

    def is_allowed(self, agent, tool):
        return tool in self.permissions.get(agent, set())

    def check(self, agent, tool):
        if not self.is_allowed(agent, tool):
            raise UnauthorizedToolAccess(f"Agent '{agent}' is not authorized to use tool '{tool}'")
