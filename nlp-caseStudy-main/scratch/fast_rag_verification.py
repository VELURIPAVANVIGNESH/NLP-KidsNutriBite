import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval
from preprocessing.rerank import run_reranking
from preprocessing.context_refiner import refine_context
from preprocessing.retrieval_repr import generate_retrieval_text

TARGET = "NK-015-C00013"

# 1. Inspect retrieval representation of NK-015-C00013
with open(os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json"), "r", encoding="utf-8") as f:
    corpus = json.load(f)
corpus_map = {c["chunk_id"]: c for c in corpus}
target_chunk = corpus_map[TARGET]
repr_text = generate_retrieval_text(target_chunk)

print("=== 1. RETRIEVAL REPRESENTATION VERIFICATION ===")
print("Chunk ID:", TARGET)
print("Raw text len:", len(target_chunk["text"]))
print("Representation len:", len(repr_text))
print("Contains 'protein':", "protein" in repr_text.lower())
print("Contains 'RDA':", "RDA" in repr_text)
print("Contains 'Recommended Dietary Allowance':", "recommended dietary allowance" in repr_text.lower())
print("Contains '10-12 years':", "10-12 years" in repr_text.lower())
print("Contains '10-year-old' or '10, 11, 12 year old':", ("10-year-old" in repr_text.lower() or "10, 11, 12 year old" in repr_text.lower() or "10 year old" in repr_text.lower()))
print("Contains 'child':", "child" in repr_text.lower())
print("Contains 'Table 2a':", "Table 2a" in repr_text)

repr_pass = all([
    "protein" in repr_text.lower(),
    "RDA" in repr_text,
    "recommended dietary allowance" in repr_text.lower(),
    "10-12 years" in repr_text.lower(),
    ("10-year-old" in repr_text.lower() or "10, 11, 12 year old" in repr_text.lower() or "10 year old" in repr_text.lower()),
    "child" in repr_text.lower(),
    "Table 2a" in repr_text
])
print("Retrieval representation check:", "PASS" if repr_pass else "FAIL")
print()

# 2. Canonical query
q_canon = "What is the protein requirement for a 10-year-old child?"
print("=== 2. CANONICAL QUERY ===")
print("Query:", q_canon)

# BM25 rank
bm25_out = run_retrieval(q_canon, child_age=10.0, mode="bm25", top_k=50, candidate_k=100, skip_hash_check=True)
bm25_rank = next((r["rank"] for r in bm25_out["results"] if r["chunk_id"] == TARGET), None)
print("BM25 rank:", bm25_rank)

# Dense rank
dense_out = run_retrieval(q_canon, child_age=10.0, mode="dense", top_k=60, candidate_k=100, skip_hash_check=True)
dense_rank = next((r["rank"] for r in dense_out["results"] if r["chunk_id"] == TARGET), None)
print("Dense rank:", dense_rank)

# Hybrid RRF rank
hybrid_out = run_retrieval(q_canon, child_age=10.0, mode="hybrid", top_k=50, candidate_k=100, skip_hash_check=True)
rrf_rank = next((r["rank"] for r in hybrid_out["results"] if r["chunk_id"] == TARGET), None)
print("RRF rank:", rrf_rank)

# Reranker rank
rerank_out = run_reranking(q_canon, child_age=10.0, candidate_k=50, top_k=5)
rerank_rank = next((r["rank"] for r in rerank_out["results"] if r["chunk_id"] == TARGET), None)
print("Cross-encoder rank:", rerank_rank)

# Final context refiner
refined = refine_context(rerank_out)
final_evidence_cids = [e["chunk_id"] for e in refined.get("evidence", [])]
canon_top5 = TARGET in final_evidence_cids[:5]
print("Final Top-5 evidence:", final_evidence_cids)
print("NK-015-C00013 in Final Top-5:", "YES" if canon_top5 else "NO")
print()

# 3. Alternate Query 1
q_alt1 = "What is the recommended dietary allowance for protein for a 10-year-old?"
print("=== 3. ALTERNATE QUERY 1 ===")
print("Query:", q_alt1)
rerank_alt1 = run_reranking(q_alt1, child_age=10.0, candidate_k=50, top_k=5)
refined_alt1 = refine_context(rerank_alt1)
alt1_cids = [e["chunk_id"] for e in refined_alt1.get("evidence", [])]
alt1_top5 = TARGET in alt1_cids[:5]
alt1_rank = next((r["rank"] for r in rerank_alt1["results"] if r["chunk_id"] == TARGET), None)
print("Cross-encoder rank:", alt1_rank)
print("Final Top-5 evidence:", alt1_cids)
print("NK-015-C00013 in Final Top-5:", "YES" if alt1_top5 else "NO")
print()

# 4. Alternate Query 2
q_alt2 = "How much protein does a 10-year-old child need per day?"
print("=== 4. ALTERNATE QUERY 2 ===")
print("Query:", q_alt2)
rerank_alt2 = run_reranking(q_alt2, child_age=10.0, candidate_k=50, top_k=5)
refined_alt2 = refine_context(rerank_alt2)
alt2_cids = [e["chunk_id"] for e in refined_alt2.get("evidence", [])]
alt2_top5 = TARGET in alt2_cids[:5]
alt2_rank = next((r["rank"] for r in rerank_alt2["results"] if r["chunk_id"] == TARGET), None)
print("Cross-encoder rank:", alt2_rank)
print("Final Top-5 evidence:", alt2_cids)
print("NK-015-C00013 in Final Top-5:", "YES" if alt2_top5 else "NO")
print()

# Summary
print("========================================")
print("FAST RAG VERIFICATION SUMMARY")
print("========================================")
print("Canonical:")
print(f"BM25: {bm25_rank}")
print(f"Dense: {dense_rank}")
print(f"RRF: {rrf_rank}")
print(f"Reranker: {rerank_rank}")
print(f"Final Top-5: {'YES' if canon_top5 else 'NO'}")
print()
print("Alternate 1:")
print(f"Final Top-5: {'YES' if alt1_top5 else 'NO'}")
print()
print("Alternate 2:")
print(f"Final Top-5: {'YES' if alt2_top5 else 'NO'}")
print()
print("Ground truth:")
print("NK-015-C00013")
print("Page 5")
print("Table 2a")
print("31.8 g/day boys")
print("32.8 g/day girls")
print()
print("Retrieval representation:")
print("PASS" if repr_pass else "FAIL")
print()
all_pass = canon_top5 and alt1_top5 and alt2_top5 and repr_pass
print("FINAL RETRIEVAL STATUS:")
print("PASS" if all_pass else "FAIL")
