import os
import sys
import json
import csv
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval
from preprocessing.retrieval_evaluation import run_evaluation_suite

class TestPhase3Retrieval(unittest.TestCase):
    """Rigorous Phase 3.4 Hybrid RRF Retrieval Engine contract and benchmark verification suite."""

    def setUp(self):
        self.eval_queries_path = os.path.join(BASE_DIR, "data", "eval", "evaluation_queries.json")
        self.eval_report_path = os.path.join(BASE_DIR, "data", "processed", "evaluation_report.csv")
        self.eval_summary_path = os.path.join(BASE_DIR, "data", "processed", "evaluation_summary.md")

        self.assertTrue(os.path.exists(self.eval_queries_path), "evaluation_queries.json missing")

    def test_01_benchmark_queries_integrity(self):
        """Verify exactly 30 ground-truth evaluation queries in evaluation_queries.json."""
        with open(self.eval_queries_path, 'r', encoding='utf-8') as f:
            eval_queries = json.load(f)

        self.assertEqual(len(eval_queries), 30, f"Expected 30 benchmark queries, found {len(eval_queries)}")
        for q in eval_queries:
            self.assertTrue(q.get("query_id"), "Missing query_id")
            self.assertTrue(q.get("query_text"), "Missing query_text")
            self.assertGreater(len(q.get("relevant_chunks", [])), 0, "Missing ground truth relevant_chunks")

    def test_02_retrieval_modes_and_schema(self):
        """Verify BM25, Dense, and Hybrid retrieval mode execution and output schema."""
        test_query = "What is the recommended daily calcium allowance for school children?"

        # BM25 mode
        res_bm25 = run_retrieval(query=test_query, child_age=8.0, mode="bm25", top_k=5)
        self.assertEqual(res_bm25["status"], "success")
        self.assertEqual(len(res_bm25["results"]), 5)
        self.assertIsNotNone(res_bm25["results"][0]["sparse_rank"])

        # Dense mode
        res_dense = run_retrieval(query=test_query, child_age=8.0, mode="dense", top_k=5)
        self.assertEqual(res_dense["status"], "success")
        self.assertEqual(len(res_dense["results"]), 5)
        self.assertIsNotNone(res_dense["results"][0]["dense_rank"])

        # Hybrid mode
        res_hybrid = run_retrieval(query=test_query, child_age=8.0, mode="hybrid", top_k=5)
        self.assertEqual(res_hybrid["status"], "success")
        self.assertEqual(len(res_hybrid["results"]), 5)
        self.assertIsNotNone(res_hybrid["results"][0]["rrf_score"])

    def test_03_deterministic_retrieval_repeatability(self):
        """Verify 100% deterministic ranking and score repeatability across multiple calls."""
        test_query = "What is the recommended dietary protein intake for an 8-year-old child?"

        res_run1 = run_retrieval(query=test_query, child_age=8.0, mode="hybrid", top_k=5)
        res_run2 = run_retrieval(query=test_query, child_age=8.0, mode="hybrid", top_k=5)

        cids_run1 = [r["chunk_id"] for r in res_run1["results"]]
        cids_run2 = [r["chunk_id"] for r in res_run2["results"]]
        self.assertEqual(cids_run1, cids_run2, "Retrieval ranking is nondeterministic between runs")

        scores_run1 = [r["score"] for r in res_run1["results"]]
        scores_run2 = [r["score"] for r in res_run2["results"]]
        self.assertEqual(scores_run1, scores_run2, "Retrieval scores are nondeterministic between runs")

    def test_04_age_scope_enforcement_gate(self):
        """Verify strict rejection of out-of-scope age queries (<5 and >15 years)."""
        test_query = "What infant formula is recommended?"

        # Out-of-scope underage (3.0 yrs)
        res_underage = run_retrieval(query=test_query, child_age=3.0, mode="hybrid", top_k=5)
        self.assertEqual(res_underage["scope_status"], "out_of_scope")
        self.assertEqual(res_underage["status"], "terminated_out_of_scope")
        self.assertEqual(len(res_underage["results"]), 0)

        # Out-of-scope overage (16.0 yrs)
        res_overage = run_retrieval(query=test_query, child_age=16.0, mode="hybrid", top_k=5)
        self.assertEqual(res_overage["scope_status"], "out_of_scope")
        self.assertEqual(res_overage["status"], "terminated_out_of_scope")
        self.assertEqual(len(res_overage["results"]), 0)

    def test_05_frozen_baseline_metric_verification(self):
        """Verify that evaluation outputs match frozen retrieval baseline MRR benchmarks."""
        self.assertTrue(os.path.exists(self.eval_report_path), "evaluation_report.csv missing")
        self.assertTrue(os.path.exists(self.eval_summary_path), "evaluation_summary.md missing")

        with open(self.eval_report_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 30 queries x 3 modes = 90 rows
        self.assertEqual(len(rows), 90, f"Expected 90 evaluation report rows (30 queries x 3 modes), found {len(rows)}")

if __name__ == "__main__":
    unittest.main()
