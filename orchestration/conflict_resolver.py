"""Conflict resolution: never blindly pick a value. Merge by product, resolve by trusted-source
priority, record every conflict with a severity so Validator/Supervisor/Human can review it."""
from config import settings

FIELDS = ("price", "ram_gb", "storage_gb", "rating", "in_stock")


def _key(p):
    return p.get("id") or p.get("name", "").strip().lower()


def _severity(field, values):
    values = list(values)
    if isinstance(values[0], bool):
        return "high"
    lo, hi = min(values), max(values)
    if field == "rating":
        return "high" if hi - lo >= 0.2 else "low"
    return "high" if hi and (hi - lo) / hi > 0.05 else "low"


def resolve_conflicts(results_by_source, priority=None):
    priority = priority or settings.TRUSTED_SOURCE_PRIORITY
    order = [s for s in priority if s in results_by_source] + \
            [s for s in results_by_source if s not in priority]

    grouped = {}                                   # product key -> {source: record}
    for source in order:
        for rec in results_by_source[source]:
            grouped.setdefault(_key(rec), {}).setdefault(source, rec)

    merged, conflicts = [], []
    for key, by_src in grouped.items():
        first = next(s for s in order if s in by_src)
        product = dict(by_src[first])
        product["sources"] = [s for s in order if s in by_src]
        product.pop("source", None)
        for field in FIELDS:
            present = {s: by_src[s].get(field) for s in product["sources"] if by_src[s].get(field) is not None}
            if not present:
                product[field] = None
                continue
            if len(set(present.values())) == 1:
                product[field] = next(iter(present.values()))
                continue
            chosen_source = next(s for s in order if s in present)
            product[field] = present[chosen_source]
            conflicts.append({
                "product_id": product.get("id"), "product": product.get("name"), "field": field,
                "values": present, "resolved_value": present[chosen_source],
                "resolved_by": f"trusted_priority:{chosen_source}",
                "severity": _severity(field, present.values()),
            })
        merged.append(product)
    return merged, conflicts
