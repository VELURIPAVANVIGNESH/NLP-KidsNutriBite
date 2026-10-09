"""
preprocessing/test_phase3_4_1_evaluation.py — Automated Test Suite for Phase 3.4.1 Evaluation
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import csv
import json
import sys
import math
import hashlib
import unittest
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import capture_frozen_assets_hashes, verify_hashes
from preprocessing.retrieval_evaluation import run_evaluation_suite, format_pct

class TestNutriKidRetrievalEvaluation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config_path = "preprocessing/config.json"
        with open(cls.config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)
            
        cls.benchmark_path = "data/evaluation/retrieval_benchmark.json"
        with open(cls.benchmark_path, "r", encoding="utf-8") as f:
            cls.benchmark_queries = json.load(f)
            
        with open(cls.config["preprocessed_corpus_path"], "r", encoding="utf-8") as f:
            cls.corpus = json.load(f)
        cls.corpus_ids = set(c["chunk_id"] for c in cls.corpus)
        
        with open(cls.config["manifest_path"], "r", encoding="utf-8") as f:
            manifest_rows = list(csv.DictReader(f))
        cls.disabled_sids = set(r["source_id"] for r in manifest_rows if r["retrieval_enabled"].strip().lower() == "false")
        
        cls.initial_hashes = capture_frozen_assets_hashes(cls.config)
        cls.eval_results, _ = run_evaluation_suite(cls.benchmark_path)

    def test_01_benchmark_dataset_exists(self):
        """TEST 01: Benchmark dataset file exists at data/evaluation/retrieval_benchmark.json"""
        self.assertTrue(os.path.exists(self.benchmark_path), "retrieval_benchmark.json does not exist")

    def test_02_at_least_30_queries(self):
        """TEST 02: Benchmark dataset contains at least 30 queries"""
        self.assertGreaterEqual(len(self.benchmark_queries), 30, f"Expected >= 30 queries, found {len(self.benchmark_queries)}")

    def test_03_query_id_completeness(self):
        """TEST 03: Every query in benchmark has a non-empty query_id"""
        for q in self.benchmark_queries:
            self.assertIn("query_id", q)
            self.assertTrue(str(q["query_id"]).strip(), f"Query missing query_id: {q}")

    def test_04_relevance_labels_present(self):
        """TEST 04: Every query has relevant_chunks relevance labels"""
        for q in self.benchmark_queries:
            rel = q.get("relevant_chunks", [])
            self.assertGreater(len(rel), 0, f"Query {q['query_id']} has 0 relevant_chunks labels")

    def test_05_relevant_chunks_exist_in_corpus(self):
        """TEST 05: Every relevant chunk ID exists in preprocessed_corpus.json"""
        for q in self.benchmark_queries:
            for rel in q.get("relevant_chunks", []):
                cid = rel["chunk_id"]
                self.assertIn(cid, self.corpus_ids, f"Relevant chunk {cid} in query {q['query_id']} missing from corpus")

    def test_06_bm25_evaluated_on_all_queries(self):
        """TEST 06: BM25 evaluated on every benchmark query"""
        bm25_qids = set(r["query_id"] for r in self.eval_results if r["mode"] == "bm25")
        bench_qids = set(q["query_id"] for q in self.benchmark_queries)
        self.assertEqual(bm25_qids, bench_qids, "BM25 was not evaluated on all benchmark queries")

    def test_07_dense_evaluated_on_all_queries(self):
        """TEST 07: Dense FAISS evaluated on every benchmark query"""
        dense_qids = set(r["query_id"] for r in self.eval_results if r["mode"] == "dense")
        bench_qids = set(q["query_id"] for q in self.benchmark_queries)
        self.assertEqual(dense_qids, bench_qids, "Dense retriever was not evaluated on all benchmark queries")

    def test_08_hybrid_evaluated_on_all_queries(self):
        """TEST 08: Hybrid RRF evaluated on every benchmark query"""
        hybrid_qids = set(r["query_id"] for r in self.eval_results if r["mode"] == "hybrid")
        bench_qids = set(q["query_id"] for q in self.benchmark_queries)
        self.assertEqual(hybrid_qids, bench_qids, "Hybrid retriever was not evaluated on all benchmark queries")

    def test_09_no_duplicate_query_ids(self):
        """TEST 09: No duplicate query IDs in benchmark dataset"""
        qids = [q["query_id"] for q in self.benchmark_queries]
        self.assertEqual(len(qids), len(set(qids)), "Duplicate query IDs found in benchmark dataset")

    def test_10_no_disabled_documents_retrieved(self):
        """TEST 10: No disabled source documents retrieved across evaluation runs"""
        for r in self.eval_results:
            cids = r["retrieved_top5_chunk_ids"].split("|") if r["retrieved_top5_chunk_ids"] else []
            for cid in cids:
                if cid:
                    sid = cid.split("-C")[0] if "-C" in cid else cid
                    self.assertNotIn(sid, self.disabled_sids, f"Disabled source {sid} retrieved in query {r['query_id']}")

    def test_11_metrics_are_finite(self):
        """TEST 11: All calculated metrics are finite (no NaN or Inf)"""
        metric_keys = ["precision@1", "precision@3", "precision@5", "recall@1", "recall@3", "recall@5", "mrr", "map", "ndcg@5", "hit_rate@5"]
        for r in self.eval_results:
            for k in metric_keys:
                v = r[k]
                self.assertFalse(math.isnan(v), f"NaN metric found for {k} in query {r['query_id']} mode {r['mode']}")
                self.assertFalse(math.isinf(v), f"Inf metric found for {k} in query {r['query_id']} mode {r['mode']}")

    def test_12_metric_ranges_valid(self):
        """TEST 12: Metric ranges are strictly between 0.0 and 1.0"""
        metric_keys = ["precision@1", "precision@3", "precision@5", "recall@1", "recall@3", "recall@5", "mrr", "map", "ndcg@5", "hit_rate@5"]
        for r in self.eval_results:
            for k in metric_keys:
                v = r[k]
                self.assertGreaterEqual(v, 0.0, f"Metric {k} < 0 in query {r['query_id']}")
                self.assertLessEqual(v, 1.0, f"Metric {k} > 1.0 in query {r['query_id']}")

    def test_13_evaluation_is_deterministic(self):
        """TEST 13: Evaluation runs produce 100% identical metric results across runs"""
        eval_run2, _ = run_evaluation_suite(self.benchmark_path)
        self.assertEqual(len(self.eval_results), len(eval_run2))
        for r1, r2 in zip(self.eval_results, eval_run2):
            self.assertEqual(r1["query_id"], r2["query_id"])
            self.assertEqual(r1["mode"], r2["mode"])
            self.assertEqual(r1["retrieved_top5_chunk_ids"], r2["retrieved_top5_chunk_ids"])
            self.assertAlmostEqual(r1["mrr"], r2["mrr"], places=6)
            self.assertAlmostEqual(r1["map"], r2["map"], places=6)

    def test_14_improvement_calculations_correct(self):
        """TEST 14: Hybrid improvement calculations match (Hybrid - Base) / Base * 100 formula"""
        self.assertEqual(format_pct(0.04, 0.02), "+100.00%")
        self.assertEqual(format_pct(0.015, 0.02), "-25.00%")
        self.assertEqual(format_pct(0.05, 0.0), "N/A")

    def test_15_frozen_assets_unchanged(self):
        """TEST 15: Zero frozen Phase 1-3.4 input assets modified"""
        ok, err = verify_hashes(self.initial_hashes)
        self.assertTrue(ok, f"Frozen asset modification detected: {err}")

def run_suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNutriKidRetrievalEvaluation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
