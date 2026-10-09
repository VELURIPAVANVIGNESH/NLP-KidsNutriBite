"""
Final protein pipeline trace.
Stages: BM25 | Dense | RRF (inside run_retrieval hybrid) | Reranker | Context Refiner
NO LLM generation — retrieval only.
"""
import sys, json
sys.path.insert(0, ".")

QUERY   = "What is the protein requirement for a 10-year-old child?"
AGE     = 10.0
IODINE  = "NK-021-C00582"
SEP     = "=" * 65

CONFIG  = "preprocessing/config.json"

# ────────────────────────────────────────────────
# STAGE 1+2+3 via run_retrieval (BM25 only, Dense only, Hybrid RRF)
# ────────────────────────────────────────────────
from preprocessing.retrieve import run_retrieval

print(SEP)
print("STAGE 1: BM25 only (mode=bm25, top_k=10)")
print(SEP)
bm25_out = run_retrieval(QUERY, child_age=AGE, mode="bm25", top_k=10,
                          candidate_k=100, config_path=CONFIG, skip_hash_check=True)
bm25_res = bm25_out["results"]
for r in bm25_res[:5]:
    print("  [%d] %-28s  score=%.4f  sparse_rank=%s" % (
        r["rank"], r["chunk_id"], r["score"], r.get("sparse_rank")))
bm25_iodine = next((r["rank"] for r in bm25_res if r["chunk_id"] == IODINE), None)
bm25_nk015  = next((r["rank"] for r in bm25_res if r["chunk_id"].startswith("NK-015")), None)
print()
print("  Iodine %s BM25 rank: %s" % (IODINE, bm25_iodine))
print("  NK-015-* BM25 first rank: %s" % bm25_nk015)

print()
print(SEP)
print("STAGE 2: Dense only (mode=dense, top_k=10)")
print(SEP)
dense_out = run_retrieval(QUERY, child_age=AGE, mode="dense", top_k=10,
                           candidate_k=100, config_path=CONFIG, skip_hash_check=True)
dense_res = dense_out["results"]
for r in dense_res[:5]:
    print("  [%d] %-28s  score=%.4f  dense_rank=%s" % (
        r["rank"], r["chunk_id"], r["score"], r.get("dense_rank")))
dense_iodine = next((r["rank"] for r in dense_res if r["chunk_id"] == IODINE), None)
dense_nk015  = next((r["rank"] for r in dense_res if r["chunk_id"].startswith("NK-015")), None)
print()
print("  Iodine %s Dense rank: %s" % (IODINE, dense_iodine))
print("  NK-015-* Dense first rank: %s" % dense_nk015)

print()
print(SEP)
print("STAGE 3: Hybrid RRF (mode=hybrid, top_k=50 — candidate pool)")
print(SEP)
rrf_out = run_retrieval(QUERY, child_age=AGE, mode="hybrid", top_k=50,
                         candidate_k=100, config_path=CONFIG, skip_hash_check=True)
rrf_res = rrf_out["results"]
print("  Top 10 RRF candidates:")
for r in rrf_res[:10]:
    print("  [%2d] %-28s  rrf=%.6f  bm25_rank=%s  dense_rank=%s" % (
        r["rank"], r["chunk_id"], r.get("rrf_score", r["score"]),
        r.get("sparse_rank"), r.get("dense_rank")))
rrf_iodine = next((r["rank"] for r in rrf_res if r["chunk_id"] == IODINE), None)
rrf_nk015  = next((r["rank"] for r in rrf_res if r["chunk_id"].startswith("NK-015")), None)
print()
print("  Iodine %s RRF rank: %s" % (IODINE, rrf_iodine))
print("  NK-015-* RRF first rank: %s" % rrf_nk015)

# ────────────────────────────────────────────────
# STAGE 4: Cross-Encoder Reranker
# ────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 4: Cross-Encoder Reranker (bge-reranker-base, top_k=5)")
print(SEP)
from preprocessing.rerank import run_reranking
re_out = run_reranking(QUERY, child_age=AGE,
                        reranker_model_name="BAAI/bge-reranker-base",
                        candidate_k=50, top_k=5, config_path=CONFIG)
