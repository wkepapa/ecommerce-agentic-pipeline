"""Comparison tool: side-by-side table + best-in-class per parameter."""

PARAMETERS = ("price", "ram_gb", "storage_gb", "rating")


def compare_products(products, parameters=PARAMETERS):
    rows = [{"id": p.get("id"), "name": p["name"], "brand": p.get("brand"),
             **{k: p.get(k) for k in parameters}} for p in products]
    best = {}
    for k in parameters:
        vals = [(p.get(k), p["name"]) for p in products if p.get(k) is not None]
        if not vals:
            continue
        best[k] = min(vals, key=lambda x: x[0])[1] if k == "price" else max(vals, key=lambda x: x[0])[1]
    prices = [p["price"] for p in products if p.get("price") is not None]
    summary = {"count": len(products)}
    if prices:
        summary.update({"price_min": min(prices), "price_max": max(prices),
                        "price_avg": round(sum(prices) / len(prices))})
    return {"data": {"rows": rows, "best": best, "summary": summary},
            "ops": len(products) * len(parameters)}
