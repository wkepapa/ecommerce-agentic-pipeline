"""Builds the 'Expected Final Result' report: ranking, reasoning, validation, trace,
communication records, metrics, cost, security results, human approval."""
import json

from config import settings


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def build_report(ctx, security_results=None):
    s, m = ctx.state, ctx.metrics.summary()
    req = {k: v for k, v in s.requirements.items() if v is not None}
    L = ["# Multi-Agent E-Commerce Recommendation Report", "",
         f"- Workflow ID: `{s.workflow_id}`", f"- Final status: **{s.status}**",
         f"- Execution mode: {ctx.mode}", "",
         "## 1. User query", f"> {s.user_query}", ""]
    if s.clean_query is not None and s.clean_query != s.user_query:
        L += [f"Sanitised query used for planning: `{s.clean_query}`", ""]
    L += ["## 2. Structured requirements (Planner output)",
          _table(["Requirement", "Value"], [(k, v) for k, v in req.items()]), ""]

    L += ["## 3. Ranked products with recommendation score",
          _table(["Rank", "Product", "Price (₹)", "RAM", "Storage", "Rating", "Score", "Sources"],
                 [(p["rank"], p["name"], f"{p['price']:,.0f}", p["ram_gb"], p["storage_gb"], p["rating"],
                   p["score"], ",".join(p.get("sources", []))) for p in s.ranking[:settings.TOP_N]]
                 or [("-",) * 8]), ""]
    L += ["## 4. Selection reasoning"] + [f"- {p['reasoning']}" for p in s.ranking[:settings.TOP_N]] + [""]
    if s.rejected_results:
        L += ["### Rejected by the Filter Agent",
              _table(["Product", "Reason(s)"], [(p["name"], "; ".join(p["rejection_reasons"]))
                                                for p in s.rejected_results]), ""]

    L += ["## 5. Validation result",
          _table(["Checkpoint", "Passed", "Issues"],
                 [(k, v["passed"], "; ".join(v["issues"]) or "-") for k, v in s.validation.items()]), ""]
    if s.conflicts:
        L += ["### Data conflicts resolved",
              _table(["Product", "Field", "Values", "Resolved", "By", "Severity"],
                     [(c["product"], c["field"], c["values"], c["resolved_value"], c["resolved_by"],
                       c["severity"]) for c in s.conflicts]), ""]

    L += ["## 6. Human approval status", f"- Decision: **{s.human_approval.get('decision', 'n/a')}**",
          f"- Comment: {s.human_approval.get('comment', '-')}", ""]
    fr = s.final_recommendation
    if fr.get("top_pick"):
        t = fr["top_pick"]
        L += ["## 7. Final recommendation",
              f"**{t['name']}** - ₹{t['price']:,.0f}, {t['ram_gb']} GB RAM, {t['storage_gb']} GB storage, "
              f"rating {t['rating']} (score {t['score']}/100)", ""]
    else:
        L += ["## 7. Final recommendation", f"Status: {fr.get('status', 'none')}", ""]

    L += ["## 8. Agent execution trace", "```", ctx.tracer.flow(), "", ctx.tracer.render_text(), "```", ""]
    L += ["## 9. Agent communication records",
          _table(["Sender", "Receiver", "Task", "Status", "Output", "Retries"],
                 [(x["sender"], x["receiver"], x["task"], x["status"], x["output_summary"] or x["error"],
                   x["retries"]) for x in s.messages]), ""]
    L += ["## 10. Performance metrics",
          _table(["Metric", "Value"], [
              ("Total workflow time (s)", m["total_time_s"]),
              ("Sequential estimate (s)", m["sequential_time_s"]),
              ("Staged wall time (s)", m["parallel_time_s"]),
              ("Speedup (sequential / parallel)", m["speedup"]),
              ("Agent executions", m["agent_calls"]), ("Tool calls", m["tool_calls"]),
              ("Retries", m["retries"]), ("Processing operations", m["processing_ops"])]), ""]
    c = m["cost"]
    L += ["## 11. Experimental cost (units)",
          _table(["Component", "Cost"], [(k, v) for k, v in c.items()]), ""]
    if security_results is not None:
        L += ["## 12. Security test result",
              _table(["Test", "Result", "Details"],
                     [(r["test"], "PASS" if r["passed"] else "FAIL", r["details"]) for r in security_results]), ""]
    if s.errors:
        L += ["## Errors recorded"] + [f"- {e}" for e in s.errors] + [""]
    return "\n".join(L)


def save_report(ctx, security_results=None):
    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    settings.TRACE_DIR.mkdir(parents=True, exist_ok=True)
    wid = ctx.state.workflow_id
    path = settings.REPORT_DIR / f"report_{wid}.md"
    path.write_text(build_report(ctx, security_results), encoding="utf-8")
    (settings.TRACE_DIR / f"trace_{wid}.json").write_text(
        json.dumps(ctx.state.trace, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return path
