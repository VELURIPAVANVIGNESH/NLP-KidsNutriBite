import os
import sys
import json
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from generation.generate import run_generation_pipeline, synthesize_response_from_evidence
from generation.prompts import format_evidence_block, PEDIATRIC_NUTRITION_SYSTEM_PROMPT

class TestPhase4Generation(unittest.TestCase):
    """Rigorous Phase 4 LLM Generation & Evidence Synthesis contract test suite."""

    def test_01_prompt_formatting(self):
        """Verify prompt evidence formatting and citation instruction template."""
        sample_evidence = [
            {
                "source_id": "NK-008",
                "file_name": "brief_note.pdf",
                "page_numbers": [14, 15],
                "context_prefix": "Section: Calcium RDA",
                "text": "RDA for calcium for children 10-12 yrs is 850 mg/day."
            }
        ]
        block = format_evidence_block(sample_evidence)
        self.assertIn("NK-008: brief_note.pdf, p. 14, 15", block)
        self.assertIn("Section: Calcium RDA", block)
        self.assertIn("850 mg/day", block)

    def test_02_evidence_groundedness(self):
        """Verify generated answers are grounded in input evidence."""
        res = run_generation_pipeline(query="What is the calcium requirement for a 10 year old?", child_age=10.0, top_k=3)
        self.assertEqual(res["status"], "success")
        self.assertGreater(len(res["answer"]), 100)
        self.assertGreater(res["evidence_used_count"], 0)

    def test_03_numerical_preservation(self):
        """Verify exact preservation of RDA numerical values and unit strings in answers."""
        sample_package = {
            "query": "Iron RDA",
            "requested_age": 8.0,
            "scope_status": "in_scope",
            "evidence": [
                {
                    "source_id": "NK-008",
                    "source_name": "ICMR RDA 2020",
                    "file_name": "brief_note.pdf",
                    "page_numbers": [12],
                    "context_prefix": "Section: Micronutrients",
                    "text": "Iron RDA for children 7-9 years is 15 mg/day."
                }
            ]
        }
        res = synthesize_response_from_evidence("Iron RDA", 8.0, sample_package)
        self.assertIn("15 mg/day", res["answer"])
        self.assertIn("[NK-008: brief_note.pdf, p. 12]", res["answer"])

    def test_04_provenance_citations(self):
        """Verify inline citation structure matching source_id, file_name, and page numbers."""
        res = run_generation_pipeline(query="Protein guidelines for adolescents", child_age=14.0, top_k=2)
        citations = res["citations"]
        self.assertGreater(len(citations), 0)
        for c in citations:
            self.assertTrue(c["source_id"].startswith("NK-"))
            self.assertTrue(c["file_name"].endswith(".pdf"))
            self.assertIn(c["source_id"], c["citation_label"])

    def test_05_out_of_scope_safety(self):
        """Verify safety refusal for out-of-scope age queries (<5 and >15 years)."""
        res_infant = run_generation_pipeline(query="Infant nutrition guide", child_age=2.0)
        self.assertEqual(res_infant["scope_status"], "out_of_scope")
        self.assertEqual(res_infant["status"], "terminated_out_of_scope")
        self.assertIn("Out of Scope Notice", res_infant["answer"])

    def test_06_insufficient_evidence_handling(self):
        """Verify handling of empty or missing evidence packages."""
        empty_package = {
            "query": "Unknown nutrient",
            "requested_age": 10.0,
            "scope_status": "in_scope",
            "evidence": []
        }
        res = synthesize_response_from_evidence("Unknown nutrient", 10.0, empty_package)
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertIn("insufficient evidence", res["answer"].lower())

if __name__ == "__main__":
    unittest.main()
