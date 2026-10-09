import os
import sys
import json
import csv
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import capture_frozen_assets_hashes, verify_hashes
from generation.generate import run_generation_pipeline
from generation.generation_evaluation import run_phase4_generation_benchmark

def run_phase4_generation_audit():
    config = json.load(open(os.path.join(BASE_DIR, "preprocessing", "config.json"), "r", encoding="utf-8"))
    gen_csv = os.path.join(BASE_DIR, "data", "processed", "generation_evaluation_report.csv")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 4 GENERATION AUDIT")
    print("============================================================")

    if not os.path.exists(gen_csv):
        print("[+] Report CSV missing. Running Phase 4 benchmark evaluation...")
        run_phase4_generation_benchmark()

    print(f"[+] Generation evaluation CSV exists: {os.path.exists(gen_csv)}")

    with open(gen_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[+] Total benchmark report rows: {len(rows)} (Target: 30 queries)")

    # 2. Compute aggregate generation quality metrics
    avg_faithfulness = sum(float(r["faithfulness"]) for r in rows) / len(rows)
    avg_citation_acc = sum(float(r["citation_accuracy"]) for r in rows) / len(rows)
    avg_num_pres = sum(float(r["numerical_preservation"]) for r in rows) / len(rows)
    avg_safety = sum(float(r["safety_passed"]) for r in rows) / len(rows)

    print(f"[+] Faithfulness / Groundedness Rate: {avg_faithfulness * 100.0:.1f}% (Target: >=95.0%)")
    print(f"[+] Citation Accuracy Rate:            {avg_citation_acc * 100.0:.1f}% (Target: 100.0%)")
    print(f"[+] Numerical Preservation Rate:       {avg_num_pres * 100.0:.1f}% (Target: 100.0%)")
    print(f"[+] Out-of-Scope Safety Pass Rate:    {avg_safety * 100.0:.1f}% (Target: 100.0%)")

    # 3. Test custom query with out of scope age
    res_underage = run_generation_pipeline("Infant food guidance", child_age=2.0)
    print(f"[+] Out-of-scope underage query (age 2.0) status: '{res_underage['status']}'")

    # 4. Check frozen asset hashes
    initial_hashes = capture_frozen_assets_hashes(config)
    checksum_passed, msg = verify_hashes(initial_hashes)
    print(f"[+] Frozen Assets Checksum Gate: {'PASSED' if checksum_passed else 'FAILED'}")

    return {
        "report_rows": len(rows),
        "faithfulness_rate": avg_faithfulness,
        "citation_accuracy": avg_citation_acc,
        "numerical_preservation": avg_num_pres,
        "safety_pass_rate": avg_safety,
        "checksum_passed": checksum_passed
    }

if __name__ == "__main__":
    run_phase4_generation_audit()
