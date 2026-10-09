"""
tests/test_phase2_api.py — Phase 2 FastAPI Endpoint Tests
Uses TestClient (no running server required).
"""
import os, sys, json, unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

class TestPhase2API(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        from api.main import app
        self.client = TestClient(app)

    def test_01_health_check(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")

    def test_02_ask_valid_request(self):
        """Valid /api/ask returns a response with required schema."""
        resp = self.client.post("/api/ask", json={"question": "What is protein RDA for children?", "age": 10.0})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ["answer", "scope_status"]:
            self.assertIn(key, data)
        self.assertIsInstance(data["answer"], str)

    def test_03_ask_out_of_scope_age(self):
        """Out-of-scope age returns scope_status=out_of_scope."""
        resp = self.client.post("/api/ask", json={"question": "protein?", "age": 2.0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["scope_status"], "out_of_scope")

    def test_04_faiss_search_returns_results(self):
        """FAISS similarity search endpoint returns results."""
        resp = self.client.post("/api/similarity-search/faiss",
                                json={"query": "calcium for children", "k": 5})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)
        self.assertGreater(len(data["results"]), 0)
        self.assertEqual(data["backend"], "faiss")

    def test_05_chroma_search_returns_results(self):
        """ChromaDB similarity search endpoint returns results."""
        resp = self.client.post("/api/similarity-search/chroma",
                                json={"query": "protein requirements", "k": 5})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)
        self.assertGreater(len(data["results"]), 0)
        self.assertEqual(data["backend"], "chromadb")

    def test_06_faiss_k_respected(self):
        """FAISS API respects k parameter."""
        resp = self.client.post("/api/similarity-search/faiss",
                                json={"query": "iron", "k": 3})
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.json()["results"]), 3)

    def test_07_chroma_k_respected(self):
        """ChromaDB API respects k parameter."""
        resp = self.client.post("/api/similarity-search/chroma",
                                json={"query": "iron", "k": 3})
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.json()["results"]), 3)

    def test_08_invalid_request_handled(self):
        """Missing required field returns 422 validation error."""
        resp = self.client.post("/api/ask", json={"age": 10.0})  # missing question
        self.assertEqual(resp.status_code, 422)

    def test_09_age_5_in_scope(self):
        resp = self.client.post("/api/ask", json={"question": "iron RDA", "age": 5.0})
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.json().get("scope_status"), "out_of_scope")

    def test_10_age_15_in_scope(self):
        resp = self.client.post("/api/ask", json={"question": "energy requirements", "age": 15.0})
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.json().get("scope_status"), "out_of_scope")

if __name__ == "__main__":
    unittest.main()
