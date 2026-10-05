import unittest

from agents.query_parser import parse_requirements
from config import settings
from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow


def run(query=settings.DEFAULT_QUERY, **kw):
    kw.setdefault("search_latency", 0.01)
    kw.setdefault("write_files", False)
    return ECommerceWorkflow(query, approval_gate=kw.pop("gate", HumanApprovalGate("auto")), **kw).run()


class FunctionalTests(unittest.TestCase):
    def test_requirement_extraction(self):
        r = parse_requirements(settings.DEFAULT_QUERY)
        self.assertEqual((r["category"], r["max_budget"], r["min_ram_gb"], r["min_storage_gb"], r["min_rating"]),
                         ("laptop", 70000, 16, 512, 4.2))

    def test_other_phrasings(self):
        r = parse_requirements("best laptops below 60k with 1 TB SSD and 8 GB RAM, rating 4.5+")
        self.assertEqual((r["max_budget"], r["min_storage_gb"], r["min_ram_gb"], r["min_rating"]),
                         (60000, 1024, 8, 4.5))

    def test_full_pipeline(self):
        ctx = run()
        s = ctx.state
        self.assertEqual(s.status, "completed")
        self.assertTrue(s.ranking)
        for p in s.ranking:
            self.assertLessEqual(p["price"], 70000)
            self.assertGreaterEqual(p["ram_gb"], 16)
            self.assertGreaterEqual(p["storage_gb"], 512)
            self.assertGreaterEqual(p["rating"], 4.2)
        scores = [p["score"] for p in s.ranking]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(v["passed"] for v in s.validation.values()))
        self.assertEqual(set(s.validation), {"requirements", "filtering", "ranking"})
        self.assertTrue(s.comparison["rows"])
        self.assertEqual(s.final_recommendation["status"], "approved")

    def test_routing_is_dependency_aware(self):
        stages = run().state.routing["stages"]
        self.assertEqual(len(stages[0]["tasks"]), 4)          # 3 searches + requirement validation in parallel
        self.assertTrue(stages[0]["synchronize"])
        self.assertEqual(stages[1]["tasks"], ["filter"])

    def test_conflict_resolved_by_trusted_priority(self):
        s = run().state
        c = next(c for c in s.conflicts if c["product_id"] == "L001" and c["field"] == "rating")
        self.assertEqual(c["resolved_value"], 4.4)
        self.assertEqual(c["severity"], "high")

    def test_no_results(self):
        s = run("Find laptops under ₹20,000 with at least 32 GB RAM and rating above 4.9").state
        self.assertEqual(s.status, "no_results")


if __name__ == "__main__":
    unittest.main()
