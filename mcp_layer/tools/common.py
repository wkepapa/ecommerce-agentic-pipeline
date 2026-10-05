"""Shared constraint checking used by the filter tool and the validation tool."""

# constraint name -> (requirement key, product field, "max"|"min")
CONSTRAINT_SPECS = {
    "budget": ("max_budget", "price", "max"),
    "ram": ("min_ram_gb", "ram_gb", "min"),
    "storage": ("min_storage_gb", "storage_gb", "min"),
    "rating": ("min_rating", "rating", "min"),
}


def check_constraints(product, req, require_in_stock=False):
    """Return a list of violations: [{"constraint": str, "reason": str}]."""
    violations = []
    category = req.get("category")
    if category and str(product.get("category", "")).lower() != category:
        violations.append({"constraint": "category",
                           "reason": f"category '{product.get('category')}' != '{category}'"})
    for cname, (rkey, pfield, op) in CONSTRAINT_SPECS.items():
        limit = req.get(rkey)
        if limit is None:
            continue
        value = product.get(pfield)
        if value is None:
            violations.append({"constraint": "missing_information", "reason": f"missing {pfield}"})
            continue
        ok = value <= limit if op == "max" else value >= limit
        if not ok:
            violations.append({"constraint": cname, "reason": f"{pfield} {value} violates {rkey}={limit}"})
    if require_in_stock and product.get("in_stock") is False:
        violations.append({"constraint": "availability", "reason": "out of stock"})
    return violations
