import time
import json
import os
import sys

BASE_DIR = os.path.abspath(".")
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval
from preprocessing.rerank import run_reranking
from preprocessing.context_refiner import refine_context

query = "What is the recommended dietary allowance for protein for a 10-year-old child?"
child_age = 10.0

print("=== MEASURING RETRIEVAL & RERANKING LATENCY ===")

# 1. BM25 alone
t0 = time.time()
res_bm25 = run_retrieval(query, child_age=child_age, mode="bm25", top_k=5, skip_hash_check=True)
t_bm25 = time.time() - t0
print(f"1. BM25 Retrieval: {t_bm25:.3f}s (results: {len(res_bm25.get('results', []))})")

# 2. Dense alone
t0 = time.time()
res_dense = run_retrieval(query, child_age=child_age, mode="dense", top_k=5, skip_hash_check=True)
t_dense = time.time() - t0
print(f"2. Dense FAISS Retrieval: {t_dense:.3f}s (results: {len(res_dense.get('results', []))})")

# 3. Hybrid RRF alone
t0 = time.time()
res_hybrid = run_retrieval(query, child_age=child_age, mode="hybrid", top_k=50, candidate_k=50, skip_hash_check=True)
t_hybrid = time.time() - t0
print(f"3. Hybrid RRF Retrieval (k=50): {t_hybrid:.3f}s (results: {len(res_hybrid.get('results', []))})")

# 4. Neural Cross-Encoder Reranking
t0 = time.time()
rerank_out = run_reranking(query=query, child_age=child_age, candidate_k=50, top_k=5)
t_rerank = time.time() - t0
print(f"4. BGE Cross-Encoder Reranking: {t_rerank:.3f}s (results: {len(rerank_out.get('results', []))})")

# 5. Context Refinement
t0 = time.time()
refined = refine_context(rerank_out)
t_refine = time.time() - t0
print(f"5. Context Refiner: {t_refine:.3f}s (evidence items: {len(refined.get('evidence', []))})")

print("\n=== TOP 5 REFINED EVIDENCE CHUNKS ===")
for ev in refined.get("evidence", []):
    print(f"Rank {ev.get('rank')}: Chunk {ev.get('chunk_id')} | Score: {ev.get('reranker_score', 0):.4f} | Source: {ev.get('source_id')} | Pages: {ev.get('page_numbers')}")
    print(f"   Text snippet: {ev.get('text', '')[:120]}...\n")
