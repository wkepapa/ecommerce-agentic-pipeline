"""Filter tool: constraint-based decision making."""
from mcp_layer.tools.common import check_constraints


def filter_products(products, requirements, require_in_stock=True):
    passed, rejected = [], []
    for p in products:
        violations = check_constraints(p, requirements, require_in_stock)
        if violations:
            rejected.append({**p, "rejection_reasons": [v["reason"] for v in violations]})
        else:
            passed.append(dict(p))
    return {"data": {"passed": passed, "rejected": rejected}, "ops": len(products)}
