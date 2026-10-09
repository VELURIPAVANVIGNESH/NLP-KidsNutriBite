import os
import sys
import json
import csv
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.rerank import run_reranking, get_reranker
from preprocessing.context_refiner import refine_context, compute_jaccard_similarity

class TestPhase35Reranking(unittest.TestCase):
    """Rigorous Phase 3.5 Cross-Encoder Reranking & Context Refinement contract test suite."""

    def setUp(self):
        self.rerank_csv_path = os.path.join(BASE_DIR, "data", "processed", "reranking_evaluation.csv")
        self.rerank_summary_path = os.path.join(BASE_DIR, "data", "processed", "reranking_summary.md")
        self.eval_queries_path = os.path.join(BASE_DIR, "data", "eval", "evaluation_queries.json")

    def test_01_model_loading_and_alias(self):
        """Verify CrossEncoder model loading for BAAI/bge-reranker-base."""
        model = get_reranker("BAAI/bge-reranker-base")
        self.assertIsNotNone(model, "Failed to load BAAI/bge-reranker-base model")

    def test_02_reranking_output_schema(self):
        """Verify output schema of run_reranking."""
        res = run_reranking("What is the daily calcium recommendation for children?", child_age=10.0, candidate_k=20, top_k=5)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["reranker_model"], "BAAI/bge-reranker-base")

        results = res["results"]
        self.assertEqual(len(results), 5)
        for idx, item in enumerate(results):
            self.assertEqual(item["rank"], idx + 1)
            self.assertIn("reranker_score", item)
            self.assertIn("original_rank", item)
            self.assertIn("chunk_id", item)
            self.assertIn("source_id", item)
            self.assertIn("page_numbers", item)
            self.assertIn("text", item)

    def test_03_mrr_and_ndcg_improvement_gate(self):
        """Verify MRR and nDCG@5 improvements from frozen baseline."""
        if not os.path.exists(self.rerank_csv_path):
            from preprocessing.rerank import evaluate_rerankers
            evaluate_rerankers()

        with open(self.rerank_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        bge_rows = [r for r in rows if r["mode_key"] == "reranker_bge"]
        if len(bge_rows) < 30 or sum(float(r["mrr"]) for r in bge_rows) / float(len(bge_rows)) < 0.10:
            from preprocessing.rerank import evaluate_rerankers
            evaluate_rerankers()
            with open(self.rerank_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            bge_rows = [r for r in rows if r["mode_key"] == "reranker_bge"]
        self.assertEqual(len(bge_rows), 30, f"Expected 30 queries for bge reranker, found {len(bge_rows)}")

        avg_mrr = sum(float(r["mrr"]) for r in bge_rows) / 30.0
        avg_ndcg5 = sum(float(r["ndcg@5"]) for r in bge_rows) / 30.0

        # Assert MRR is >= 0.12 (baseline was 0.0400) -> >200% improvement!
        self.assertGreaterEqual(avg_mrr, 0.1200, f"Reranker MRR ({avg_mrr:.4f}) did not achieve expected improvement threshold (>=0.1200)")

        # Assert nDCG@5 is >= 0.12 (baseline was 0.0435) -> >200% improvement!
        self.assertGreaterEqual(avg_ndcg5, 0.1200, f"Reranker nDCG@5 ({avg_ndcg5:.4f}) did not achieve expected improvement threshold (>=0.1200)")

    def test_04_exact_and_near_duplicate_deduplication(self):
        """Verify context refiner removes exact duplicate chunk IDs and near-duplicate text (Jaccard >= 0.85)."""
        sample_input = {
            "query": "What is the calcium requirement for a 10-year-old?",
            "requested_age": 10.0,
            "scope_status": "in_scope",
            "results": [
                {
                    "rank": 1,
                    "chunk_id": "NK-021-C00100",
                    "source_id": "NK-021",
                    "text": "The recommended dietary allowance of calcium for children aged 10 to 12 years is 850 mg/day.",
                    "reranker_score": 3.5
                },
                {
                    "rank": 2,
                    "chunk_id": "NK-021-C00100",  # Exact duplicate ID
                    "source_id": "NK-021",
                    "text": "The recommended dietary allowance of calcium for children aged 10 to 12 years is 850 mg/day.",
                    "reranker_score": 3.5
                },
                {
                    "rank": 3,
                    "chunk_id": "NK-021-C00101",
                    "source_id": "NK-021",
                    # Near duplicate text (>0.85 Jaccard)
                    "text": "The recommended dietary allowance of calcium for children aged 10 to 12 years is 850 mg per day.",
                    "reranker_score": 3.4
                },
                {
                    "rank": 4,
                    "chunk_id": "NK-008-C00050",
                    "source_id": "NK-008",
                    "text": "Protein requirement for school children is 23 g/day.",
                    "reranker_score": 1.2
                }
            ]
        }

        refined = refine_context(sample_input, near_duplicate_threshold=0.85)
        stats = refined["refinement_stats"]
        evidence = refined["evidence"]

        self.assertEqual(stats["exact_duplicates_removed"], 1)
        self.assertEqual(stats["near_duplicates_removed"], 1)
        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0]["chunk_id"], "NK-021-C00100")
        self.assertEqual(evidence[1]["chunk_id"], "NK-008-C00050")

    def test_05_numerical_and_provenance_preservation(self):
        """Verify 100% preservation of numbers, units, source_id, file_name, and page_numbers in context refiner."""
        sample_input = {
            "query": "Iron RDA for children",
            "requested_age": 9.0,
            "scope_status": "in_scope",
            "results": [
                {
                    "rank": 1,
                    "chunk_id": "NK-008-C00210",
                    "source_id": "NK-008",
                    "source_name": "ICMR RDA 2020",
                    "file_name": "brief_note.pdf",
                    "page_numbers": [14, 15],
                    "age_min": 7.0,
                    "age_max": 9.0,
                    "reranker_score": 2.85,
                    "context_prefix": "Section: Iron RDA Table",
                    "text": "Iron EAR for children 7-9 years is 11 mg/day and RDA is 15 mg/day."
                }
            ]
        }

        refined = refine_context(sample_input)
        ev = refined["evidence"][0]

        self.assertEqual(ev["source_id"], "NK-008")
        self.assertEqual(ev["file_name"], "brief_note.pdf")
        self.assertEqual(ev["page_numbers"], [14, 15])
        self.assertIn("11 mg/day", ev["text"])
        self.assertIn("15 mg/day", ev["text"])

    def test_06_age_scope_enforcement_in_reranking(self):
        """Verify that out-of-scope age queries are terminated cleanly before reranking."""
        res_underage = run_reranking("Infant feeding guidelines", child_age=2.0)
        self.assertEqual(res_underage["scope_status"], "out_of_scope")
        self.assertEqual(res_underage["status"], "terminated_out_of_scope")
        self.assertEqual(len(res_underage["results"]), 0)

        refined_underage = refine_context(res_underage)
        self.assertEqual(refined_underage["scope_status"], "out_of_scope")
        self.assertEqual(len(refined_underage["evidence"]), 0)

    def test_07_deterministic_repeatability(self):
        """Verify 100% deterministic repeatability across repeat reranking calls."""
        q = "What is the recommended daily intake of Vitamin D for a 12 year old child?"
        res1 = run_reranking(q, child_age=12.0)
        res2 = run_reranking(q, child_age=12.0)

        cids1 = [r["chunk_id"] for r in res1["results"]]
        cids2 = [r["chunk_id"] for r in res2["results"]]
        self.assertEqual(cids1, cids2)

        scores1 = [r["reranker_score"] for r in res1["results"]]
        scores2 = [r["reranker_score"] for r in res2["results"]]
        self.assertEqual(scores1, scores2)

if __name__ == "__main__":
    unittest.main()
