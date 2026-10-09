"""
Direct pipeline verification (no LLM) - confirms BM25+Dense+RRF+Reranker results
after the enriched retrieval text index rebuild.
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

from preprocessing.retrieve import run_retrieval
from preprocessing.rerank import run_reranking

QUERY = "What is the protein requirement for a 10-year-old child?"
AGE = 10.0
TARGET = "NK-015-C00013"
WRONG  = "NK-021-C00582"

print("=" * 60)
print("RETRIEVAL PIPELINE VERIFICATION (Post-Fix)")
print("=" * 60)
print(f"Query: {QUERY}")
print(f"Age:   {AGE}")
print()

# Step 1: BM25 + Dense + RRF (top 100)
rrf_result = run_retrieval(
    query=QUERY,
    child_age=AGE,
    mode="hybrid",
    top_k=20,
    candidate_k=100,
    skip_hash_check=True
)

print(f"RRF Status: {rrf_result['status']}")
print()

print("--- Top 15 RRF Results ---")
target_rrf_rank = None
wrong_rrf_rank  = None
for r in rrf_result["results"][:15]:
    cid = r["chunk_id"]
    label = ""
    if cid == TARGET:
        label = "  <-- [TARGET] NK-015 Protein RDA Table 2a"
        target_rrf_rank = r["rank"]
    elif cid == WRONG:
        label = "  <-- [WRONG]  NK-021 Iodine"
        wrong_rrf_rank = r["rank"]
    print(f"  RRF Rank {r['rank']:2d}: {cid}  BM25={r['sparse_rank']}  Dense={r['dense_rank']}  RRF={r['rrf_score']:.6f}{label}")

print()
print(f"NK-015-C00013 (Protein RDA) RRF rank: {target_rrf_rank}")
print(f"NK-021-C00582 (Iodine)      RRF rank: {wrong_rrf_rank}")
print()

# Step 2: Full reranking pipeline (run_reranking calls retrieve internally)
print("--- Running Cross-Encoder Reranker (top 50 -> top 5) ---")
rerank_result = run_reranking(
    query=QUERY,
    child_age=AGE,
    candidate_k=50,
    top_k=5,
)

print(f"Rerank Status: {rerank_result['status']}")
print()
print("--- Top 5 Reranker Results ---")
target_rerank_rank = None
wrong_rerank_rank  = None
for r in rerank_result["results"]:
    cid = r["chunk_id"]
    rank = r["rank"]
    label = ""
    if cid == TARGET:
        label = "  <-- [TARGET] NK-015 Protein RDA Table 2a"
        target_rerank_rank = rank
    elif cid == WRONG:
        label = "  <-- [WRONG]  NK-021 Iodine"
        wrong_rerank_rank = rank
    score = r.get("cross_encoder_score", r.get("score", "?"))
    pages = r.get("page_numbers", "?")
    text_snip = r.get("text", "")[:120].strip()
    print(f"  Rerank Rank {rank}: {cid}  score={score}  pages={pages}{label}")
    print(f"            text: {text_snip}")
    print()

print(f"NK-015-C00013 (Protein RDA) Rerank rank: {target_rerank_rank}")
print(f"NK-021-C00582 (Iodine)      Rerank rank: {wrong_rerank_rank}")
print()

# Verdict
print("=" * 60)
print("VERDICT")
print("=" * 60)
if target_rrf_rank is not None and target_rrf_rank <= 10:
    print(f"[PASS] NK-015-C00013 in RRF Top-10 (rank {target_rrf_rank})")
else:
    print(f"[FAIL] NK-015-C00013 NOT in RRF Top-10 (rank={target_rrf_rank})")

if target_rerank_rank is not None and target_rerank_rank <= 5:
    print(f"[PASS] NK-015-C00013 in Reranker Top-5 (rank {target_rerank_rank})")
else:
    print(f"[FAIL] NK-015-C00013 NOT in Reranker Top-5 (rank={target_rerank_rank})")

if wrong_rerank_rank is None:
    print(f"[PASS] NK-021-C00582 (Iodine) NOT in Reranker Top-5")
else:
    print(f"[INFO] NK-021-C00582 (Iodine) still appears at Reranker rank {wrong_rerank_rank}")

# Save
out = {
    "query": QUERY,
    "age": AGE,
    "rrf_results_top15": rrf_result["results"][:15],
    "reranked_top5": rerank_result["results"],
    "target_rrf_rank": target_rrf_rank,
    "wrong_rrf_rank": wrong_rrf_rank,
    "target_rerank_rank": target_rerank_rank,
    "wrong_rerank_rank": wrong_rerank_rank,
}
with open("scratch/pipeline_verification_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print()
print("Full result saved to scratch/pipeline_verification_result.json")
