#!/usr/bin/env python3
"""
scratch/run_gen_validation.py
NutriKid Final Validation - GEN001 diagnosis + 5-query post-fix ROUGE benchmark.

Writes results to:
  data/processed/postfix_rouge_results.json
  data/processed/gen001_diagnosis.json
"""
import os, sys, json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, BASE_DIR)

BENCH_PATH = os.path.join(BASE_DIR, "data", "eval", "generation_benchmark.json")
OUT_ROUGE  = os.path.join(BASE_DIR, "data", "processed", "postfix_rouge_results.json")
OUT_DIAG   = os.path.join(BASE_DIR, "data", "processed", "gen001_diagnosis.json")

# ---- ROUGE scorer ----
from rouge_score import rouge_scorer as _rs
ROUGE = _rs.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

def rouge(gen, ref):
    s = ROUGE.score(ref, gen)
    return {
        "rouge1": round(s["rouge1"].fmeasure, 4),
        "rouge2": round(s["rouge2"].fmeasure, 4),
        "rougeL": round(s["rougeL"].fmeasure, 4),
    }

# ---- Grounding heuristic ----
def grounding(gen, evidence):
    if not evidence or not gen:
        return {"grounded": False, "overlap_score": 0.0, "method": "heuristic_token_overlap"}
    ev_tokens = set()
    for e in evidence:
        ev_tokens.update(e.get("text", "").lower().split())
    gen_tokens = set(gen.lower().split())
    score = len(gen_tokens & ev_tokens) / max(len(gen_tokens), 1)
    return {"grounded": score > 0.25, "overlap_score": round(score, 4), "method": "heuristic_token_overlap"}

# ---- Citation validation heuristic ----
import re as _re
def citations_valid(gen, retrieved_ids):
    cited = _re.findall(r"NK-\d{3}-C\d{5}", gen)
    if not cited:
        return {"all_citations_valid": True, "cited_ids": [], "invalid_citations": [], "method": "heuristic_regex"}
    invalid = [c for c in cited if c not in retrieved_ids]
    return {"all_citations_valid": len(invalid) == 0, "cited_ids": cited,
            "invalid_citations": invalid, "method": "heuristic_regex"}

# ---- Fidelity guard ----
from generation.nutrient_fidelity_guard import validate_nutrient_fidelity

def main():
    print("=" * 60)
    print("NutriKid Post-Fix ROUGE Benchmark (5 queries)")
    print("=" * 60)

    with open(BENCH_PATH, encoding="utf-8") as f:
        benchmark = json.load(f)
    benchmark = benchmark[:5]  # GEN001-GEN005

    from generation.qwen_generator import run_qwen_pipeline

    results = []
    agg = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    n = 0

    for item in benchmark:
        qid      = item["query_id"]
        question = item["question"]
        age      = item.get("age", 10.0)
        reference= item["reference_answer"]
        ev_ids   = item.get("relevant_chunk_ids", [])

        print(f"\n[{qid}] {question[:70]}...")
        try:
            gen_res  = run_qwen_pipeline(query=question, child_age=age,
                                         candidate_k=50, top_k=5)
            generated = gen_res.get("answer", "")
            evidence  = gen_res.get("evidence", [])
            ret_ids   = [e.get("chunk_id","") for e in evidence]
            fidelity  = gen_res.get("fidelity_check") or validate_nutrient_fidelity(question, generated)
        except Exception as ex:
            print(f"  ERROR: {ex}")
            generated = ""
            evidence  = []
            ret_ids   = []
            fidelity  = {"passed": False, "failure_reason": str(ex), "method": "error"}

        r = rouge(generated, reference)
        g = grounding(generated, evidence)
        c = citations_valid(generated, ret_ids)
        fid = fidelity if isinstance(fidelity, dict) else validate_nutrient_fidelity(question, generated)

        # Pass/fail logic:
        # PASS = fidelity guard passed AND answer is non-empty
        passed = fid.get("passed", True) and len(generated) > 10

        print(f"  ROUGE-1={r['rouge1']}  ROUGE-2={r['rouge2']}  ROUGE-L={r['rougeL']}")
        print(f"  Fidelity: {'PASS' if fid.get('passed',True) else 'FAIL - ' + fid.get('failure_reason','')[:80]}")
        print(f"  Grounded: {g['grounded']} (overlap={g['overlap_score']})")
        print(f"  Answer[:150]: {generated[:150]}")

        row = {
            "query_id":          qid,
            "question":          question,
            "age":               age,
            "retrieved_top5_ids": ret_ids,
            "generated_answer":  generated,
            "reference_answer":  reference,
            "rouge1_fmeasure":   r["rouge1"],
            "rouge2_fmeasure":   r["rouge2"],
            "rougeL_fmeasure":   r["rougeL"],
            "citation_validity": c,
            "heuristic_grounding": g,
            "nutrient_fidelity": fid,
            "pass_fail":         "PASS" if passed else "FAIL",
        }
        results.append(row)
        agg["rouge1"] += r["rouge1"]
        agg["rouge2"] += r["rouge2"]
        agg["rougeL"] += r["rougeL"]
        n += 1

    avg_r1 = round(agg["rouge1"] / n, 4) if n else 0.0
    avg_r2 = round(agg["rouge2"] / n, 4) if n else 0.0
    avg_rl = round(agg["rougeL"] / n, 4) if n else 0.0

    summary = {
        "run_label": "post_fix",
        "n_queries": n,
        "avg_rouge1": avg_r1,
        "avg_rouge2": avg_r2,
        "avg_rougeL": avg_rl,
        "per_query": results,
    }

    with open(OUT_ROUGE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Post-fix ROUGE: ROUGE-1={avg_r1}  ROUGE-2={avg_r2}  ROUGE-L={avg_rl}")
    print(f"Results saved: {OUT_ROUGE}")
    print("=" * 60)

    # GEN001 diagnosis
    gen001 = next((r for r in results if r["query_id"] == "GEN001"), None)
    if gen001:
        diag = {
            "query_id": "GEN001",
            "question": gen001["question"],
            "age": gen001["age"],
            "pre_fix_generated_answer": (
                "For a 10-year-old child, the recommended dietary allowance for protein is "
                "between 90 and 120 micrograms (µg) per day. This recommendation aligns with "
                "the FAO/WHO expert consultation's findings that iodine requirements..."
            ),
            "pre_fix_failure": "WRONG NUTRIENT SUBSTITUTION: iodine µg/day reported as protein RDA",
            "post_fix_generated_answer": gen001["generated_answer"],
            "post_fix_fidelity": gen001["nutrient_fidelity"],
            "post_fix_pass_fail": gen001["pass_fail"],
            "fix_applied": "Deterministic NutrientFidelityGuard in generation/nutrient_fidelity_guard.py",
        }
        with open(OUT_DIAG, "w", encoding="utf-8") as f:
            json.dump(diag, f, indent=2, ensure_ascii=False)
        print(f"GEN001 diagnosis saved: {OUT_DIAG}")

    return summary

if __name__ == "__main__":
    main()
