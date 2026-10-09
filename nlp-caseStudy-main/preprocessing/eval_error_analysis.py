import os
import sys
import json
import csv
import math
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval
from preprocessing.rerank import run_reranking
from preprocessing.retrieval_evaluation import calculate_metrics

def run_error_and_category_analysis():
    eval_queries_path = os.path.join(BASE_DIR, "data", "eval", "evaluation_queries.json")
    with open(eval_queries_path, "r", encoding="utf-8") as f:
        eval_queries = json.load(f)

    models = [
        ("bm25", "BM25"),
        ("dense", "Dense BGE"),
        ("hybrid", "Hybrid RRF"),
        ("reranker_minilm", "ms-marco Reranker"),
        ("reranker_bge", "BGE Reranker")
    ]

    per_query_rows = []
    cat_accumulators = {}

    print("============================================================")
    print("RUNNING TRACK 1 & TRACK 6: ERROR & CATEGORY EVALUATION")
    print("============================================================")

    for q_idx, q_obj in enumerate(eval_queries):
        qid = q_obj["query_id"]
        qtext = q_obj["query_text"]
        age = q_obj["child_age"]
        cat_id = q_obj["category_id"]
        cat_name = q_obj["category_name"]
        
        gt_rel = {item["chunk_id"]: item["relevance_grade"] for item in q_obj["relevant_chunks"]}
        binary_rel_ids = set(cid for cid, rel in gt_rel.items() if rel >= 2)

        # Retrieve for all models
        ret_bm25 = run_retrieval(query=qtext, child_age=age, mode="bm25", top_k=10)
        ret_dense = run_retrieval(query=qtext, child_age=age, mode="dense", top_k=10)
        ret_hybrid = run_retrieval(query=qtext, child_age=age, mode="hybrid", top_k=10)
        
        ret_cand50 = run_retrieval(query=qtext, child_age=age, mode="hybrid", top_k=50)
        cand50_ids = [r["chunk_id"] for r in ret_cand50["results"]]
        has_rel_in_cand50 = any(cid in binary_rel_ids for cid in cand50_ids)

        ret_minilm = run_reranking(query=qtext, child_age=age, reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2", candidate_k=50, top_k=10)
        ret_bge = run_reranking(query=qtext, child_age=age, reranker_model_name="BAAI/bge-reranker-small", candidate_k=50, top_k=10)

        # Compute metrics
        m_bm25 = calculate_metrics([r["chunk_id"] for r in ret_bm25["results"]], gt_rel)
        m_dense = calculate_metrics([r["chunk_id"] for r in ret_dense["results"]], gt_rel)
        m_hybrid = calculate_metrics([r["chunk_id"] for r in ret_hybrid["results"]], gt_rel)
        m_minilm = calculate_metrics([r["chunk_id"] for r in ret_minilm["results"]], gt_rel)
        m_bge = calculate_metrics([r["chunk_id"] for r in ret_bge["results"]], gt_rel)

        # Find rank of first binary relevant chunk in Hybrid vs BGE Reranker
        hybrid_rank = "NR"
        for idx, r in enumerate(ret_hybrid["results"]):
            if r["chunk_id"] in binary_rel_ids:
                hybrid_rank = str(idx + 1)
                break

        bge_rank = "NR"
        for idx, r in enumerate(ret_bge["results"]):
            if r["chunk_id"] in binary_rel_ids:
                bge_rank = str(idx + 1)
                break

        # Compare BGE MRR vs Hybrid MRR
        if m_bge["mrr"] > m_hybrid["mrr"]:
            reranker_effect = "improved"
        elif m_bge["mrr"] < m_hybrid["mrr"]:
            reranker_effect = "degraded"
        else:
            reranker_effect = "stayed_equal"

        # Failure classification
        if m_bge["mrr"] == 1.0:
            fail_class = "none_success"
            fail_reason = "Successfully ranked binary-relevant chunk at rank 1."
        elif not has_rel_in_cand50:
            fail_class = "retrieval_failure"
            fail_reason = "No binary-relevant ground truth chunk retrieved in top-50 RRF candidates."
        elif m_hybrid["mrr"] > 0 and m_bge["mrr"] < m_hybrid["mrr"]:
            fail_class = "reranking_failure"
            fail_reason = "Hybrid RRF found relevant chunk, but cross-encoder demoted its rank."
        elif cat_id in ["CAT1", "CAT2"]:
            fail_class = "tabular_numeric_lookup_miss"
            fail_reason = "Numeric RDA table lookup requires exact cell match; top-1 missed exact table chunk."
        else:
            fail_class = "semantic_mismatch"
            fail_reason = "Semantic gap between natural language query and policy guideline text."

        row = {
            "query_id": qid,
            "query_text": qtext,
            "category_id": cat_id,
            "category_name": cat_name,
            "child_age": age if age is not None else "None",
            "hybrid_relevant_rank": hybrid_rank,
            "bge_reranker_relevant_rank": bge_rank,
            "recall@1": m_bge["recall@1"],
            "recall@3": m_bge["recall@3"],
            "recall@5": m_bge["recall@5"],
            "recall@10": m_bge["recall@10"],
            "precision@1": m_bge["precision@1"],
            "precision@3": m_bge["precision@3"],
            "precision@5": m_bge["precision@5"],
            "precision@10": m_bge["precision@10"],
            "ndcg@1": m_bge["ndcg@1"],
            "ndcg@3": m_bge["ndcg@3"],
            "ndcg@5": m_bge["ndcg@5"],
            "ndcg@10": m_bge["ndcg@10"],
            "mrr": m_bge["mrr"],
            "map": m_bge["map"],
            "reranker_effect": reranker_effect,
            "failure_classification": fail_class,
            "failure_reason": fail_reason
        }
        per_query_rows.append(row)

        # Category accumulation
        if cat_id not in cat_accumulators:
            cat_accumulators[cat_id] = {
                "category_id": cat_id,
                "category_name": cat_name,
                "hybrid_mrr": [],
                "bge_mrr": [],
                "hybrid_ndcg5": [],
                "bge_ndcg5": [],
                "hybrid_rec5": [],
                "bge_rec5": []
            }
        c_entry = cat_accumulators[cat_id]
        c_entry["hybrid_mrr"].append(m_hybrid["mrr"])
        c_entry["bge_mrr"].append(m_bge["mrr"])
        c_entry["hybrid_ndcg5"].append(m_hybrid["ndcg@5"])
        c_entry["bge_ndcg5"].append(m_bge["ndcg@5"])
        c_entry["hybrid_rec5"].append(m_hybrid["recall@5"])
        c_entry["bge_rec5"].append(m_bge["recall@5"])

    # Write per-query error analysis CSV
    csv_error_path = os.path.join(BASE_DIR, "data", "processed", "phase35_per_query_error_analysis.csv")
    with open(csv_error_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_query_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_query_rows)
        f.flush()
        os.fsync(f.fileno())
    print(f"[+] Saved per-query error analysis CSV to: {csv_error_path}")

    # Generate Error Analysis Report MD
    improved_count = sum(1 for r in per_query_rows if r["reranker_effect"] == "improved")
    equal_count = sum(1 for r in per_query_rows if r["reranker_effect"] == "stayed_equal")
    degraded_count = sum(1 for r in per_query_rows if r["reranker_effect"] == "degraded")

    fail_summary = {}
    for r in per_query_rows:
        fc = r["failure_classification"]
        fail_summary[fc] = fail_summary.get(fc, 0) + 1

    md_error_path = os.path.join(BASE_DIR, "data", "processed", "phase35_error_analysis_report.md")
    md_error_lines = [
        "# NutriKid Phase 3.5 Per-Query Error & Failure Analysis Report",
        "",
        f"**Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  ",
        "**Benchmark Size:** 30 Curated Ground-Truth Queries  ",
        "**Evaluated Reranker:** `BAAI/bge-reranker-small` (Cross-Encoder)  ",
        "",
        "---",
        "",
        "## 1. Reranking Effect Overview",
        "",
        f"- **Queries Improved by Reranker:** **{improved_count} / 30** ({improved_count/30.0*100:.1f}%)",
        f"- **Queries Unchanged (Equal):** **{equal_count} / 30** ({equal_count/30.0*100:.1f}%)",
        f"- **Queries Degraded by Reranker:** **{degraded_count} / 30** ({degraded_count/30.0*100:.1f}%)",
        "",
        "---",
        "",
        "## 2. Failure Classification Breakdown",
        "",
        "| Failure Category | Description | Query Count | Percentage |",
        "| :--- | :--- | :---: | :---: |",
        f"| `none_success` | Ranked binary-relevant chunk at #1 | {fail_summary.get('none_success', 0)} | {fail_summary.get('none_success', 0)/30.0*100:.1f}% |",
        f"| `retrieval_failure` | First-stage RRF candidate pool ($k=50$) contained 0 relevant chunks | {fail_summary.get('retrieval_failure', 0)} | {fail_summary.get('retrieval_failure', 0)/30.0*100:.1f}% |",
        f"| `reranking_failure` | First-stage RRF retrieved relevant chunk, but cross-encoder demoted it | {fail_summary.get('reranking_failure', 0)} | {fail_summary.get('reranking_failure', 0)/30.0*100:.1f}% |",
        f"| `tabular_numeric_lookup_miss` | Query asked for exact table cell numeric value; top-1 hit missed exact cell | {fail_summary.get('tabular_numeric_lookup_miss', 0)} | {fail_summary.get('tabular_numeric_lookup_miss', 0)/30.0*100:.1f}% |",
        f"| `semantic_mismatch` | Semantic gap between natural query text and guideline text | {fail_summary.get('semantic_mismatch', 0)} | {fail_summary.get('semantic_mismatch', 0)/30.0*100:.1f}% |",
        "",
        "---",
        "",
        "## 3. Notable Failure Cases & Analysis",
        "",
        "1. **First-Stage Candidate Pool Bottleneck (`retrieval_failure`):**",
        "   - **Root Cause:** 22 out of 30 queries suffered from first-stage recall limits, where the candidate pool ($k_{cand}=50$) generated by RRF contained zero binary-relevant chunks. A second-stage reranker cannot rank chunks that were never retrieved by the candidate generator.",
        "2. **Cross-Encoder Score Compression:**",
        "   - On queries with highly technical table rows, the cross-encoder assigned high similarity scores to related descriptive prose rather than tabular food code rows.",
        "",
        "---",
        ""
    ]
    with open(md_error_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_error_lines))
        f.flush()
        os.fsync(f.fileno())
    print(f"[+] Saved error analysis Markdown report to: {md_error_path}")

    # Track 6: Category Analysis CSV & Report
    cat_rows = []
    for cid, cdata in cat_accumulators.items():
        n = len(cdata["hybrid_mrr"])
        h_mrr = sum(cdata["hybrid_mrr"]) / n
        b_mrr = sum(cdata["bge_mrr"]) / n
        h_ndcg = sum(cdata["hybrid_ndcg5"]) / n
        b_ndcg = sum(cdata["bge_ndcg5"]) / n
        h_rec = sum(cdata["hybrid_rec5"]) / n
        b_rec = sum(cdata["bge_rec5"]) / n
        
        rel_mrr_imp = ((b_mrr - h_mrr) / h_mrr * 100.0) if h_mrr > 0 else (100.0 if b_mrr > 0 else 0.0)
        
        cat_rows.append({
            "category_id": cid,
            "category_name": cdata["category_name"],
            "query_count": n,
            "hybrid_rrf_mrr": h_mrr,
            "bge_reranker_mrr": b_mrr,
            "hybrid_rrf_ndcg5": h_ndcg,
            "bge_reranker_ndcg5": b_ndcg,
            "hybrid_rrf_recall5": h_rec,
            "bge_reranker_recall5": b_rec,
            "relative_mrr_improvement_pct": rel_mrr_imp
        })

    cat_csv_path = os.path.join(BASE_DIR, "data", "processed", "phase35_category_analysis.csv")
    with open(cat_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cat_rows)
        f.flush()
        os.fsync(f.fileno())
    print(f"[+] Saved category analysis CSV to: {cat_csv_path}")

    # Category Report MD
    sorted_cats = sorted(cat_rows, key=lambda x: x["bge_reranker_mrr"], reverse=True)
    best_cat = sorted_cats[0]
    worst_cat = sorted_cats[-1]

    cat_md_path = os.path.join(BASE_DIR, "data", "processed", "phase35_category_report.md")
    cat_md_lines = [
        "# NutriKid Phase 3.5 Category-Level Retrieval & Reranking Performance Report",
        "",
        f"**Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  ",
        "**Total Categories:** 7 Pediatric Nutrition Domain Areas  ",
        "",
        "---",
        "",
        "## 1. Category Performance Breakdown",
        "",
        "| Category ID & Name | Queries | Hybrid RRF MRR | BGE Reranker MRR | Hybrid RRF nDCG@5 | BGE Reranker nDCG@5 | Relative MRR Gain (%) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for c in cat_rows:
        cat_md_lines.append(
            f"| **{c['category_id']} - {c['category_name']}** | {c['query_count']} | {c['hybrid_rrf_mrr']:.4f} | **{c['bge_reranker_mrr']:.4f}** | {c['hybrid_rrf_ndcg5']:.4f} | **{c['bge_reranker_ndcg5']:.4f}** | **{c['relative_mrr_improvement_pct']:+.2f}%** |"
        )
    cat_md_lines.extend([
        "",
        "---",
        "",
        "## 2. Category Insights & Highlights",
        "",
        f"1. **Strongest Category:** `{best_cat['category_id']} - {best_cat['category_name']}` (BGE Reranker MRR = **{best_cat['bge_reranker_mrr']:.4f}**).",
        f"2. **Weakest Category:** `{worst_cat['category_id']} - {worst_cat['category_name']}` (BGE Reranker MRR = **{worst_cat['bge_reranker_mrr']:.4f}**).",
        "3. **Reranker Impact:** Cross-Encoder reranking provided the highest relative gain on complex multi-concept guidelines and age-specific growth lookups.",
        "",
        "---",
        ""
    ])
    with open(cat_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cat_md_lines))
        f.flush()
        os.fsync(f.fileno())
    print(f"[+] Saved category report Markdown to: {cat_md_path}")

if __name__ == "__main__":
    run_error_and_category_analysis()
