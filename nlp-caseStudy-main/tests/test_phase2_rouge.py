"""
tests/test_phase2_rouge.py — Phase 2 ROUGE Evaluation Tests
"""
import os, sys, json, unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase2ROUGE(unittest.TestCase):

    def test_01_rouge_module_imports(self):
        from generation import rouge_evaluation
        self.assertTrue(hasattr(rouge_evaluation, "compute_rouge"))
        self.assertTrue(hasattr(rouge_evaluation, "run_rouge_evaluation"))

    def test_02_benchmark_dataset_loads(self):
        bench_path = os.path.join(BASE_DIR, "data", "eval", "generation_benchmark.json")
        self.assertTrue(os.path.exists(bench_path), "generation_benchmark.json not found")
        with open(bench_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        for item in data:
            for k in ["query_id", "question", "reference_answer"]:
                self.assertIn(k, item)

    def test_03_rouge1_computed(self):
        from generation.rouge_evaluation import compute_rouge
        generated = "The recommended protein intake for children is 31 grams per day."
        reference = "Children aged 10-12 years need approximately 31-32 grams of protein daily."
        scores = compute_rouge(generated, reference)
        self.assertIn("rouge1", scores)
        self.assertIn("fmeasure", scores["rouge1"])
        self.assertGreaterEqual(scores["rouge1"]["fmeasure"], 0.0)
        self.assertLessEqual(scores["rouge1"]["fmeasure"], 1.0)

    def test_04_rouge2_computed(self):
        from generation.rouge_evaluation import compute_rouge
        generated = "Protein requirement for age 10 is 31g per day."
        reference = "Protein requirement for children aged 10 is approximately 31g per day."
        scores = compute_rouge(generated, reference)
        self.assertIn("rouge2", scores)
        self.assertGreaterEqual(scores["rouge2"]["fmeasure"], 0.0)

    def test_05_rougeL_computed(self):
        from generation.rouge_evaluation import compute_rouge
        generated = "Children need 31g protein daily."
        reference = "Children need approximately 31 grams of protein every day."
        scores = compute_rouge(generated, reference)
        self.assertIn("rougeL", scores)
        self.assertGreaterEqual(scores["rougeL"]["fmeasure"], 0.0)

    def test_06_identical_text_gives_perfect_score(self):
        from generation.rouge_evaluation import compute_rouge
        text = "Children need 31g protein daily from quality food sources."
        scores = compute_rouge(text, text)
        self.assertAlmostEqual(scores["rouge1"]["fmeasure"], 1.0, places=2)

    def test_07_grounding_evaluation(self):
        from generation.rouge_evaluation import evaluate_grounding
        evidence = [{"text": "The recommended protein intake for children is 31g per day."}]
        gen = "Recommended protein intake for children is 31 grams per day from the guidelines."
        result = evaluate_grounding(gen, evidence)
        self.assertIn("grounded", result)
        self.assertIn("overlap_score", result)
        self.assertIn("method", result)
        self.assertIn("heuristic", result["method"])

    def test_08_citation_correctness_evaluation(self):
        from generation.rouge_evaluation import evaluate_citations
        result = evaluate_citations("Protein is 31g [NK-015-C00013].", ["NK-015-C00013"])
        self.assertIn("all_citations_valid", result)
        self.assertTrue(result["all_citations_valid"])

    def test_09_numerical_preservation_evaluation(self):
        from generation.rouge_evaluation import evaluate_numerical_preservation
        evidence = [{"text": "Protein is 31.8 g/day for boys aged 10-12 years."}]
        gen = "The recommended amount is 31.8 g/day based on the guidelines."
        result = evaluate_numerical_preservation(gen, evidence)
        self.assertIn("preserved", result)
        self.assertIn("method", result)

    def test_10_aggregate_rouge_computed(self):
        from generation.rouge_evaluation import compute_rouge
        pairs = [
            ("Children need protein daily.", "Children need adequate protein every day."),
            ("Iron is essential for blood.", "Iron supports blood formation in children."),
            ("Calcium is needed for bones.", "Calcium supports bone development."),
        ]
        r1_scores = []
        for gen, ref in pairs:
            scores = compute_rouge(gen, ref)
            r1_scores.append(scores["rouge1"]["fmeasure"])
        avg = sum(r1_scores) / len(r1_scores)
        self.assertGreater(avg, 0.0)
        self.assertLessEqual(avg, 1.0)

if __name__ == "__main__":
    unittest.main()
