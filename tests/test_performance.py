import unittest

from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow
from config import settings


def run(mode):
    return ECommerceWorkflow(settings.DEFAULT_QUERY, mode=mode, approval_gate=HumanApprovalGate("auto"),
                             search_latency=0.15, write_files=False).run()


class PerformanceTests(unittest.TestCase):
    def test_parallel_is_faster_than_sequential(self):
        seq, par = run("sequential"), run("parallel")
        self.assertGreater(seq.metrics.total_time / par.metrics.total_time, 1.5)
        self.assertGreater(par.metrics.speedup(), 1.5)          # staged sequential-estimate / staged wall

    def test_same_work_same_cost_when_no_retries(self):
        seq, par = run("sequential"), run("parallel")
        self.assertEqual(seq.metrics.agent_calls, par.metrics.agent_calls)
        self.assertEqual(seq.metrics.tool_calls, par.metrics.tool_calls)
        self.assertEqual(seq.metrics.cost()["total"], par.metrics.cost()["total"])
        self.assertEqual(par.metrics.agent_calls, 12)
        self.assertEqual(par.metrics.tool_calls, 10)

    def test_same_ranking_in_both_modes(self):
        a = [p["id"] for p in run("sequential").state.ranking]
        b = [p["id"] for p in run("parallel").state.ranking]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
