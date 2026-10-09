import unittest
import os
import sys
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.rerank import run_reranking

class TestRerankerPipeline(unittest.TestCase):

    def test_01_reranker_in_scope_candidate_expansion(self):
        """Assert reranker accepts candidate_k=50 and returns top_k=5 items with reranker_score."""
        res = run_reranking(
            query="What is the recommended dietary allowance for calcium for a child?",
            child_age=10.0,
            reranker_model_name="BAAI/bge-reranker-base",
            candidate_k=50,
            top_k=5
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["scope_status"], "in_scope")
        self.assertEqual(len(res["results"]), 5)
        
        # Verify metadata preservation
        first_item = res["results"][0]
        self.assertIn("chunk_id", first_item)
        self.assertIn("source_id", first_item)
        self.assertIn("source_name", first_item)
        self.assertIn("page_numbers", first_item)
        self.assertIn("reranker_score", first_item)
        self.assertIn("original_rank", first_item)
        self.assertIn("final_rank", first_item)

    def test_02_reranker_out_of_scope_termination(self):
        """Assert out of scope age (<5.0) terminates with 0 results."""
        res = run_reranking(
            query="What is infant formula recommendation?",
            child_age=3.0,
            reranker_model_name="BAAI/bge-reranker-base",
            candidate_k=50,
            top_k=5
        )
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(len(res["results"]), 0)

    def test_03_reranker_deterministic_sorting(self):
        """Assert output results are sorted by reranker score descending."""
        res = run_reranking(
            query="What foods are rich in iron?",
            child_age=12.0,
            reranker_model_name="BAAI/bge-reranker-base",
            candidate_k=50,
            top_k=5
        )
        scores = [item["reranker_score"] for item in res["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

if __name__ == "__main__":
    unittest.main()