re_res = re_out["results"]
for r in re_res[:5]:
    rnk = r.get("final_rank", r.get("rank"))
    print("  [%d] %-28s  reranker_score=%.4f  orig_rank=%s" % (
        rnk, r["chunk_id"], r.get("reranker_score", r["score"]),
        r.get("original_rank")))
re_iodine = next((r.get("final_rank", r.get("rank")) for r in re_res if r["chunk_id"] == IODINE), None)
re_nk015  = next((r.get("final_rank", r.get("rank")) for r in re_res if r["chunk_id"].startswith("NK-015")), None)
# Also show NK-015 chunk text snippet if found
nk015_chunk = next((r for r in re_res if r["chunk_id"].startswith("NK-015")), None)
print()
print("  Iodine %s Reranker rank: %s" % (IODINE, re_iodine or "NOT in Top 5"))
print("  NK-015-* Reranker first rank: %s" % (re_nk015 or "NOT in Top 5"))
if nk015_chunk:
    print("  NK-015 text snippet: \"%s...\"" % nk015_chunk.get("text","")[:100].replace("\n"," "))
    print("  NK-015 page_numbers: %s" % nk015_chunk.get("page_numbers"))

# ────────────────────────────────────────────────
# STAGE 5: Context Refiner
# ────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 5: Context Refiner (Jaccard dedup)")
print(SEP)
from preprocessing.context_refiner import refine_context
refined_out = refine_context(re_out)
evidence = refined_out.get("evidence", [])
print("  Context refiner: %d → %d chunks" % (len(re_res), len(evidence)))
for i, e in enumerate(evidence, 1):
    txt = e.get("text","")[:80].replace("\n"," ")
    print("  [%d] %-28s  pages=%s  \"%s...\"" % (
        i, e["chunk_id"], e.get("page_numbers"), txt))
fin_iodine = next((i+1 for i,e in enumerate(evidence) if e["chunk_id"] == IODINE), None)
fin_nk015  = next((i+1 for i,e in enumerate(evidence) if e["chunk_id"].startswith("NK-015")), None)
nk015_ev   = next((e for e in evidence if e["chunk_id"].startswith("NK-015")), None)
print()
print("  Iodine %s in final evidence: %s" % (IODINE, fin_iodine or "NOT PRESENT"))
print("  NK-015-* in final evidence: rank=%s" % (fin_nk015 or "NOT PRESENT"))
if nk015_ev:
    print("  NK-015 page_numbers: %s" % nk015_ev.get("page_numbers"))
    print("  NK-015 text snippet: \"%s...\"" % nk015_ev.get("text","")[:120].replace("\n"," "))

# ────────────────────────────────────────────────
# SUMMARY TABLE
# ────────────────────────────────────────────────
print()
print(SEP)
print("RETRIEVAL PIPELINE SUMMARY")
print(SEP)
print("  %-20s | %-20s | %-20s" % ("Stage", "Iodine NK-021-C00582", "NK-015-* rank"))
print("  " + "-"*65)
print("  %-20s | %-20s | %-20s" % ("BM25",      str(bm25_iodine or "absent"),  str(bm25_nk015 or "absent")))
print("  %-20s | %-20s | %-20s" % ("Dense",     str(dense_iodine or "absent"), str(dense_nk015 or "absent")))
print("  %-20s | %-20s | %-20s" % ("RRF hybrid",str(rrf_iodine or "absent"),   str(rrf_nk015 or "absent")))
print("  %-20s | %-20s | %-20s" % ("Reranker",  str(re_iodine or "absent"),    str(re_nk015 or "absent")))
print("  %-20s | %-20s | %-20s" % ("Final ctx", str(fin_iodine or "absent"),   str(fin_nk015 or "absent")))
print()
nk015_page5 = False
if nk015_ev:
    pages = nk015_ev.get("page_numbers", [])
    nk015_page5 = (5 in pages) or (any(p >= 4 for p in pages))  # page 5 or near
    print("  NK-015 pages in final evidence: %s (contains page 5: %s)" % (pages, 5 in pages if pages else "N/A"))
print()
print("  NK-015 protein retrieval PASS: %s" % ("PASS" if fin_nk015 else "FAIL"))
print("  Iodine NOT dominant at Rank 1 : %s" % ("PASS" if re_iodine != 1 else "FAIL -- iodine still Rank 1 after reranker"))
