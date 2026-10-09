"""
preprocessing/test_retriever.py — Automated Test Suite for Phase 3.4 Hybrid Retriever
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import csv
import json
import sys
import hashlib
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval, capture_frozen_assets_hashes, verify_hashes, check_age_compatibility

class TestNutriKidRetriever(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config_path = "preprocessing/config.json"
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)
            
        with open(cls.config["preprocessed_corpus_path"], "r", encoding="utf-8") as f:
            cls.corpus = json.load(f)
        cls.corpus_dict = {c["chunk_id"]: c for c in cls.corpus}
        
        with open(cls.config["manifest_path"], "r", encoding="utf-8") as f:
            manifest_rows = list(csv.DictReader(f))
        cls.disabled_sids = set(r["source_id"] for r in manifest_rows if r["retrieval_enabled"].strip().lower() == "false")
        
        # Capture frozen asset hashes before tests begin
        cls.initial_hashes = capture_frozen_assets_hashes(cls.config)

    def test_01_in_scope_age_10(self):
        """TEST 1: Age=10, Calcium RDA query -> in_scope, success status"""
        res = run_retrieval(query="Calcium RDA for children", child_age=10, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "in_scope")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["results"]), 5)
        
        chunk_ids = [r["chunk_id"] for r in res["results"]]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)), "Duplicate chunk IDs found in top_k")
        
        for r in res["results"]:
            cid = r["chunk_id"]
            orig = self.corpus_dict[cid]
            self.assertEqual(r["text"], orig["text"], "Returned text does not match preprocessed_corpus.json")
            self.assertNotIn(r["source_id"], self.disabled_sids, f"Disabled source {r['source_id']} returned")
            self.assertTrue(check_age_compatibility(orig, 10), f"Age incompatible chunk {cid} returned for age 10")

    def test_02_in_scope_age_15(self):
        """TEST 2: Age=15, Red meat query -> in_scope, success status (upper boundary)"""
        res = run_retrieval(query="Red meat intake guidelines", child_age=15, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "in_scope")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["results"]), 5)
        
        for r in res["results"]:
            cid = r["chunk_id"]
            orig = self.corpus_dict[cid]
            self.assertNotIn(r["source_id"], self.disabled_sids)
            self.assertTrue(check_age_compatibility(orig, 15))

    def test_02b_in_scope_boundary_age_5(self):
        """TEST 2b: Age=5 (lower in-scope boundary) -> in_scope, success status"""
        res = run_retrieval(query="Calcium RDA for children", child_age=5, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "in_scope")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["results"]), 5)

    def test_03_out_of_scope_age_4(self):
        """TEST 3: Age=4 (lower out-of-scope boundary) -> out_of_scope, 0 results, 0 retrieval execution"""
        res = run_retrieval(query="Zinc requirement", child_age=4, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertEqual(len(res["results"]), 0)
        self.assertEqual(res["accounting"]["returned_count"], 0)

    def test_04_out_of_scope_age_1(self):
        """TEST 4: Age=1 -> out_of_scope, zero retrieval"""
        res = run_retrieval(query="Infant nutrition formula", child_age=1, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertEqual(len(res["results"]), 0)

    def test_05_out_of_scope_age_16(self):
        """TEST 5: Age=16 (upper out-of-scope boundary) -> out_of_scope, zero retrieval"""
        res = run_retrieval(query="Adolescent energy intake", child_age=16, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertEqual(len(res["results"]), 0)

    def test_06_null_age_default_research_scope(self):
        """TEST 6: Age=null -> default_research_scope [5, 15]"""
        res = run_retrieval(query="Iron-rich foods for growing children", child_age=None, mode="hybrid", top_k=5)
        self.assertEqual(res["scope_status"], "default_research_scope")
        self.assertEqual(res["effective_age_scope"], [5, 15])
        self.assertIn(res["status"], ["success", "insufficient_eligible_candidates"])
        self.assertEqual(len(res["results"]), 5)
        
        for r in res["results"]:
            cid = r["chunk_id"]
            orig = self.corpus_dict[cid]
            self.assertTrue(check_age_compatibility(orig, None))

    def test_07_mode_comparison_and_determinism(self):
        """TEST 7: Compare BM25, Dense, Hybrid modes and verify 100% deterministic reproducibility"""
        query = "Vitamin D deficiency symptoms"
        res_bm25 = run_retrieval(query=query, child_age=12, mode="bm25", top_k=5)
        res_dense = run_retrieval(query=query, child_age=12, mode="dense", top_k=5)
        res_hybrid = run_retrieval(query=query, child_age=12, mode="hybrid", top_k=5)
        
        self.assertEqual(res_bm25["status"], "success")
        self.assertEqual(res_dense["status"], "success")
        self.assertEqual(res_hybrid["status"], "success")
        
        # Verify deterministic reproducibility (2 consecutive calls produce identical output)
        res_hybrid_repeat = run_retrieval(query=query, child_age=12, mode="hybrid", top_k=5)
        self.assertEqual(
            [r["chunk_id"] for r in res_hybrid["results"]],
            [r["chunk_id"] for r in res_hybrid_repeat["results"]],
            "Hybrid retrieval is non-deterministic!"
        )

    def test_08_insufficient_candidates_handling(self):
        """TEST 8: Request top_k=10 with candidate_k=1 -> status = insufficient_eligible_candidates"""
        res = run_retrieval(query="Potassium intake guideline", child_age=8, mode="hybrid", top_k=10, candidate_k=1)
        self.assertLess(res["accounting"]["returned_count"], 10)
        self.assertEqual(res["status"], "insufficient_eligible_candidates")
        self.assertEqual(res["accounting"]["candidate_k"], 1)

    def test_09_rrf_calculation_and_tie_breaking(self):
        """TEST 9: Validate RRF formula: RRF(d) = 1/(60+sparse_rank) + 1/(60+dense_rank)"""
        res = run_retrieval(query="Sodium intake for children", child_age=10, mode="hybrid", top_k=5)
        for r in res["results"]:
            s_r = r["sparse_rank"]
            d_r = r["dense_rank"]
            expected_rrf = 0.0
            if s_r is not None:
                expected_rrf += 1.0 / (60.0 + s_r)
            if d_r is not None:
                expected_rrf += 1.0 / (60.0 + d_r)
                
            self.assertAlmostEqual(r["rrf_score"], expected_rrf, places=6, msg=f"RRF calculation mismatch for chunk {r['chunk_id']}")

    def test_10_frozen_assets_integrity(self):
        """TEST 10: Verify 0 modifications to frozen input assets"""
        ok, err = verify_hashes(self.initial_hashes)
        self.assertTrue(ok, f"Frozen asset integrity check failed: {err}")

def run_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNutriKidRetriever)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Save text report to data/processed/retrieval_test_report.txt
    report_lines = [
        "==================================================",
        "NUTRIKID HYBRID RETRIEVER VALIDATION REPORT (PHASE 3.4)",
        "==================================================",
        f"Tests Run: {result.testsRun}",
        f"Failures:  {len(result.failures)}",
        f"Errors:    {len(result.errors)}",
        f"Status:    {'PASS' if result.wasSuccessful() else 'FAIL'}",
        "=================================================="
    ]
    with open("data/processed/retrieval_test_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
