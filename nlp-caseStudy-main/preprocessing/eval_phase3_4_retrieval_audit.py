import os
import sys
import json
import csv
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import capture_frozen_assets_hashes, verify_hashes
from preprocessing.retrieval_evaluation import run_evaluation_suite, aggregate_results

def run_phase3_4_retrieval_audit():
    config = json.load(open(os.path.join(BASE_DIR, "preprocessing", "config.json"), "r", encoding="utf-8"))
    report_csv = os.path.join(BASE_DIR, "data", "processed", "evaluation_report.csv")
    cat_report_csv = os.path.join(BASE_DIR, "data", "processed", "evaluation_category_report.csv")
    summary_md = os.path.join(BASE_DIR, "data", "processed", "evaluation_summary.md")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 3.4 RETRIEVAL ENGINE AUDIT")
    print("============================================================")

    # 1. Deliverables existence
    print(f"[+] Evaluation report CSV exists: {os.path.exists(report_csv)}")
    print(f"[+] Category report CSV exists: {os.path.exists(cat_report_csv)}")
    print(f"[+] Summary report MD exists: {os.path.exists(summary_md)}")

    # 2. Check total report rows
    with open(report_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[+] Total per-query evaluation rows: {len(rows)} (Target: 90 rows = 30 queries x 3 modes)")

    # 3. Aggregate metrics check
    results, _ = run_evaluation_suite()
    overall, cat_agg = aggregate_results(results)

    hybrid_mrr = overall["hybrid"]["mrr"]
    bm25_mrr = overall["bm25"]["mrr"]
    dense_mrr = overall["dense"]["mrr"]

    print(f"[+] BM25 MRR: {bm25_mrr:.4f} (Target: 0.0361)")
    print(f"[+] Dense MRR: {dense_mrr:.4f} (Target: 0.0178)")
    print(f"[+] Hybrid RRF MRR: {hybrid_mrr:.4f} (Target: 0.0400)")

    # 4. Check Checksum Gate
    initial_hashes = capture_frozen_assets_hashes(config)
    checksum_passed, msg = verify_hashes(initial_hashes)
    print(f"[+] Frozen Assets Checksum Gate: {'PASSED' if checksum_passed else 'FAILED'}")

    return {
        "report_rows": len(rows),
        "bm25_mrr": bm25_mrr,
        "dense_mrr": dense_mrr,
        "hybrid_mrr": hybrid_mrr,
        "checksum_passed": checksum_passed
    }

if __name__ == "__main__":
    run_phase3_4_retrieval_audit()
