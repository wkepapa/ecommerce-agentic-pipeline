import unittest

from config import settings
from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow


def run(query=settings.DEFAULT_QUERY, gate=None, **kw):
    kw.setdefault("search_latency", 0.01)
    return ECommerceWorkflow(query, approval_gate=gate or HumanApprovalGate("auto"),
                             write_files=False, **kw).run()


class FailureTests(unittest.TestCase):
    def test_transient_failure_is_retried(self):
        ctx = run(faults={"source_b": 1})
        self.assertEqual(ctx.state.status, "completed")
        self.assertEqual(ctx.metrics.retries, 1)
        self.assertIn("source_b", ctx.state.raw_search_results)

    def test_permanent_failure_degrades_gracefully_with_bounded_retries(self):
        ctx = run(faults={"source_c": 99})
        self.assertEqual(ctx.state.status, "completed")
        self.assertEqual(ctx.metrics.retries, settings.MAX_RETRIES)       # never infinite
        self.assertNotIn("source_c", ctx.state.raw_search_results)
        self.assertTrue(ctx.state.errors)

    def test_all_sources_fail_aborts(self):
        ctx = run(faults={"source_a": 99, "source_b": 99, "source_c": 99})
        self.assertEqual(ctx.state.status, "aborted")

    def test_invalid_input(self):
        self.assertEqual(run("hello there").state.status, "failed_invalid_input")

    def test_missing_data_rejected_by_filter(self):
        s = run().state
        names = {p["name"]: p["rejection_reasons"] for p in s.rejected_results}
        self.assertIn("missing rating", names["Dell Inspiron 14"])

    def test_human_rejection(self):
        self.assertEqual(run(gate=HumanApprovalGate("reject")).state.status, "rejected_by_human")

    def test_human_reanalysis_then_approval(self):
        ctx = run(gate=HumanApprovalGate("scripted", ["reanalyse", "approve"]))
        self.assertEqual(ctx.state.status, "completed")
        self.assertEqual(ctx.state.human_approval["decision"], "approve")

    def test_tool_timeout_is_recoverable_error_type(self):
        ctx = run(search_latency=0.3, tool_timeout=0.05, max_retries=1)
        self.assertEqual(ctx.state.status, "aborted")                     # every source times out


if __name__ == "__main__":
    unittest.main()
