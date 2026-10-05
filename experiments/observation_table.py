"""Fills the lab's OBSERVATION TABLE from real runs."""


def build_observation_table(query, seq_ctx, par_ctx, fault_ctx, security_results):
    sm, pm, fm = seq_ctx.metrics.summary(), par_ctx.metrics.summary(), fault_ctx.metrics.summary()
    senders = {m["sender"].split("[")[0] for m in par_ctx.state.messages}
    passed = sum(r["passed"] for r in security_results)
    top = par_ctx.state.ranking[0] if par_ctx.state.ranking else None
    speedup = round(sm["total_time_s"] / pm["total_time_s"], 2) if pm["total_time_s"] else 1.0
    rows = [
        ("User Query", query),
        ("Number of Agents Executed", f"{pm['agent_calls']} executions across {len(senders)} distinct agents"),
        ("Sequential Execution Time", f"{sm['total_time_s']} s"),
        ("Parallel Execution Time", f"{pm['total_time_s']} s"),
        ("Speedup (Sequential / Parallel)", f"{speedup}x"),
        ("Number of Tool Calls", pm["tool_calls"]),
        ("Number of Retries (with 1 injected transient failure)", fm["retries"]),
        ("Experimental Cost (clean parallel run)", f"{pm['cost']['total']} units"),
        ("Human Approval", par_ctx.state.human_approval.get("decision", "n/a")),
        ("Security Test Result", f"{passed}/{len(security_results)} passed"),
        ("Final Recommendation",
         f"{top['name']} - ₹{top['price']:,.0f} (score {top['score']})" if top else "none"),
    ]
    lines = ["| Parameter | Observation |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    return "\n".join(lines), rows
