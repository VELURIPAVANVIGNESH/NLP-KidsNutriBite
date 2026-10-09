"""
generation/rouge_evaluation.py — NutriKid Phase 2 ROUGE Evaluation

Implements ROUGE-1, ROUGE-2, ROUGE-L for generation quality evaluation.

ROUGE compares GENERATED ANSWER vs REFERENCE ANSWER.
It does NOT compare against retrieved chunks.

Reference answers are loaded from data/eval/generation_benchmark.json.
"""

import os, sys, json
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from rouge_score import rouge_scorer

ROUGE_SCORER = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
BENCHMARK_PATH = os.path.join(BASE_DIR, "data", "eval", "generation_benchmark.json")


def compute_rouge(generated: str, reference: str) -> dict:
    """
    Compute ROUGE-1, ROUGE-2, ROUGE-L between generated and reference answers.

    Returns:
        dict with rouge1, rouge2, rougeL  (each: precision, recall, fmeasure)
    """
    scores = ROUGE_SCORER.score(reference, generated)
    return {
        "rouge1": {
            "precision": round(scores["rouge1"].precision, 4),
            "recall":    round(scores["rouge1"].recall,    4),
            "fmeasure":  round(scores["rouge1"].fmeasure,  4),
        },
        "rouge2": {
            "precision": round(scores["rouge2"].precision, 4),
            "recall":    round(scores["rouge2"].recall,    4),
            "fmeasure":  round(scores["rouge2"].fmeasure,  4),
        },
        "rougeL": {
            "precision": round(scores["rougeL"].precision, 4),
            "recall":    round(scores["rougeL"].recall,    4),
            "fmeasure":  round(scores["rougeL"].fmeasure,  4),
        },
    }


def evaluate_grounding(generated: str, evidence_items: list) -> dict:
    """
    HEURISTIC: Check whether generated answer text overlaps with supplied evidence.
    Not a scientifically validated grounding metric — labelled as heuristic.
    """
    if not evidence_items or not generated:
        return {"grounded": False, "overlap_score": 0.0, "method": "heuristic_token_overlap"}
    ev_tokens = set()
    for e in evidence_items:
        ev_tokens.update(e.get("text","").lower().split())
    gen_tokens = set(generated.lower().split())
    overlap = len(gen_tokens & ev_tokens) / max(len(gen_tokens), 1)
    return {"grounded": overlap > 0.25, "overlap_score": round(overlap, 4), "method": "heuristic_token_overlap"}


def evaluate_citations(generated: str, supplied_chunk_ids: list) -> dict:
    """
    HEURISTIC: Check whether cited chunk IDs in the answer belong to supplied evidence.
    """
    import re
    cited = re.findall(r"NK-\d{3}-C\d{5}", generated)
    if not cited:
        return {"all_citations_valid": True, "cited_ids": [], "invalid_citations": [],
                "method": "heuristic_regex"}
    invalid = [c for c in cited if c not in supplied_chunk_ids]
    return {"all_citations_valid": len(invalid) == 0, "cited_ids": cited,
            "invalid_citations": invalid, "method": "heuristic_regex"}


def evaluate_numerical_preservation(generated: str, evidence_items: list) -> dict:
    """
    HEURISTIC: Check that numbers appearing in evidence also appear in generated answer.
    """
    import re
    num_pattern = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg/day|g/day|µg/day|kcal/day|mg|g|µg|kcal|%|ml)\b", re.IGNORECASE)
    ev_numbers = set()
    for e in evidence_items:
        ev_numbers.update(num_pattern.findall(e.get("text","")))
    if not ev_numbers:
        return {"preserved": True, "ev_numbers": [], "found_in_answer": [], "method": "heuristic_regex"}
    found = [n for n in ev_numbers if n.lower() in generated.lower()]
    preserved = len(found) / max(len(ev_numbers), 1) >= 0.4
    return {"preserved": preserved, "ev_numbers": list(ev_numbers),
            "found_in_answer": found, "preservation_rate": round(len(found)/max(len(ev_numbers),1), 4),
            "method": "heuristic_regex"}


def run_rouge_evaluation(use_qwen=True, max_queries=None):
    """
    Run ROUGE evaluation over the generation benchmark.

    Args:
        use_qwen    : If True use Qwen pipeline; else use deterministic synthesizer.
        max_queries : Limit number of queries (None = all).

    Returns:
        dict with per-query results and aggregate ROUGE scores.
    """
    if not os.path.exists(BENCHMARK_PATH):
        raise FileNotFoundError(f"Generation benchmark not found: {BENCHMARK_PATH}")
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        benchmark = json.load(f)
    if max_queries:
        benchmark = benchmark[:max_queries]

    if use_qwen:
        from generation.qwen_generator import run_qwen_pipeline as run_pipeline
    else:
        from generation.generate import run_generation_pipeline as run_pipeline

    results = []
    agg_r1 = agg_r2 = agg_rl = 0.0
    n = 0

    for item in benchmark:
        qid      = item["query_id"]
        question = item["question"]
        age      = item.get("age", 10.0)
        reference= item["reference_answer"]
        ev_ids   = item.get("relevant_chunk_ids", [])

        print(f"[ROUGE] Evaluating {qid}: {question[:60]}...")
        try:
            if use_qwen:
                gen_res = run_pipeline(query=question, child_age=age)
            else:
                gen_res = run_pipeline(query=question, child_age=age)
            generated = gen_res.get("answer", "")
            evidence  = gen_res.get("evidence", [])
            evidence_items = [{"text": e.get("text",""), "chunk_id": e.get("chunk_id","")} for e in evidence]
            retrieved_ids  = [e.get("chunk_id","") for e in evidence]
        except Exception as ex:
            generated = ""
            evidence_items = []
            retrieved_ids  = []
            print(f"  [ROUGE] Error for {qid}: {ex}")

        rouge  = compute_rouge(generated, reference)
        ground = evaluate_grounding(generated, evidence_items)
        cit    = evaluate_citations(generated, retrieved_ids)
        nums   = evaluate_numerical_preservation(generated, evidence_items)

        r = {
            "query_id":       qid,
            "question":       question,
            "age":            age,
            "generated_answer": generated,
            "reference_answer": reference,
            "rouge": rouge,
            "grounding":      ground,
            "citations":      cit,
            "numerics":       nums,
        }
        results.append(r)
        agg_r1 += rouge["rouge1"]["fmeasure"]
        agg_r2 += rouge["rouge2"]["fmeasure"]
        agg_rl += rouge["rougeL"]["fmeasure"]
        n += 1

    avg_r1 = round(agg_r1 / n, 4) if n else 0.0
    avg_r2 = round(agg_r2 / n, 4) if n else 0.0
    avg_rl = round(agg_rl / n, 4) if n else 0.0

    summary = {
        "n_queries":    n,
        "avg_rouge1":   avg_r1,
        "avg_rouge2":   avg_r2,
        "avg_rougeL":   avg_rl,
        "per_query":    results,
    }

    out_path = os.path.join(BASE_DIR, "data", "processed", "rouge_evaluation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[ROUGE] Results saved to {out_path}")
    print(f"[ROUGE] Avg ROUGE-1={avg_r1}  ROUGE-2={avg_r2}  ROUGE-L={avg_rl} ({n} queries)")
    return summary


if __name__ == "__main__":
    run_rouge_evaluation(use_qwen=True, max_queries=5)
