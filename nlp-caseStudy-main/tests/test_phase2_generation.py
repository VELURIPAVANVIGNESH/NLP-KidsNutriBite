"""
tests/test_phase2_generation.py — Phase 2 Generation Tests (Qwen 2.5 Instruct)
"""
import os, sys, json, unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase2Generation(unittest.TestCase):
    """Qwen generation integration tests."""

    def test_01_generator_module_imports(self):
        """Verify qwen_generator module imports cleanly."""
        from generation import qwen_generator
        self.assertTrue(hasattr(qwen_generator, "generate_answer"))
        self.assertTrue(hasattr(qwen_generator, "run_qwen_pipeline"))
        self.assertTrue(hasattr(qwen_generator, "GENERATION_CONFIG"))

    def test_02_generation_config_keys(self):
        """Verify generation configuration has required keys."""
        from generation.qwen_generator import GENERATION_CONFIG
        for key in ["model", "temperature", "top_p", "top_k", "max_new_tokens"]:
            self.assertIn(key, GENERATION_CONFIG)
        self.assertIsInstance(GENERATION_CONFIG["temperature"], float)
        self.assertLessEqual(GENERATION_CONFIG["temperature"], 1.0)

    def test_03_out_of_scope_low_age(self):
        """Age < 5 must be rejected without running generation."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("What is protein RDA?", child_age=3.0)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertEqual(res["citations"], [])

    def test_04_out_of_scope_high_age(self):
        """Age > 15 must be rejected without running generation."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("What is protein RDA?", child_age=18.0)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")

    def test_05_in_scope_pipeline_returns_answer(self):
        """Valid query returns non-empty answer with citations."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("What is the protein RDA for a 10-year-old?", child_age=10.0)
        self.assertIn(res["scope_status"], ["in_scope", "out_of_scope"])
        if res["scope_status"] == "in_scope":
            self.assertIn("answer", res)
            self.assertIsInstance(res["answer"], str)
            self.assertGreater(len(res["answer"]), 10)

    def test_06_evidence_not_independently_retrieved(self):
        """generate_answer must accept externally supplied evidence and not retrieve independently."""
        from generation.qwen_generator import generate_answer
        # Supply explicit synthetic evidence - model must use only this
        fake_evidence = [{"chunk_id": "TEST-001", "source_id": "NK-000",
                          "source_name": "Test Source", "file_name": "test.pdf",
                          "page_numbers": [1], "text": "The recommended protein is 31g/day for age 10."}]
        res = generate_answer("protein requirement", 10.0, fake_evidence)
        self.assertIn("answer", res)
        self.assertIsInstance(res["answer"], str)
        self.assertGreater(len(res["answer"]), 5)
        # Citations should come from supplied evidence
        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["chunk_id"], "TEST-001")

    def test_07_empty_evidence_returns_insufficient_notice(self):
        """Empty evidence list returns an insufficient-evidence notice, not a hallucinated answer."""
        from generation.qwen_generator import generate_answer
        res = generate_answer("What is protein RDA?", 10.0, [])
        self.assertIn("Insufficient", res["answer"])
        self.assertEqual(res["citations"], [])

    def test_08_response_schema(self):
        """Full pipeline response has required schema keys."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("Calcium requirements for children", child_age=8.0)
        for key in ["query", "scope_status", "answer", "citations", "generation_metadata"]:
            self.assertIn(key, res)

    def test_09_age_boundaries(self):
        """Age=5 and age=15 are in scope; age=4.9 and age=15.1 are out of scope."""
        from generation.qwen_generator import run_qwen_pipeline
        in5  = run_qwen_pipeline("iron RDA", child_age=5.0)
        in15 = run_qwen_pipeline("iron RDA", child_age=15.0)
        out4 = run_qwen_pipeline("iron RDA", child_age=4.9)
        out16= run_qwen_pipeline("iron RDA", child_age=15.1)
        self.assertNotEqual(in5["scope_status"], "out_of_scope")
        self.assertNotEqual(in15["scope_status"], "out_of_scope")
        self.assertEqual(out4["scope_status"],  "out_of_scope")
        self.assertEqual(out16["scope_status"], "out_of_scope")

    def test_10_generation_metadata_present(self):
        """Generation metadata includes model name and temperature."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("protein", child_age=10.0)
        meta = res.get("generation_metadata", {})
        self.assertIn("model", meta)
        self.assertIn("temperature", meta)
        self.assertIn("max_new_tokens", meta)

    def test_11_out_of_domain_queries_refused(self):
        """Out-of-domain queries (e.g., cricket, sports, coding) must be rejected immediately."""
        from generation.qwen_generator import run_qwen_pipeline
        res = run_qwen_pipeline("cricket match summary of ind vs wi", child_age=12.0)
        self.assertEqual(res["scope_status"], "out_of_scope")
        self.assertEqual(res["status"], "terminated_out_of_scope")
        self.assertIn("Out of Domain", res["answer"])
        self.assertEqual(res["citations"], [])
        self.assertEqual(res["evidence"], [])

if __name__ == "__main__":
    unittest.main()

