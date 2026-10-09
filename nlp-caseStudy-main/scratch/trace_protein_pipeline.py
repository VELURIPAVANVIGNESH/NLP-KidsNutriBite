"""
Final targeted verification: traces the full retrieval pipeline for the protein query
and then calls /api/ask to verify end-to-end behaviour.
"""

import sys, json, time, requests
sys.path.insert(0, ".")

QUERY = "What is the protein requirement for a 10-year-old child?"
AGE   = 10

SEP = "=" * 70

# ─────────────────────────────────────────────────────────
# STAGE 1 – BM25
# ─────────────────────────────────────────────────────────
print(SEP)
print("STAGE 1: BM25 Retrieval")
print(SEP)

from preprocessing.retrieve import bm25_retrieve
bm25_results = bm25_retrieve(QUERY, top_k=10)
print(f"BM25 returned {len(bm25_results)} results")
for i, r in enumerate(bm25_results[:5], 1):
    print(f"  [{i}] {r.get('chunk_id','?'):25s}  score={r.get('score', r.get('bm25_score', '?')):.4f}")

# ─────────────────────────────────────────────────────────
# STAGE 2 – Dense / BGE
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 2: Dense (BGE-M3 / FAISS) Retrieval")
print(SEP)

from preprocessing.retrieve import dense_retrieve
dense_results = dense_retrieve(QUERY, top_k=10)
print(f"Dense returned {len(dense_results)} results")
for i, r in enumerate(dense_results[:5], 1):
    score_val = r.get('score', r.get('similarity_score', r.get('dense_score', '?')))
    print(f"  [{i}] {r.get('chunk_id','?'):25s}  score={score_val}")

# ─────────────────────────────────────────────────────────
# STAGE 3 – RRF Fusion
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 3: RRF Fusion")
print(SEP)

from preprocessing.retrieve import rrf_fusion
rrf_results = rrf_fusion(bm25_results, dense_results, top_k=10)
print(f"RRF returned {len(rrf_results)} results")
for i, r in enumerate(rrf_results[:5], 1):
    score_val = r.get('rrf_score', r.get('score', '?'))
    print(f"  [{i}] {r.get('chunk_id','?'):25s}  rrf_score={score_val}")

# Check if iodine chunk is in Top 5
iodine_chunk = "NK-021-C00582"
iodine_rank_rrf = next((i+1 for i, r in enumerate(rrf_results) if r.get('chunk_id') == iodine_chunk), None)
nk015_rank_rrf  = next((i+1 for i, r in enumerate(rrf_results) if r.get('chunk_id','').startswith('NK-015')), None)
print(f"\n  Iodine chunk {iodine_chunk} rank after RRF: {iodine_rank_rrf or 'not in Top 10'}")
print(f"  NK-015 first appearance rank after RRF:  {nk015_rank_rrf or 'not in Top 10'}")

# ─────────────────────────────────────────────────────────
# STAGE 4 – Cross-Encoder Reranker
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 4: Cross-Encoder Reranker (bge-reranker-base)")
print(SEP)

try:
    from preprocessing.rerank import rerank_candidates
    reranked = rerank_candidates(QUERY, rrf_results, top_k=5)
    print(f"Reranker returned {len(reranked)} results")
    for i, r in enumerate(reranked[:5], 1):
        score_val = r.get('rerank_score', r.get('cross_encoder_score', r.get('score', '?')))
        print(f"  [{i}] {r.get('chunk_id','?'):25s}  rerank_score={score_val}")

    iodine_rank_re = next((i+1 for i, r in enumerate(reranked) if r.get('chunk_id') == iodine_chunk), None)
    nk015_rank_re  = next((i+1 for i, r in enumerate(reranked) if r.get('chunk_id','').startswith('NK-015')), None)
    print(f"\n  Iodine chunk {iodine_chunk} rank after Reranker: {iodine_rank_re or 'not in Top 5'}")
    print(f"  NK-015 first appearance rank after Reranker:  {nk015_rank_re or 'not in Top 5'}")
except Exception as e:
    print(f"  ERROR running reranker: {e}")
    reranked = rrf_results[:5]

# ─────────────────────────────────────────────────────────
# STAGE 5 – Context Refiner
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 5: Context Refiner (Jaccard dedup)")
print(SEP)

try:
    from generation.context_refiner import refine_context
    refined = refine_context(reranked)
    print(f"Context refiner returned {len(refined)} chunks (from {len(reranked)} input)")
    for i, r in enumerate(refined[:5], 1):
        cid = r.get('chunk_id', '?')
        txt_preview = r.get('text', '')[:80].replace('\n', ' ')
        print(f"  [{i}] {cid:25s}  \"{txt_preview}...\"")

    iodine_final = next((i+1 for i, r in enumerate(refined) if r.get('chunk_id') == iodine_chunk), None)
    nk015_final  = next((i+1 for i, r in enumerate(refined) if r.get('chunk_id','').startswith('NK-015')), None)
    print(f"\n  Iodine chunk {iodine_chunk} in final evidence: {iodine_final or 'NOT PRESENT'}")
    print(f"  NK-015 chunk in final evidence: {nk015_final or 'NOT PRESENT'}")
