"""
generation/chroma_faiss_comparison.py — FAISS vs ChromaDB Comparison

Runs the EXISTING corrected 30-query retrieval benchmark against both
FAISS and ChromaDB similarity search (top-k only, no reranking).

Does NOT modify the benchmark, corpus, or Phase 1 retrieval pipeline.
"""

import os, sys, json, math
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

BENCHMARK_PATH = os.path.join(BASE_DIR, "data", "eval", "evaluation_queries.json")


def dcg(relevances):
    return sum(r / math.log2(i + 2) for i, r in enumerate(relevances))

def calculate_metrics(retrieved_ids, gt_rel, k_vals=(5, 10)):
    gt_set = set(gt_rel.keys())
    metrics = {}
    for k in k_vals:
        top = retrieved_ids[:k]
        hits = [1 if cid in gt_set else 0 for cid in top]
        metrics[f"recall@{k}"] = min(sum(hits) / max(len(gt_set), 1), 1.0)
    # MRR
    mrr = 0.0
    for rank, cid in enumerate(retrieved_ids[:10], 1):
        if cid in gt_set:
            mrr = 1.0 / rank
            break
    metrics["mrr"] = mrr
    # nDCG@5
    top5 = retrieved_ids[:5]
    rel5 = [gt_rel.get(cid, 0) for cid in top5]
    ideal = sorted(gt_rel.values(), reverse=True)[:5]
    ideal_padded = ideal + [0] * (5 - len(ideal))
    idcg = dcg(ideal_padded)
    metrics["ndcg@5"] = dcg(rel5) / idcg if idcg > 0 else 0.0
    return metrics


def run_comparison(k=10):
    from generation.chroma_retriever import similarity_search_chroma, similarity_search_faiss

    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        queries = json.load(f)

    faiss_all, chroma_all = [], []
    per_query = []

    for q in queries:
        qid     = q["query_id"]
        qtext   = q["query_text"]
        gt_rel  = {item["chunk_id"]: item["relevance_grade"] for item in q["relevant_chunks"]}

        faiss_res  = similarity_search_faiss(qtext, k=k)
        chroma_res = similarity_search_chroma(qtext, k=k)

        faiss_ids  = [r["chunk_id"] for r in faiss_res]
        chroma_ids = [r["chunk_id"] for r in chroma_res]

        fm = calculate_metrics(faiss_ids,  gt_rel)
        cm = calculate_metrics(chroma_ids, gt_rel)
        faiss_all.append(fm)
        chroma_all.append(cm)

        top5_f = set(faiss_ids[:5])
        top5_c = set(chroma_ids[:5])
        top5_overlap = len(top5_f & top5_c) / 5.0

        per_query.append({
            "query_id": qid, "query_text": qtext,
            "faiss_top10": faiss_ids,  "chroma_top10": chroma_ids,
            "faiss_metrics": fm,       "chroma_metrics": cm,
            "top5_overlap": round(top5_overlap, 4),
            "top1_agree": faiss_ids[0] == chroma_ids[0] if faiss_ids and chroma_ids else False,
        })
        print(f"  {qid}: FAISS MRR={fm['mrr']:.4f}  Chroma MRR={cm['mrr']:.4f}  Top5-overlap={top5_overlap:.2f}")

    def avg(lst, k_): return round(sum(m[k_] for m in lst) / len(lst), 4)
    n = len(faiss_all)

    top5_overlaps = [pq["top5_overlap"] for pq in per_query]
    top10_overlaps= [len(set(pq["faiss_top10"]) & set(pq["chroma_top10"])) / k for pq in per_query]
    agree_top1    = sum(1 for pq in per_query if pq["top1_agree"]) / n

    # Find agree/differ examples
    sorted_by_overlap = sorted(per_query, key=lambda x: x["top5_overlap"])
    example_differ = sorted_by_overlap[0]
    example_agree  = sorted_by_overlap[-1]

    summary = {
        "n_queries": n,
        "faiss": {"recall@5": avg(faiss_all,"recall@5"), "recall@10": avg(faiss_all,"recall@10"),
                  "mrr": avg(faiss_all,"mrr"), "ndcg@5": avg(faiss_all,"ndcg@5")},
        "chroma": {"recall@5": avg(chroma_all,"recall@5"), "recall@10": avg(chroma_all,"recall@10"),
                   "mrr": avg(chroma_all,"mrr"), "ndcg@5": avg(chroma_all,"ndcg@5")},
        "avg_top5_overlap": round(sum(top5_overlaps)/n, 4),
        "avg_top10_overlap": round(sum(top10_overlaps)/n, 4),
        "pct_agree_top1": round(agree_top1 * 100, 1),
        "example_agree":  {"query_id": example_agree["query_id"],  "query_text": example_agree["query_text"],
                           "top5_overlap": example_agree["top5_overlap"]},
        "example_differ": {"query_id": example_differ["query_id"], "query_text": example_differ["query_text"],
                           "top5_overlap": example_differ["top5_overlap"]},
        "per_query": per_query,
    }

    out_path = os.path.join(BASE_DIR, "data", "processed", "chroma_faiss_comparison.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n[Comparison] Saved to {out_path}")
    print(f"FAISS   -> R@5={summary['faiss']['recall@5']}  MRR={summary['faiss']['mrr']}  nDCG@5={summary['faiss']['ndcg@5']}")
    print(f"ChromaDB-> R@5={summary['chroma']['recall@5']}  MRR={summary['chroma']['mrr']}  nDCG@5={summary['chroma']['ndcg@5']}")
    print(f"Top-5 overlap (avg): {summary['avg_top5_overlap']*100:.1f}%  Top-1 agree: {summary['pct_agree_top1']}%")
    return summary

if __name__ == "__main__":
    run_comparison()
