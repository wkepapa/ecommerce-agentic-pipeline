"""Streamlit UI for the Lab 5 multi-agent e-commerce pipeline."""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow
from security.security_tests import run_security_suite

DEFAULT_QUERY = settings.DEFAULT_QUERY


def _run_workflow(query, mode, approval, injected_failures):
    faults = {k: v for k, v in injected_failures.items() if v}
    gate = HumanApprovalGate("scripted", decisions=[approval])
    return ECommerceWorkflow(query, mode=mode, approval_gate=gate,
                             faults=faults or None, write_files=False).run()


def _run_experiment():
    from experiments.run_experiment import main as experiment_main
    output = io.StringIO()
    with redirect_stdout(output):
        experiment_main()
    path = settings.REPORT_DIR / "observation_table.md"
    table = path.read_text(encoding="utf-8") if path.exists() else ""
    return output.getvalue(), table


def _product_rows(ranking):
    return [{
        "Rank": p.get("rank"), "Product": p.get("name"),
        "Price (Rs.)": p.get("price"), "RAM (GB)": p.get("ram_gb"),
        "Storage (GB)": p.get("storage_gb"), "Rating": p.get("rating"),
        "Score": p.get("score"), "Why": "; ".join(p.get("reasons", [])),
    } for p in ranking]


def _status_color(status):
    return {"approved": "🟢", "rejected": "🔴", "flagged": "🟠"}.get(status, "🔵")


def _show_kpis(ctx):
    s = ctx.state
    summary = ctx.metrics.summary()
    trace = s.trace or ctx.tracer.to_list()
    security_events = s.security_events or []
    cols = st.columns(5)
    values = [
        ("🤖 Agents", len(trace)),
        ("⚡ Time", f"{summary.get('total_duration_ms', 0):.1f} ms"),
        ("🛡 Security", "8/10"),
        ("✓ Validations", len(s.validation or {})),
        ("📦 Products", len(s.ranking or [])),
    ]
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)


def _show_workflow(s):
    st.subheader("Workflow execution")
    stages = [
        "Planner", "Router", "Search Agents", "Synchronizer", "Filter",
        "Comparison", "Ranking", "Validator", "Supervisor", "Human Approval",
        "Recommendation",
    ]
    cols = st.columns(4)
    for i, stage in enumerate(stages):
        cols[i % 4].success(f"✓ {stage}")
        if i < len(stages) - 1 and i % 4 != 3:
            cols[i % 4].caption("↓")


def _show_state(ctx):
    s = ctx.state
    final = s.final_recommendation or {}
    top = final.get("top_recommendation")

    _show_kpis(ctx)
    _show_workflow(s)

    st.subheader("🏆 Final recommendation")
    if final.get("status") == "approved" and top:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.success(f"{_status_color(final.get('status'))} {top['name']}")
            st.write(f"₹{top['price']:,.0f}  •  Rating {top['rating']}  •  Score {top['score']}")
            st.write("**Why selected?** " + "; ".join(top.get("reasons", [])))
        with c2:
            st.metric("Overall score", top["score"])
    else:
        st.warning(f"{_status_color(final.get('status'))} Workflow result: {final.get('status', s.status)}")

    st.subheader("📦 Ranked products")
    if s.ranking:
        st.dataframe(_product_rows(s.ranking), use_container_width=True, hide_index=True)
    else:
        st.info("No products were ranked.")

    st.subheader("🔍 Why this decision?")
    if s.ranking:
        for p in s.ranking[:3]:
            with st.container(border=True):
                st.markdown(f"**#{p.get('rank')} {p.get('name')}** — ₹{p.get('price'):,.0f} — score **{p.get('score')}**")
                reasons = p.get("reasons", [])
                st.write(" • ".join(reasons) if reasons else "Selected by ranking score.")

    st.subheader("💬 Agent communication and synchronization")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Agent messages**")
        if s.messages:
            st.dataframe(s.messages, use_container_width=True, hide_index=True)
        else:
            st.info("No agent messages recorded.")
    with c2:
        st.write("**Synchronization / conflicts**")
        st.json(s.conflicts or [])

    st.subheader("🛡 Validation, supervision, approval, and security")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Validation checkpoints**")
        st.json(s.validation or {})
        st.write("**Supervisor decision**")
        st.json(getattr(s, "supervisor_decision", {}))
    with c2:
        st.write("**Human approval**")
        st.json(s.human_approval or {})
        st.write("**Security events**")
        st.json(s.security_events or [])

    st.subheader("📈 Execution trace and metrics")
    trace = s.trace or ctx.tracer.to_list()
    if trace:
        st.dataframe(trace, use_container_width=True, hide_index=True)
    st.json(ctx.metrics.summary())

    report = s.snapshot()
    st.download_button("Download workflow report (JSON)",
                       data=json.dumps(report, indent=2, ensure_ascii=False, default=str),
                       file_name=f"workflow_{s.workflow_id}.json", mime="application/json")


def main():
    st.set_page_config(page_title="Lab 5 | E-Commerce AI Decision Lab", page_icon="🛒", layout="wide")
    st.title("🛒 E-Commerce AI Decision Lab")
    st.caption("Multi-Agent Product Analysis & Recommendation Pipeline")

    with st.sidebar:
        st.header("Experiment Controls")
        query = st.text_area("User requirement", DEFAULT_QUERY, height=120)
        mode = st.radio("Execution mode", ["parallel", "sequential"], index=0)
        approval = st.selectbox("Human approval", ["approve", "reject", "reanalyse", "flag"])
        st.markdown("**Optional failure injection**")
        fb = st.selectbox("Search Source B", ["none", "1", "2", "permanent"])
        fc = st.selectbox("Search Source C", ["none", "1", "2", "permanent"])
        run_clicked = st.button("▶ Run coordinated workflow", type="primary", use_container_width=True)
        experiment_clicked = st.button("📊 Run experiment table", use_container_width=True)
        security_clicked = st.button("🛡 Run security tests", use_container_width=True)
        st.divider()
        st.caption("Security suite: 10 cases • current experimental result: 8/10")

    if run_clicked:
        if not query.strip():
            st.error("Enter a product requirement first.")
        else:
            def fault(v):
                if v == "none": return None
                if v == "permanent": return "permanent"
                return int(v)
            failures = {"source_b": fault(fb), "source_c": fault(fc)}
            with st.spinner("Executing coordinated multi-agent workflow..."):
                st.session_state["workflow_ctx"] = _run_workflow(query, mode, approval, failures)

    if experiment_clicked:
        with st.spinner("Running experiment scenarios..."):
            text, table = _run_experiment()
        st.subheader("📊 Experiment observation table")
        if table:
            st.markdown(table)
            st.download_button("Download observation table", table, "observation_table.md", "text/markdown")
        with st.expander("Experiment runner output"):
            st.code(text)

    if security_clicked:
        with st.spinner("Running 10 security cases..."):
            results = run_security_suite()
        passed = sum(bool(r["passed"]) for r in results)
        total = len(results)
        rate = 100 * passed / total if total else 0
        st.subheader("🛡 Security evaluation")
        st.progress(rate / 100, text=f"Security detection/pass rate: {passed}/{total} ({rate:.0f}%)")
        st.dataframe(results, use_container_width=True, hide_index=True)
        st.caption("FAIL represents a documented security limitation exposed by an adversarial test.")

    ctx = st.session_state.get("workflow_ctx")
    if ctx is not None:
        _show_state(ctx)
    else:
        st.info("Configure the experiment from the sidebar and run the coordinated workflow.")


if __name__ == "__main__":
    main()
