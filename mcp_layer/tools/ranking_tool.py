"""Ranking tool: requirement-aware, fully explainable scoring.

Each factor gets a 0..1 sub-score based on HEADROOM over the user's requirement:
  price   : 0 at the budget, 1 when 40% (or more) below the budget
  ram     : 0.5 when exactly at the minimum, 1.0 at 2x the minimum
  storage : 0.5 when exactly at the minimum, 1.0 at 2x the minimum
  rating  : 0 at the minimum rating, 1 at 5.0
score = 100 * sum(weight * sub_score) / sum(weights)
"""


def _clamp(x):
    return max(0.0, min(1.0, x))


def _sub_scores(p, req, max_price):
    budget = req.get("max_budget") or max_price
    ram_min, sto_min, rat_min = req.get("min_ram_gb"), req.get("min_storage_gb"), req.get("min_rating")
    return {
        "price": _clamp((budget - p["price"]) / (0.4 * budget)),
        "ram": _clamp(p["ram_gb"] / (2 * ram_min)) if ram_min else _clamp(p["ram_gb"] / 32),
        "storage": _clamp(p["storage_gb"] / (2 * sto_min)) if sto_min else _clamp(p["storage_gb"] / 1024),
        "rating": _clamp((p["rating"] - rat_min) / (5 - rat_min)) if rat_min is not None and rat_min < 5
        else _clamp(p["rating"] / 5),
    }


def _reasoning(p, req, sub, rank, score):
    budget = req.get("max_budget")
    parts = []
    if budget:
        pct = (budget - p["price"]) / budget * 100
        parts.append(f"price ₹{p['price']:,.0f} is {pct:.1f}% below the ₹{budget:,.0f} budget")
    else:
        parts.append(f"price ₹{p['price']:,.0f}")
    ram_min, sto_min, rat_min = req.get("min_ram_gb"), req.get("min_storage_gb"), req.get("min_rating")
    parts.append(f"RAM {p['ram_gb']} GB" + (f" (min {ram_min} GB)" if ram_min else ""))
    parts.append(f"storage {p['storage_gb']} GB" + (f" (min {sto_min} GB)" if sto_min else ""))
    parts.append(f"rating {p['rating']}" + (f" (min {rat_min})" if rat_min is not None else ""))
    strongest = max(sub, key=sub.get)
    return f"Rank #{rank} (score {score:.1f}/100): " + "; ".join(parts) + f". Strongest factor: {strongest}."


def rank_products(products, requirements, weights):
    if not products:
        return {"data": [], "ops": 0}
    total_w = sum(weights.values())
    max_price = max(p["price"] for p in products)
    ranked = []
    for p in products:
        sub = _sub_scores(p, requirements, max_price)
        breakdown = {k: round(weights[k] * sub[k] * 100 / total_w, 1) for k in weights}
        score = round(sum(weights[k] * sub[k] for k in weights) * 100 / total_w, 1)
        ranked.append({**p, "score": score, "breakdown": breakdown, "_sub": sub})
    ranked.sort(key=lambda r: (-r["score"], r["price"], -r["rating"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
        r["reasoning"] = _reasoning(r, requirements, r.pop("_sub"), i, r["score"])
    return {"data": ranked, "ops": len(products) * len(weights)}
