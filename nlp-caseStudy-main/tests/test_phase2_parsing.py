import os
import sys
import json
import csv
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase2DocumentParsing(unittest.TestCase):
    """Rigorous Phase 2 PDF parsing contract and quality gate verification suite."""

    def setUp(self):
        self.manifest_path = os.path.join(BASE_DIR, "data", "metadata", "corpus_manifest.csv")
        self.parsed_dir = os.path.join(BASE_DIR, "data", "processed", "parsed")
        self.report_path = os.path.join(BASE_DIR, "data", "processed", "parser_report.csv")
        self.summary_path = os.path.join(BASE_DIR, "data", "processed", "parser_summary.txt")

        self.assertTrue(os.path.exists(self.manifest_path), "Corpus manifest file missing")
        self.assertTrue(os.path.exists(self.parsed_dir), "Parsed JSON output directory missing")

    def test_01_parsed_json_file_count_parity(self):
        """Verify exactly 22 parsed JSON files corresponding to 22 active retrieval documents."""
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            active_sids = [r["source_id"] for r in reader if r["retrieval_enabled"].lower() == "true"]

        self.assertEqual(len(active_sids), 22, f"Expected 22 active documents in manifest, found {len(active_sids)}")

        parsed_files = [f for f in os.listdir(self.parsed_dir) if f.endswith("_parsed.json")]
        self.assertEqual(len(parsed_files), 22, f"Expected 22 parsed JSON files, found {len(parsed_files)}")

        expected_json_names = set(f"{sid}_parsed.json" for sid in active_sids)
        actual_json_names = set(parsed_files)
        self.assertEqual(expected_json_names, actual_json_names, "Parsed JSON filenames do not match active source IDs in manifest")

    def test_02_parsed_json_schema_and_metadata_inheritance(self):
        """Verify schema fields, metadata inheritance, and non-empty page structures."""
        for fname in os.listdir(self.parsed_dir):
            if not fname.endswith("_parsed.json"):
                continue

            fpath = os.path.join(self.parsed_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sid = data.get("source_id")
            self.assertTrue(sid and sid.startswith("NK-"), f"Missing or invalid source_id in {fname}")
            self.assertTrue(data.get("source_name"), f"Missing source_name in {fname}")
            self.assertTrue(data.get("file_name"), f"Missing file_name in {fname}")
            self.assertTrue(data.get("relative_path"), f"Missing relative_path in {fname}")

            meta = data.get("metadata", {})
            self.assertIn("publisher", meta, f"Missing publisher metadata in {fname}")
            self.assertIn("publication_year", meta, f"Missing publication_year metadata in {fname}")
            self.assertIn("document_type", meta, f"Missing document_type metadata in {fname}")
            self.assertIn("authority_tier", meta, f"Missing authority_tier metadata in {fname}")
            self.assertIn("domain", meta, f"Missing domain metadata in {fname}")
            self.assertIn("age_min", meta, f"Missing age_min metadata in {fname}")
            self.assertIn("age_max", meta, f"Missing age_max metadata in {fname}")
            self.assertEqual(meta.get("retrieval_enabled"), "true", f"retrieval_enabled must be true in active parsed JSON {fname}")

            pages = data.get("pages", [])
            self.assertGreater(len(pages), 0, f"No pages extracted in {fname}")
            self.assertEqual(len(pages), meta.get("total_pages"), f"Page list length does not match total_pages metadata in {fname}")

            # Check page numbering sequence
            for idx, p in enumerate(pages):
                self.assertEqual(p.get("page_number"), idx + 1, f"Non-sequential page number in {fname}")
                self.assertIsNotNone(p.get("text"), f"Null text on page {idx+1} in {fname}")

    def test_03_zero_text_corruption_replacement_characters(self):
        """Verify zero unicode replacement characters (\ufffd) across all extracted text buffers."""
        corrupted_pages = []
        for fname in os.listdir(self.parsed_dir):
            if not fname.endswith("_parsed.json"):
                continue

            fpath = os.path.join(self.parsed_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sid = data.get("source_id")
            for p in data.get("pages", []):
                p_text = p.get("text", "")
                if "\ufffd" in p_text or "\uFFFD" in p_text:
                    corrupted_pages.append((sid, p.get("page_number")))

        self.assertEqual(len(corrupted_pages), 0, f"Found corrupted text pages with unicode replacement characters: {corrupted_pages}")

    def test_04_key_document_content_and_numerical_preservation(self):
        """Verify extraction of key tabular documents (IFCT_BOOK and RDA brief_note)."""
        # 1. Test NK-010 (IFCT_BOOK.pdf)
        ifct_path = os.path.join(self.parsed_dir, "NK-010_parsed.json")
        self.assertTrue(os.path.exists(ifct_path), "NK-010_parsed.json (IFCT_BOOK) missing")
        with open(ifct_path, 'r', encoding='utf-8') as f:
            ifct_data = json.load(f)
        full_ifct_text = " ".join(p["text"] for p in ifct_data["pages"])
        self.assertIn("Protein", full_ifct_text, "IFCT text missing 'Protein'")
        self.assertIn("Calcium", full_ifct_text, "IFCT text missing 'Calcium'")

        # 2. Test NK-008 (brief_note.pdf - RDA/EAR reference)
        rda_path = os.path.join(self.parsed_dir, "NK-008_parsed.json")
        self.assertTrue(os.path.exists(rda_path), "NK-008_parsed.json (brief_note) missing")
        with open(rda_path, 'r', encoding='utf-8') as f:
            rda_data = json.load(f)
        full_rda_text = " ".join(p["text"] for p in rda_data["pages"])
        self.assertTrue("RDA" in full_rda_text or "EAR" in full_rda_text, "RDA/EAR text missing key nutrient standards keywords")

    def test_05_parser_reports_and_summaries_exist(self):
        """Verify parser_report.csv and parser_summary.txt deliverables."""
        self.assertTrue(os.path.exists(self.report_path), f"Report CSV missing: {self.report_path}")
        self.assertTrue(os.path.exists(self.summary_path), f"Summary TXT missing: {self.summary_path}")

        with open(self.report_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            report_rows = list(reader)
        self.assertEqual(len(report_rows), 22, f"Expected 22 report rows, found {len(report_rows)}")

if __name__ == "__main__":
    unittest.main()
