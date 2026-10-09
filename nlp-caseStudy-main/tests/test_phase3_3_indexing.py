import os
import sys
import json
import csv
import math
import numpy as np
import faiss
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase3Indexing(unittest.TestCase):
    """Rigorous Phase 3.3 dual indexing (BM25 + FAISS Dense) contract and quality gate verification suite."""

    def setUp(self):
        self.corpus_path = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")
        self.bm25_path = os.path.join(BASE_DIR, "data", "processed", "bm25_index.json")
        self.faiss_path = os.path.join(BASE_DIR, "data", "processed", "dense_index.faiss")
        self.dense_map_path = os.path.join(BASE_DIR, "data", "processed", "dense_index_map.json")

        self.assertTrue(os.path.exists(self.corpus_path), "preprocessed_corpus.json missing")
        self.assertTrue(os.path.exists(self.bm25_path), "bm25_index.json missing")
        self.assertTrue(os.path.exists(self.faiss_path), "dense_index.faiss missing")
        self.assertTrue(os.path.exists(self.dense_map_path), "dense_index_map.json missing")

    def test_01_bm25_index_schema_and_counts(self):
        """Verify BM25 index parameters, document count, and inverted index integrity."""
        with open(self.bm25_path, 'r', encoding='utf-8') as f:
            bm25 = json.load(f)

        self.assertEqual(bm25.get("k1"), 1.5, "BM25 k1 parameter mismatch")
        self.assertEqual(bm25.get("b"), 0.75, "BM25 b parameter mismatch")
        self.assertEqual(bm25.get("corpus_doc_count"), 6422, f"BM25 doc count expected 6,422, got {bm25.get('corpus_doc_count')}")

        doc_ids = bm25.get("doc_ids", [])
        self.assertEqual(len(doc_ids), 6422, f"BM25 doc_ids length expected 6,422, got {len(doc_ids)}")

        idf_dict = bm25.get("idf", {})
        self.assertGreater(len(idf_dict), 5000, f"Expected >5000 unique vocabulary terms in BM25 IDF, got {len(idf_dict)}")

    def test_02_faiss_dense_index_integrity_and_dimension(self):
        """Verify FAISS index total vector count, embedding dimension, and zero NaN/Inf."""
        index = faiss.read_index(self.faiss_path)
        self.assertEqual(index.ntotal, 6422, f"FAISS ntotal expected 6,422, got {index.ntotal}")
        self.assertEqual(index.d, 384, f"FAISS embedding dimension expected 384 (BGE-small), got {index.d}")

        # Reconstruct sample vectors (first 50 and last 50) and check L2 norms & NaN/Inf
        sample_indices = list(range(50)) + list(range(6372, 6422))
        for idx in sample_indices:
            vec = index.reconstruct(idx)
            self.assertFalse(np.isnan(vec).any(), f"NaN value found in FAISS vector at offset {idx}")
            self.assertFalse(np.isinf(vec).any(), f"Inf value found in FAISS vector at offset {idx}")

            l2_norm = float(np.linalg.norm(vec))
            self.assertAlmostEqual(l2_norm, 1.0, places=3, msg=f"Vector at offset {idx} is not L2 normalized (norm={l2_norm})")

    def test_03_bi_directional_mapping_parity(self):
        """Verify 1:1 parity across preprocessed_corpus, BM25 doc_ids, and dense_index_map."""
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
        with open(self.bm25_path, 'r', encoding='utf-8') as f:
            bm25 = json.load(f)
        with open(self.dense_map_path, 'r', encoding='utf-8') as f:
            dense_map = json.load(f)

        self.assertEqual(len(corpus), 6422)
        self.assertEqual(len(bm25["doc_ids"]), 6422)
        self.assertEqual(len(dense_map), 6422)

        for i in range(6422):
            corpus_cid = corpus[i]["chunk_id"]
            bm25_cid = bm25["doc_ids"][i]
            map_cid = dense_map[i]

            self.assertEqual(corpus_cid, bm25_cid, f"Mismatch at offset {i}: corpus='{corpus_cid}', bm25='{bm25_cid}'")
            self.assertEqual(corpus_cid, map_cid, f"Mismatch at offset {i}: corpus='{corpus_cid}', dense_map='{map_cid}'")

    def test_04_preprocessor_reports_and_summaries_exist(self):
        """Verify preprocessor_report.csv and preprocessor_summary.txt deliverables."""
        report_path = os.path.join(BASE_DIR, "data", "processed", "preprocessor_report.csv")
        summary_path = os.path.join(BASE_DIR, "data", "processed", "preprocessor_summary.txt")

        self.assertTrue(os.path.exists(report_path), "preprocessor_report.csv missing")
        self.assertTrue(os.path.exists(summary_path), "preprocessor_summary.txt missing")

        with open(report_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            report_rows = list(reader)
        self.assertEqual(len(report_rows), 6422, f"Expected 6,422 report rows, found {len(report_rows)}")

if __name__ == "__main__":
    unittest.main()
