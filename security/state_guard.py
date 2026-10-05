"""Write-permission table for the shared workflow state (least privilege for state)."""
from core.exceptions import UnauthorizedStateWrite

COMMON_KEYS = {"messages", "errors"}

WRITE_PERMISSIONS = {
    "orchestrator":     {"clean_query", "status", "trace", "metrics"},
    "planner":          {"requirements", "plan"},
    "router":           {"routing"},
    "search_agent":     {"raw_search_results"},
    "synchronizer":     {"search_results", "conflicts"},
    "filter_agent":     {"filtered_results", "rejected_results"},
    "comparison_agent": {"comparison"},
    "ranking_agent":    {"ranking"},
    "validator_agent":  {"validation"},
    "supervisor_agent": {"human_approval", "final_recommendation", "status"},
}


class StateGuard:
    @staticmethod
    def check_write(writer, key, locked_keys):
        allowed = WRITE_PERMISSIONS.get(writer)
        if allowed is None:
            raise UnauthorizedStateWrite(f"Unknown writer '{writer}' may not modify shared state")
        if key in locked_keys:
            raise UnauthorizedStateWrite(f"'{key}' is locked; '{writer}' cannot modify it")
        if key not in allowed and key not in COMMON_KEYS:
            raise UnauthorizedStateWrite(f"'{writer}' is not permitted to write '{key}'")
