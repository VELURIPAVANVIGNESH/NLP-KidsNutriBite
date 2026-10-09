import unittest
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.context_refiner import refine_context, compute_jaccard_similarity

class TestContextRefiner(unittest.TestCase):

    def test_01_exact_duplicate_removal(self):
        """Assert exact chunk IDs are deduplicated."""
        sample_input = {
            "query": "Calcium requirement",
            "requested_age": 10.0,
            "scope_status": "in_scope",
            "results": [
                {"rank": 1, "chunk_id": "C1", "reranker_score": 2.5, "text": "Calcium recommendation for children is 850 mg/day."},
                {"rank": 2, "chunk_id": "C1", "reranker_score": 2.5, "text": "Calcium recommendation for children is 850 mg/day."},
                {"rank": 3, "chunk_id": "C2", "reranker_score": 1.8, "text": "Iron allowance for adolescents is 16 mg/day."}
            ]
        }
        refined = refine_context(sample_input)
        self.assertEqual(refined["refinement_stats"]["exact_duplicates_removed"], 1)
        self.assertEqual(len(refined["evidence"]), 2)
        self.assertEqual(refined["evidence"][0]["chunk_id"], "C1")
        self.assertEqual(refined["evidence"][1]["chunk_id"], "C2")

    def test_02_near_duplicate_text_detection(self):
        """Assert near-duplicate text chunks (Jaccard > 0.85) are filtered out."""
        text_a = "Recommended dietary allowance for calcium in children aged 10-12 years is 850 mg per day according to ICMR NIN guidelines."
        text_b = "Recommended dietary allowance for calcium in children aged 10-12 years is 850 mg per day according to ICMR NIN 2020 guidelines."
        
        sim = compute_jaccard_similarity(text_a, text_b)
        self.assertGreater(sim, 0.85)
        
        sample_input = {
            "query": "Calcium requirement",
            "requested_age": 10.0,
            "scope_status": "in_scope",
            "results": [
                {"rank": 1, "chunk_id": "C1", "reranker_score": 2.5, "text": text_a},
                {"rank": 2, "chunk_id": "C2", "reranker_score": 2.4, "text": text_b}
            ]
        }
        refined = refine_context(sample_input, near_duplicate_threshold=0.85)
        self.assertEqual(refined["refinement_stats"]["near_duplicates_removed"], 1)
        self.assertEqual(len(refined["evidence"]), 1)

    def test_03_preservation_of_numerical_values_and_provenance(self):
        """Assert numeric values, units, page numbers, and provenance are preserved."""
        text_with_numbers = "Daily Iron RDA is 16.5 mg/day (±0.5) for ages 10-15."
        sample_input = {
            "query": "Iron RDA",
            "requested_age": 12.0,
            "scope_status": "in_scope",
            "results": [
                {
                    "rank": 1,
                    "chunk_id": "NK-021-C001",
                    "source_id": "NK-021",
                    "source_name": "Human Vitamin Requirements",
                    "file_name": "Human Vitamin .pdf",
                    "page_numbers": [12, 13],
                    "reranker_score": 3.0,
                    "text": text_with_numbers
                }
            ]
        }
        refined = refine_context(sample_input)
        ev = refined["evidence"][0]
        self.assertEqual(ev["text"], text_with_numbers)
        self.assertIn("16.5 mg/day (±0.5)", ev["text"])
        self.assertEqual(ev["page_numbers"], [12, 13])
        self.assertEqual(ev["source_id"], "NK-021")

    def test_04_out_of_scope_and_empty_input(self):
        """Assert out of scope inputs yield empty evidence cleanly."""
        sample_input = {
            "query": "Infant formula",
            "requested_age": 2.0,
            "scope_status": "out_of_scope",
            "results": []
        }
        refined = refine_context(sample_input)
        self.assertEqual(refined["scope_status"], "out_of_scope")
        self.assertEqual(len(refined["evidence"]), 0)

if __name__ == "__main__":
    unittest.main()
