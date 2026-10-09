import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))
from generation.qwen_generator import generate_answer

chunks = json.load(open('data/processed/preprocessed_corpus.json', encoding='utf-8'))
c = [x for x in chunks if x['chunk_id'] == 'NK-015-C00013'][0]

query = "What is the protein requirement for a 10-year-old child?"
child_age = 10.0

print(f"Running TEST 1 — Direct generator with query: '{query}', age: {child_age}")
print("Evidence: NK-015-C00013 only.\n")

res = generate_answer(query=query, child_age=child_age, evidence_items=[c])

print("=== RESULT ANSWER ===")
print(res.get("answer"))
print("\n=== CITATIONS ===")
print(json.dumps(res.get("citations"), indent=2))
print("\n=== FIDELITY CHECK ===")
print(json.dumps(res.get("fidelity_check"), indent=2))

answer = res.get("answer", "")
has_boys = "31.8" in answer and "Boys" in answer
has_girls = "32.8" in answer and "Girls" in answer
has_10_2 = "10.2" in answer
has_ug = "µg" in answer or "ug" in answer or "microgram" in answer.lower()
fidelity_pass = res.get("fidelity_check", {}).get("passed", False)
citations_has_nk015 = any(cit.get("chunk_id") == "NK-015-C00013" for cit in res.get("citations", []))

print("\n=== TEST 1 SUMMARY CHECKS ===")
print(f"Boys 10-12 (31.8 g/day) present: {'PASS' if has_boys else 'FAIL'}")
print(f"Girls 10-12 (32.8 g/day) present: {'PASS' if has_girls else 'FAIL'}")
print(f"Fidelity Guard passed: {'PASS' if fidelity_pass else 'FAIL'}")
print(f"Citation NK-015-C00013: {'PASS' if citations_has_nk015 else 'FAIL'}")
print(f"No 10.2 g/day: {'PASS' if not has_10_2 else 'FAIL'}")
print(f"No ug/micrograms: {'PASS' if not has_ug else 'FAIL'}")