except Exception as e:
    print(f"  Context refiner error: {e}")
    refined = reranked[:5]

# ─────────────────────────────────────────────────────────
# STAGE 6 – /api/ask live call
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("STAGE 6: Live /api/ask call")
print(SEP)
print(f"  Query: {QUERY}")
print(f"  Age:   {AGE}")
print("  (Note: LLM generation on CPU takes ~3-4 minutes)")
print("  Sending request...")

try:
    t0 = time.time()
    resp = requests.post(
        "http://127.0.0.1:8000/api/ask",
        json={"query": QUERY, "child_age": AGE},
        timeout=300
    )
    elapsed = time.time() - t0
    print(f"  Response received in {elapsed:.1f}s  HTTP {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        answer    = data.get("answer", "")
        citations = data.get("citations", [])
        fidelity  = data.get("fidelity_check", {})

        print()
        print("--- ANSWER ---")
        print(answer[:600])
        if len(answer) > 600:
            print(f"  ... [{len(answer)-600} more chars]")

        print()
        print("--- CITATIONS ---")
        for c in citations:
            cid   = c.get("chunk_id", c.get("source", "?"))
            pages = c.get("page_numbers", [])
            print(f"  {cid}  pages={pages}")

        print()
        print("--- FIDELITY GUARD ---")
        print(f"  passed           : {fidelity.get('passed')}")
        print(f"  nutrient_detected: {fidelity.get('nutrient_detected')}")
        print(f"  unit_contaminated: {fidelity.get('unit_contaminated')}")
        print(f"  failure_reason   : {fidelity.get('failure_reason','')[:120]}")

        # Check correctness heuristics
        ans_lower = answer.lower()
        has_g_day    = "g/day" in ans_lower or "grams" in ans_lower
        has_ug       = "µg" in answer or " ug" in ans_lower or "micrograms" in ans_lower
        has_protein  = "protein" in ans_lower
        has_iodine   = "iodine" in ans_lower or "thyroid" in ans_lower
        cit_ids      = [c.get("chunk_id", c.get("source","")) for c in citations]
        cites_nk015  = any("NK-015" in c for c in cit_ids)
        cites_nk021  = any("NK-021" in c for c in cit_ids)

        print()
        print("--- CONTENT ANALYSIS ---")
        print(f"  Answer mentions protein  : {has_protein}")
        print(f"  Answer uses g/day/grams  : {has_g_day}")
        print(f"  Answer uses µg/ug units  : {has_ug}  ← should be False")
        print(f"  Answer mentions iodine   : {has_iodine}  ← should be False")
        print(f"  Citations include NK-015 : {cites_nk015}  ← should be True")
        print(f"  Citations include NK-021 : {cites_nk021}  ← ideally False (iodine doc)")
    else:
        print(f"  ERROR: HTTP {resp.status_code} — {resp.text[:300]}")
        data = {}
        fidelity = {}
        cit_ids = []
        has_g_day = has_ug = has_iodine = cites_nk015 = cites_nk021 = None
        has_protein = None

except requests.exceptions.Timeout:
    print("  TIMEOUT after 300s — LLM still generating. Skipping /api/ask analysis.")
    data = {}
    fidelity = {}
    cit_ids = []
    has_g_day = has_ug = has_iodine = cites_nk015 = cites_nk021 = None
    has_protein = None
    elapsed = 300

except Exception as ex:
    print(f"  Exception: {ex}")
    data = {}
    fidelity = {}
    cit_ids = []
    has_g_day = has_ug = has_iodine = cites_nk015 = cites_nk021 = None
    has_protein = None
    elapsed = 0

# ─────────────────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────────────────
print()
print(SEP)
print("FINAL VERIFICATION REPORT")
print(SEP)

def yn(v, want=True):
    if v is None: return "UNKNOWN"
    return "PASS" if (bool(v) == want) else "FAIL"

# Fidelity guard
fg_pass = fidelity.get("passed", None)
if fg_pass is None:
    fg_label = "UNKNOWN (no API response)"
elif fg_pass:
    fg_label = "PASS"
else:
    fg_label = "FAIL (guard triggered)"

# Protein retrieval: NK-015 should appear in final refined evidence
nk015_retrieved = nk015_final is not None if 'nk015_final' in dir() else None

# Iodine dominance
iodine_dom = (iodine_rank_re == 1) if iodine_rank_re else False

print(f"  Fidelity Guard           : {fg_label}")
print(f"  Protein Retrieval        : {'PASS' if nk015_retrieved else 'FAIL'} "
      f"(NK-015 rank in refined evidence: {nk015_final or 'absent'})")
print(f"  Iodine Chunk NK-021-C00582 dominance : {'FAIL — still Rank #1' if iodine_dom else 'PASS — not Rank #1'} "
      f"(reranker rank: {iodine_rank_re or 'absent'})")
print(f"  Protein Citation NK-015  : {yn(cites_nk015, True)}")
print(f"  Correct unit (g/day)     : {yn(has_g_day, True)}")
print(f"  Iodine unit contamination: {yn(has_ug, False)}")
print(f"  Answer on protein topic  : {yn(has_protein, True)}")
