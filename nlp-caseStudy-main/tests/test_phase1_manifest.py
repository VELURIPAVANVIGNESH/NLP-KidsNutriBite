import os
import sys
import csv
import hashlib
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase1CorpusManifest(unittest.TestCase):
    """Rigorous Phase 1 contract and quality gate verification suite."""

    def setUp(self):
        self.manifest_path = os.path.join(BASE_DIR, "data", "metadata", "corpus_manifest.csv")
        self.corpus_dir = os.path.join(BASE_DIR, "knowledge_corpus")
        self.assertTrue(os.path.exists(self.manifest_path), f"Manifest file missing: {self.manifest_path}")

    def calculate_md5(self, filepath):
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    def test_01_physical_pdf_discovery_parity(self):
        """Verify that every PDF on disk in knowledge_corpus is present in corpus_manifest.csv."""
        discovered_pdfs = []
        for root, dirs, files in os.walk(self.corpus_dir):
            for f in files:
                if f.endswith('.pdf'):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, BASE_DIR).replace('\\', '/')
                    discovered_pdfs.append(rel_path)

        self.assertEqual(len(discovered_pdfs), 32, f"Expected 32 physical PDFs on disk, found {len(discovered_pdfs)}")

        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            manifest_paths = [row["relative_path"] for row in reader]

        self.assertEqual(len(manifest_paths), 32, f"Expected 32 manifest rows, found {len(manifest_paths)}")
        self.assertEqual(set(discovered_pdfs), set(manifest_paths), "Discovered PDFs on disk do not match manifest entries")

    def test_02_schema_and_mandatory_fields(self):
        """Verify manifest CSV header schema and mandatory non-empty fields."""
        expected_headers = [
            "source_id", "source_name", "file_name", "relative_path", "folder",
            "publisher", "publication_year", "document_type", "authority_tier",
            "domain", "age_min", "age_max", "retrieval_enabled"
        ]

        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, expected_headers, "CSV fieldnames do not match expected Phase 1 schema")

            for row in reader:
                sid = row["source_id"]
                self.assertTrue(sid.startswith("NK-"), f"Source ID '{sid}' does not follow NK-xxx format")
                self.assertTrue(row["source_name"].strip(), f"Missing source_name for {sid}")
                self.assertTrue(row["file_name"].strip(), f"Missing file_name for {sid}")
                self.assertTrue(row["relative_path"].strip(), f"Missing relative_path for {sid}")
                self.assertIn(row["retrieval_enabled"].lower(), ["true", "false"], f"Invalid retrieval_enabled value for {sid}")

    def test_03_active_vs_disabled_document_counts(self):
        """Verify exactly 22 active retrieval documents and 10 disabled documents."""
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        active_rows = [r for r in rows if r["retrieval_enabled"].lower() == "true"]
        disabled_rows = [r for r in rows if r["retrieval_enabled"].lower() == "false"]

        self.assertEqual(len(active_rows), 22, f"Expected exactly 22 active retrieval documents, found {len(active_rows)}")
        self.assertEqual(len(disabled_rows), 10, f"Expected exactly 10 disabled retrieval documents, found {len(disabled_rows)}")

    def test_04_folder_retrieval_policy_enforcement(self):
        """Verify strict retrieval policy for out-of-scope, evaluation, reference, and infant folders."""
        forbidden_folders = {"03_EVALUATION_CONTEXT", "04_OUT_OF_SCOPE_INFANT", "05_REFERENCE_ONLY"}

        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                folder = row["folder"]
                fname = row["file_name"]
                ret_enabled = (row["retrieval_enabled"].lower() == "true")

                if folder in forbidden_folders:
                    self.assertFalse(ret_enabled, f"Document '{fname}' in forbidden folder '{folder}' must have retrieval_enabled=false")

                if fname == "WHO.pdf":
                    self.assertFalse(ret_enabled, "Infant growth standard 'WHO.pdf' (0-5 yrs) must have retrieval_enabled=false")

                if fname == "ref-1-txt-book.pdf":
                    self.assertFalse(ret_enabled, "Duplicate content document 'ref-1-txt-book.pdf' must have retrieval_enabled=false")

    def test_05_md5_byte_hash_integrity(self):
        """Verify MD5 hash calculation across all 32 PDFs and verify file readability."""
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rel_path = row["relative_path"]
                abs_path = os.path.join(BASE_DIR, rel_path)
                self.assertTrue(os.path.exists(abs_path), f"File referenced in manifest does not exist: {abs_path}")
                md5_hash = self.calculate_md5(abs_path)
                self.assertEqual(len(md5_hash), 32, f"MD5 hash calculation failed for {rel_path}")

if __name__ == "__main__":
    unittest.main()
