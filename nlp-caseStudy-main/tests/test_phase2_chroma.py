"""
tests/test_phase2_chroma.py — Phase 2 ChromaDB + FAISS Similarity Tests
"""
import os, sys, json, unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

CORPUS_PATH = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")

class TestChromaDB(unittest.TestCase):
    """ChromaDB vector search tests."""

    def test_01_chroma_module_imports(self):
        from generation import chroma_retriever
        self.assertTrue(hasattr(chroma_retriever, "similarity_search_chroma"))
        self.assertTrue(hasattr(chroma_retriever, "build_chroma_collection"))

    def test_02_chroma_collection_builds(self):
        """ChromaDB collection can be built/loaded."""
        from generation.chroma_retriever import build_chroma_collection
        col = build_chroma_collection(force_rebuild=False)
        self.assertIsNotNone(col)

    def test_03_chroma_collection_size(self):
        """ChromaDB collection contains all 6,422 canonical chunks."""
        from generation.chroma_retriever import build_chroma_collection
        col = build_chroma_collection(force_rebuild=False)
        count = col.count()
        self.assertEqual(count, 6422, f"Expected 6422 chunks, got {count}")

    def test_04_chroma_similarity_search_works(self):
        """ChromaDB similarity search returns non-empty results."""
        from generation.chroma_retriever import similarity_search_chroma
        results = similarity_search_chroma("protein requirements for children", k=5)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_05_chroma_k_respected(self):
        """ChromaDB respects the k parameter."""
        from generation.chroma_retriever import similarity_search_chroma
        for k in [1, 3, 5, 10]:
            results = similarity_search_chroma("calcium", k=k)
            self.assertLessEqual(len(results), k)
            self.assertGreater(len(results), 0)

    def test_06_chroma_results_ranked_by_score(self):
        """ChromaDB results are in descending similarity order."""
        from generation.chroma_retriever import similarity_search_chroma
        results = similarity_search_chroma("iron deficiency in school children", k=5)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True),
                         "ChromaDB results not in descending similarity order")

    def test_07_chroma_chunk_ids_valid(self):
        """All returned chunk IDs exist in the canonical corpus."""
        from generation.chroma_retriever import similarity_search_chroma
        with open(CORPUS_PATH, encoding="utf-8") as f:
            corpus_ids = {c["chunk_id"] for c in json.load(f)}
        results = similarity_search_chroma("vitamin D for children", k=10)
        for r in results:
            self.assertIn(r["chunk_id"], corpus_ids,
                          f"Chunk ID {r['chunk_id']} not in canonical corpus")

    def test_08_chroma_metadata_preserved(self):
        """Each result contains source metadata fields."""
        from generation.chroma_retriever import similarity_search_chroma
        results = similarity_search_chroma("sodium intake guidelines", k=3)
        for r in results:
            self.assertIn("chunk_id", r)
            self.assertIn("score", r)
            self.assertIn("text", r)
            self.assertIn("metadata", r)
            self.assertIn("source", r["metadata"])

    def test_09_chroma_deterministic(self):
        """Same query returns same results on repeated calls."""
        from generation.chroma_retriever import similarity_search_chroma
        q = "carbohydrate intake for children"
        r1 = [x["chunk_id"] for x in similarity_search_chroma(q, k=5)]
        r2 = [x["chunk_id"] for x in similarity_search_chroma(q, k=5)]
        self.assertEqual(r1, r2, "ChromaDB is not deterministic for identical queries")

    def test_10_faiss_similarity_search_works(self):
        """FAISS similarity_search_faiss returns valid results."""
        from generation.chroma_retriever import similarity_search_faiss
        results = similarity_search_faiss("protein for children", k=5)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        with open(CORPUS_PATH, encoding="utf-8") as f:
            corpus_ids = {c["chunk_id"] for c in json.load(f)}
        for r in results:
            self.assertIn(r["chunk_id"], corpus_ids)

    def test_11_faiss_k_respected(self):
        """FAISS respects the k parameter."""
        from generation.chroma_retriever import similarity_search_faiss
        results = similarity_search_faiss("iron", k=3)
        self.assertLessEqual(len(results), 3)

    def test_12_faiss_does_not_modify_index(self):
        """Running FAISS search does not alter the frozen index file mtime."""
        import os, time
        idx_path = os.path.join(BASE_DIR, "data", "processed", "dense_index.faiss")
        mtime_before = os.path.getmtime(idx_path)
        from generation.chroma_retriever import similarity_search_faiss
        similarity_search_faiss("calcium", k=5)
        mtime_after = os.path.getmtime(idx_path)
        self.assertEqual(mtime_before, mtime_after, "FAISS index was modified during search!")

    def test_13_both_use_same_corpus(self):
        """FAISS and ChromaDB return chunk IDs from the same canonical 6,422-chunk corpus."""
        from generation.chroma_retriever import similarity_search_faiss, similarity_search_chroma
        with open(CORPUS_PATH, encoding="utf-8") as f:
            corpus_ids = {c["chunk_id"] for c in json.load(f)}
        q = "energy requirements for adolescents"
        f_ids  = {r["chunk_id"] for r in similarity_search_faiss(q,  k=10)}
        ch_ids = {r["chunk_id"] for r in similarity_search_chroma(q, k=10)}
        for cid in (f_ids | ch_ids):
            self.assertIn(cid, corpus_ids, f"Chunk {cid} not in canonical corpus")

    def test_14_benchmark_annotations_unchanged(self):
        """Running vector search does not modify the benchmark annotation file."""
        import json, os
        bench_path = os.path.join(BASE_DIR, "data", "eval", "evaluation_queries.json")
        with open(bench_path, encoding="utf-8") as f:
            before = json.load(f)
        from generation.chroma_retriever import similarity_search_chroma
        similarity_search_chroma("test query", k=2)
        with open(bench_path, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual(before, after, "Benchmark annotations were modified by vector search!")

if __name__ == "__main__":
    unittest.main()
