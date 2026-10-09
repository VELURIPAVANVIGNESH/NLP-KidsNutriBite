import os
import sys
import json
import csv
import re
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase3Chunking(unittest.TestCase):
    """Rigorous Phase 3.0-3.2 domain-aware chunking contract and quality gate verification suite."""

    def setUp(self):
        self.corpus_path = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")
        self.chunks_dir = os.path.join(BASE_DIR, "data", "processed", "chunks")
        self.manifest_path = os.path.join(BASE_DIR, "data", "metadata", "corpus_manifest.csv")
        self.report_path = os.path.join(BASE_DIR, "data", "processed", "chunker_report.csv")
        self.summary_path = os.path.join(BASE_DIR, "data", "processed", "chunker_summary.txt")

        self.assertTrue(os.path.exists(self.corpus_path), f"Unified corpus JSON missing: {self.corpus_path}")
        self.assertTrue(os.path.exists(self.chunks_dir), f"Chunks directory missing: {self.chunks_dir}")

    def test_01_total_chunk_count_and_file_parity(self):
        """Verify exactly 6,422 total chunks in preprocessed_corpus.json and 22 chunk files in chunks/."""
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        self.assertEqual(len(corpus), 6422, f"Expected exactly 6,422 chunks in preprocessed_corpus.json, found {len(corpus)}")

        chunk_files = [f for f in os.listdir(self.chunks_dir) if f.endswith("_chunks.json")]
        self.assertEqual(len(chunk_files), 22, f"Expected 22 document chunk JSON files, found {len(chunk_files)}")

    def test_02_chunk_id_format_and_uniqueness(self):
        """Verify chunk ID format {source_id}-C{index:05d} and 100% global uniqueness."""
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        seen_ids = set()
        chunk_id_pattern = re.compile(r'^NK-\d{3}-C\d{5}$')

        for c in corpus:
            cid = c.get("chunk_id")
            self.assertTrue(cid, "Missing chunk_id in corpus entry")
            self.assertTrue(chunk_id_pattern.match(cid), f"Invalid chunk_id format '{cid}'")
            self.assertNotIn(cid, seen_ids, f"Duplicate chunk_id detected: '{cid}'")
            seen_ids.add(cid)

        self.assertEqual(len(seen_ids), 6422, "Unique chunk ID count does not match total chunk count")

    def test_03_chunk_text_length_and_non_emptiness(self):
        """Verify zero empty chunks and compliance with average/target length bounds."""
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        empty_chunks = []
        oversized_chunks = []
        total_len = 0

        for c in corpus:
            txt = c.get("text", "")
            cid = c.get("chunk_id")
            c_len = len(txt)
            total_len += c_len

            if not txt.strip():
                empty_chunks.append(cid)

            # Flag extremely oversized chunks (>5000 chars)
            if c_len > 5000:
                oversized_chunks.append((cid, c_len))

        avg_len = total_len / float(len(corpus))

        self.assertEqual(len(empty_chunks), 0, f"Found empty chunks: {empty_chunks}")
        self.assertEqual(len(oversized_chunks), 0, f"Found extremely oversized chunks (>5000 chars): {oversized_chunks}")
        self.assertGreaterEqual(avg_len, 600.0, f"Average chunk length ({avg_len:.1f}) is below minimum target")
        self.assertLessEqual(avg_len, 1100.0, f"Average chunk length ({avg_len:.1f}) is above maximum target")

    def test_04_metadata_inheritance_and_page_provenance(self):
        """Verify 100% inheritance of manifest metadata fields and non-empty page numbers."""
        mandatory_fields = [
            "chunk_id", "source_id", "source_name", "file_name", "relative_path",
            "page_numbers", "publisher", "publication_year", "document_type",
            "authority_tier", "domain", "text"
        ]

        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        for c in corpus:
            cid = c.get("chunk_id")
            for field in mandatory_fields:
                self.assertIn(field, c, f"Missing metadata field '{field}' in chunk '{cid}'")

            pages = c.get("page_numbers")
            self.assertIsInstance(pages, list, f"page_numbers is not a list in '{cid}'")
            self.assertGreater(len(pages), 0, f"Empty page_numbers list in '{cid}'")
            for p in pages:
                self.assertIsInstance(p, int, f"Page number in '{cid}' is not an int: {p}")
                self.assertGreater(p, 0, f"Invalid page number in '{cid}': {p}")

    def test_05_ifct_tabular_chunking_verification(self):
        """Verify specialized table row chunking and category context prefix in NK-010 (IFCT_BOOK)."""
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)

        ifct_chunks = [c for c in corpus if c["source_id"] == "NK-010"]
        self.assertGreater(len(ifct_chunks), 100, f"Expected >100 IFCT chunks, found {len(ifct_chunks)}")

        table_chunks = [c for c in ifct_chunks if "Category:" in c.get("context_prefix", "")]
        self.assertGreater(len(table_chunks), 50, f"Expected >50 IFCT category-prefixed table chunks, found {len(table_chunks)}")

        # Verify presence of food codes in table chunks
        code_pattern = re.compile(r'[A-Z]\d{3}')
        chunks_with_codes = sum(1 for c in table_chunks if code_pattern.search(c["text"]))
        self.assertGreater(chunks_with_codes, 40, "IFCT table chunks missing expected food row codes")

if __name__ == "__main__":
    unittest.main()
