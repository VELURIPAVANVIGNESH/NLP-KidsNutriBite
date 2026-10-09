import unittest
import os
import sys
import json
import csv
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval, capture_frozen_assets_hashes, verify_hashes
from preprocessing.retrieval_evaluation import calculate_metrics, compute_extended_hashes

class TestNutriKidRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(BASE_DIR, "preprocessing", "config.json")
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)

    def test_01_manifest_and_metadata_integrity(self):
        """Assert manifest contains 32 total files and exactly 22 active core retrieval documents."""
        manifest_file = os.path.join(BASE_DIR, self.config["manifest_path"])
        self.assertTrue(os.path.exists(manifest_file), "corpus_manifest.csv missing!")
        
        active_count = 0
        total_count = 0
        with open(manifest_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_count += 1
                if row["retrieval_enabled"].strip().lower() == "true":
                    active_count += 1
                    
        self.assertEqual(total_count, 32, f"Expected 32 manifest records, got {total_count}")
        self.assertEqual(active_count, 22, f"Expected 22 active retrieval documents, got {active_count}")

    def test_02_parsed_documents_count(self):
        """Assert 22 parsed JSON documents exist in parsed directory."""
        parsed_dir = os.path.join(BASE_DIR, self.config["parsed_dir"])
        parsed_files = [f for f in os.listdir(parsed_dir) if f.endswith(".json")]
        self.assertEqual(len(parsed_files), 22, f"Expected 22 parsed JSONs, got {len(parsed_files)}")

    def test_03_preprocessed_chunks_count(self):
        """Assert preprocessed corpus contains exactly 6,422 retrieval-eligible chunks."""
        corpus_path = os.path.join(BASE_DIR, self.config["preprocessed_corpus_path"])
        self.assertTrue(os.path.exists(corpus_path), "preprocessed_corpus.json missing!")
        with open(corpus_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        self.assertEqual(len(chunks), 6422, f"Expected 6,422 preprocessed chunks, got {len(chunks)}")

    def test_04_bm25_index_structure(self):
        """Assert BM25 index contains 6,422 document IDs and vocabulary size of 33,038 terms."""
        bm25_path = os.path.join(BASE_DIR, self.config["bm25_index_path"])
        self.assertTrue(os.path.exists(bm25_path), "bm25_index.json missing!")
        with open(bm25_path, "r", encoding="utf-8") as f:
            bm25_data = json.load(f)
        self.assertEqual(len(bm25_data["doc_ids"]), 6422, "BM25 doc_ids count mismatch!")
        self.assertEqual(len(bm25_data["idf"]), 33038, "BM25 vocabulary size mismatch!")

    def test_05_faiss_dense_index_structure(self):
        """Assert FAISS dense index mapping contains exactly 6,422 chunk IDs."""
        dense_map_path = os.path.join(BASE_DIR, self.config["dense_map_path"])
        self.assertTrue(os.path.exists(dense_map_path), "dense_index_map.json missing!")
        with open(dense_map_path, "r", encoding="utf-8") as f:
            dense_map = json.load(f)
        self.assertEqual(len(dense_map), 6422, "FAISS map count mismatch!")

    def test_06_retrieval_age_filtering_gates(self):
        """Assert age filtering correctly passes in-scope age (10.0), terminates out-of-scope age (4.0), and defaults age=None."""
        # 1. In Scope
        res_in = run_retrieval(query="Calcium allowance for child", child_age=10.0, mode="hybrid", top_k=5)
        self.assertEqual(res_in["scope_status"], "in_scope")
        self.assertEqual(res_in["status"], "success")
        self.assertEqual(len(res_in["results"]), 5)

        # 2. Out of Scope (< 5.0)
        res_out = run_retrieval(query="Infant formula feeding", child_age=4.0, mode="hybrid", top_k=5)
        self.assertEqual(res_out["scope_status"], "out_of_scope")
        self.assertEqual(res_out["status"], "terminated_out_of_scope")
        self.assertEqual(len(res_out["results"]), 0)

        # 3. Missing Age (None)
        res_none = run_retrieval(query="Iron rich food items", child_age=None, mode="hybrid", top_k=5)
        self.assertEqual(res_none["scope_status"], "default_research_scope")
        self.assertEqual(res_none["effective_age_scope"], [5, 15])
        self.assertEqual(len(res_none["results"]), 5)

    def test_07_evaluation_metrics_calculator(self):
        """Assert metric calculation functions produce exact expected scores."""
        retrieved = ["C1", "C2", "C3", "C4", "C5"]
        ground_truth = {"C1": 3, "C3": 2, "C10": 3} # 3 total binary-relevant items (C1, C3, C10)
        metrics = calculate_metrics(retrieved, ground_truth)
        
        self.assertAlmostEqual(metrics["recall@1"], 1.0 / 3.0)
        self.assertAlmostEqual(metrics["recall@5"], 2.0 / 3.0)
        self.assertAlmostEqual(metrics["precision@1"], 1.0)
        self.assertAlmostEqual(metrics["mrr"], 1.0)

    def test_08_frozen_assets_hash_integrity(self):
        """Assert all 77 baseline data assets remain 100% untouched using MD5 checksum validation."""
        initial_hashes = capture_frozen_assets_hashes(self.config)
        integrity_passed, msg = verify_hashes(initial_hashes)
        self.assertTrue(integrity_passed, f"Hash integrity failure: {msg}")

if __name__ == "__main__":
    unittest.main()
