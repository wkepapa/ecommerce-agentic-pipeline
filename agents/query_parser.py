"""Rule-based natural-language -> structured requirements (used by the Planner)."""
import re

CATEGORY_KEYWORDS = {
    "laptop": ("laptop", "laptops", "notebook", "notebooks"),
    "smartphone": ("smartphone", "smartphones", "phone", "phones", "mobile", "mobiles"),
    "tablet": ("tablet", "tablets"),
    "headphone": ("headphone", "headphones", "earphones", "earbuds"),
}

_CURRENCY = r"(?:₹|rs\.?|inr)?\s*"
_NUMBER = r"(\d[\d,]*(?:\.\d+)?)\s*(k|lakhs?|lacs?)?"
_BUDGET_RE = re.compile(
    r"(?:under|below|within|less than|up to|upto|at most|not more than|"
    r"maximum(?: budget)?(?: of)?|max(?: budget)?(?: of)?|budget(?: of| is)?)\s*"
    + _CURRENCY + _NUMBER + r"(?![\d,]|\.\d|\s*(?:gb|tb))", re.I)

_RAM_RES = [re.compile(r"(\d+)\s*(gb|tb)\s*(?:of\s+)?(?:ram|memory)", re.I),
            re.compile(r"(?:ram|memory)\s*(?:of|:|>=|at least|minimum)?\s*(\d+)\s*(gb|tb)", re.I)]
_STORAGE_RES = [re.compile(r"(\d+)\s*(gb|tb)\s*(?:of\s+)?(?:ssd|storage|hdd|rom|nvme)", re.I),
                re.compile(r"(?:ssd|storage|hdd)\s*(?:of|:|>=|at least|minimum)?\s*(\d+)\s*(gb|tb)", re.I)]
_RATING_RES = [re.compile(r"rating\s*(?:of\s*)?(?:above|over|at least|more than|greater than|minimum|>=|>|:)?\s*"
                          r"(\d(?:\.\d+)?)", re.I),
               re.compile(r"(\d(?:\.\d+)?)\s*\+?\s*(?:stars?|rating)", re.I)]


def _to_number(num, suffix):
    value = float(num.replace(",", ""))
    s = (suffix or "").lower()
    if s == "k":
        value *= 1000
    elif s.startswith(("lakh", "lac")):
        value *= 100000
    return int(value) if value == int(value) else value


def _size_gb(num, unit):
    return int(num) * (1024 if unit.lower() == "tb" else 1)


def _first_size(patterns, text):
    for rx in patterns:
        m = rx.search(text)
        if m:
            return _size_gb(m.group(1), m.group(2))
    return None


def parse_requirements(query):
    text = query or ""
    words = re.findall(r"[a-z]+", text.lower())
    category = next((cat for cat, kws in CATEGORY_KEYWORDS.items() if any(w in kws for w in words)), None)

    budget = None
    m = _BUDGET_RE.search(text)
    if m:
        budget = _to_number(m.group(1), m.group(2))

    rating = None
    for rx in _RATING_RES:
        m = rx.search(text)
        if m:
            rating = float(m.group(1))
            break

    return {
        "category": category,
        "max_budget": budget,
        "min_ram_gb": _first_size(_RAM_RES, text),
        "min_storage_gb": _first_size(_STORAGE_RES, text),
        "min_rating": rating,
        "currency": "INR",
    }
