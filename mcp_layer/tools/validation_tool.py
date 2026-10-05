"""Validation tool: checkpoint validation (requirements -> filtering -> ranking)."""
from mcp_layer.tools.common import check_constraints

CONSTRAINT_KEYS = ("max_budget", "min_ram_gb", "min_storage_gb", "min_rating")


def _group(products, req, require_in_stock):
    """constraint name -> list of offending product names."""
    bad = {}
    for p in products:
        for v in check_constraints(p, req, require_in_stock):
            bad.setdefault(v["constraint"], []).append(p.get("name"))
    return bad


def validate_recommendation(stage, requirements, integrity_ok=True, products=None,
                            ranking=None, filtered=None, require_in_stock=True):
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "passed": bool(ok), "detail": detail})

    if stage == "requirements":
        add("requirements_integrity", integrity_ok, "requirements unchanged since planning")
        add("category_present", bool(requirements.get("category")))
        add("has_constraints", any(requirements.get(k) is not None for k in CONSTRAINT_KEYS))
        b = requirements.get("max_budget")
        add("budget_valid", b is None or b > 0, f"budget={b}")
        r = requirements.get("min_rating")
        add("rating_in_range", r is None or 0 <= r <= 5, f"min_rating={r}")
        ops = 5

    elif stage in ("filtering", "ranking"):
        items = (products if stage == "filtering" else ranking) or []
        bad = _group(items, requirements, require_in_stock)
        add("budget_compliance", "budget" not in bad, ", ".join(bad.get("budget", [])))
        add("ram_requirement", "ram" not in bad, ", ".join(bad.get("ram", [])))
        add("storage_requirement", "storage" not in bad, ", ".join(bad.get("storage", [])))
        add("rating_requirement", "rating" not in bad, ", ".join(bad.get("rating", [])))
        add("information_complete", "missing_information" not in bad,
            ", ".join(bad.get("missing_information", [])))
        add("category_match", "category" not in bad)
        if stage == "ranking":
            scores = [r.get("score") for r in items]
            add("scores_present", all(s is not None for s in scores))
            add("sorted_by_score", all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)))
            add("ranks_sequential", [r.get("rank") for r in items] == list(range(1, len(items) + 1)))
            add("reasoning_present", all(r.get("reasoning") for r in items))
            add("ranking_matches_filtered",
                {r.get("id") for r in items} == {f.get("id") for f in (filtered or [])},
                "ranked set equals filtered set")
        ops = len(items) * 6
    else:
        add("known_stage", False, f"unknown validation stage '{stage}'")
        ops = 0

    issues = [f"{c['name']}: {c['detail']}" for c in checks if not c["passed"]]
    return {"data": {"stage": stage, "passed": not issues, "checks": checks, "issues": issues},
            "ops": ops}
