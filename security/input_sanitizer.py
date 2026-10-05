"""Prompt-injection screening. Suspicious sentences are removed BEFORE planning, so only the
trusted structured requirements ever drive the decision logic."""
import re

INJECTION_PATTERNS = [
    r"\bignore\b.*\b(instruction|requirement|constraint|budget|rule|filter|previous|above)s?\b",
    r"\bdisregard\b",
    r"\bforget\b.*\b(everything|budget|previous|instruction|rule)s?\b",
    r"\b(recommend|show|pick|choose|select)\b.*\bmost expensive\b",
    r"\boverride\b",
    r"\bbypass\b",
    r"\bsystem prompt\b",
    r"\byou are now\b",
    r"\bact as\b",
    r"\bjailbreak\b",
    r"\breveal\b.*\b(prompt|tool|instruction|key)s?\b",
]
_COMPILED = [re.compile(p, re.I) for p in INJECTION_PATTERNS]
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n")


def sanitize_query(query):
    kept, findings = [], []
    for sentence in _SENTENCE_SPLIT.split(query or ""):
        if not sentence.strip():
            continue
        hit = next((rx.pattern for rx in _COMPILED if rx.search(sentence)), None)
        if hit:
            findings.append({"pattern": hit, "removed_text": sentence.strip()})
        else:
            kept.append(sentence.strip())
    return {"clean_query": " ".join(kept), "flagged": bool(findings), "findings": findings}
