import os
import sys
import json
import csv
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import capture_frozen_assets_hashes, verify_hashes
from preprocessing.rerank import run_reranking, evaluate_rerankers
from preprocessing.context_refiner import refine_context

def run_phase3_5_reranking_audit():
    config = json.load(open(os.path.join(BASE_DIR, "preprocessing", "config.json"), "r", encoding="utf-8"))
    rerank_csv = os.path.join(BASE_DIR, "data", "processed", "reranking_evaluation.csv")
    rerank_summary = os.path.join(BASE_DIR, "data", "processed", "reranking_summary.md")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 3.5 RERANKING AUDIT")
    print("============================================================")

    # 1. Deliverables existence
    print(f"[+] Reranking evaluation CSV exists: {os.path.exists(rerank_csv)}")
    print(f"[+] Reranking evaluation Summary MD exists: {os.path.exists(rerank_summary)}")

    # 2. Per-query rows check (30 queries x 5 modes = 150 rows)
    with open(rerank_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[+] Total per-query evaluation rows: {len(rows)} (Target: 150 rows = 30 queries x 5 model configurations)")

    # 3. Calculate baseline vs reranker metrics
    hybrid_rows = [r for r in rows if r["mode_key"] == "hybrid"]
    bge_rerank_rows = [r for r in rows if r["mode_key"] == "reranker_bge"]

    hybrid_mrr = sum(float(r["mrr"]) for r in hybrid_rows) / 30.0
    hybrid_ndcg5 = sum(float(r["ndcg@5"]) for r in hybrid_rows) / 30.0
    hybrid_recall5 = sum(float(r["recall@5"]) for r in hybrid_rows) / 30.0

    bge_mrr = sum(float(r["mrr"]) for r in bge_rerank_rows) / 30.0
    bge_ndcg5 = sum(float(r["ndcg@5"]) for r in bge_rerank_rows) / 30.0
    bge_recall5 = sum(float(r["recall@5"]) for r in bge_rerank_rows) / 30.0

    mrr_gain = ((bge_mrr - hybrid_mrr) / hybrid_mrr) * 100.0
    ndcg_gain = ((bge_ndcg5 - hybrid_ndcg5) / hybrid_ndcg5) * 100.0

    print(f"[+] Hybrid Baseline MRR: {hybrid_mrr:.4f} | BGE Reranker MRR: {bge_mrr:.4f} (Gain: +{mrr_gain:.1f}%)")
    print(f"[+] Hybrid Baseline nDCG@5: {hybrid_ndcg5:.4f} | BGE Reranker nDCG@5: {bge_ndcg5:.4f} (Gain: +{ndcg_gain:.1f}%)")
    print(f"[+] Hybrid Baseline Recall@5: {hybrid_recall5:.4f} | BGE Reranker Recall@5: {bge_recall5:.4f}")

    # 4. Context Refiner Verification
    sample_res = run_reranking("What is the calcium requirement for a 10 year old?", child_age=10.0, candidate_k=50, top_k=5)
    refined = refine_context(sample_res)

    print(f"[+] Context Refiner Input Chunks: {refined['refinement_stats']['raw_input_chunks']}")
    print(f"[+] Context Refiner Final Evidence Chunks: {refined['refinement_stats']['final_evidence_chunks']}")
    print(f"[+] Provenance Preservation: source_id='{refined['evidence'][0]['source_id']}', file_name='{refined['evidence'][0]['file_name']}', pages={refined['evidence'][0]['page_numbers']}")

    # 5. Check Checksum Gate
    initial_hashes = capture_frozen_assets_hashes(config)
    checksum_passed, msg = verify_hashes(initial_hashes)
    print(f"[+] Frozen Assets Checksum Gate: {'PASSED' if checksum_passed else 'FAILED'}")

    return {
        "report_rows": len(rows),
        "hybrid_mrr": hybrid_mrr,
        "bge_mrr": bge_mrr,
        "mrr_gain_pct": mrr_gain,
        "bge_ndcg5": bge_ndcg5,
        "ndcg_gain_pct": ndcg_gain,
        "checksum_passed": checksum_passed
    }

if __name__ == "__main__":
    run_phase3_5_reranking_audit()
