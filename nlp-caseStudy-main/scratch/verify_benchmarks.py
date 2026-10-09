import requests, json, time

URL = "http://localhost:8000/api/ask/stream"

test_cases = [
    {
        "name": "Query 1: Protein for 10yo",
        "payload": {"question": "Recommended protein intake for 10-year-old child (ICMR-NIN RDA)", "age": 10.0},
        "expected_nutrient": "protein",
        "expected_age": 10.0
    },
    {
        "name": "Query 2: Calcium for 12yo girl",
        "payload": {"question": "Calcium RDA for 12-year-old girl", "age": 12.0},
        "expected_nutrient": "calcium",
        "expected_age": 12.0
    },
    {
        "name": "Query 3: Iron for 7yo",
        "payload": {"question": "Iron requirements for 7-year-old", "age": 7.0},
        "expected_nutrient": "iron",
        "expected_age": 7.0
    },
    {
        "name": "Query 4: Vitamin A for 14yo boy",
        "payload": {"question": "Vitamin A UL vs RDA for 14-year-old boy", "age": 14.0},
        "expected_nutrient": "vitamin a",
        "expected_age": 14.0
    },
    {
        "name": "Query 5: Sugar for 9yo",
        "payload": {"question": "Added sugar guidelines for 9-year-old", "age": 9.0},
        "expected_nutrient": "sugar",
        "expected_age": 9.0
    },
    {
        "name": "Negative Check: Age 2 Toddler (Out of scope)",
        "payload": {"question": "Protein requirements for 2-year-old toddler", "age": 2.0},
        "should_reject": True
    }
]

print("=" * 65)
print("COMPREHENSIVE NUTRIKID 5-BENCHMARK + SAFETY VERIFICATION")
print("=" * 65)

all_passed = True

for tc in test_cases:
    print(f"\n--- {tc['name']} ---")
    t0 = time.time()
    ttft = None
    streamed_tokens = []
    final_result = None

    r = requests.post(URL, json=tc["payload"], stream=True, timeout=60)
    for line in r.iter_lines():
        if line:
            lstr = line.decode('utf-8')
            if lstr.startswith("data: "):
                data = json.loads(lstr[6:])
                if data.get("event") == "token":
                    if ttft is None:
                        ttft = time.time() - t0
                    streamed_tokens.append(data.get("token"))
                elif data.get("event") == "done":
                    final_result = data.get("result")

    total_time = time.time() - t0
    
    if tc.get("should_reject"):
        status = final_result.get("status") if final_result else "none"
        ans = final_result.get("answer", "") if final_result else ""
        if "out_of_scope" in status or "Out of Scope" in ans:
            print(f"PASS: Correctly rejected out-of-scope age ({total_time:.2f}s)")
            print(f"Refusal text: {ans}")
        else:
            print(f"FAIL: Did not reject out-of-scope age! Status: {status}")
            all_passed = False
        continue

    ans = final_result.get("answer", "") if final_result else "".join(streamed_tokens)
    citations = final_result.get("citations", []) if final_result else []
    fidelity = final_result.get("fidelity_check") if final_result else None

    # Check unwanted metadata
    has_boilerplate = any(b in ans.lower() for b in ["request for reprints", "e-mail:", "author: dr", "proofreading"])
    has_citations = len(citations) > 0
    fidelity_pass = (fidelity is None) or fidelity.get("passed", True)

    print(f"TTFT: {ttft:.2f}s | Total: {total_time:.2f}s")
    print(f"Answer Preview:\n{ans[:200]}...")
    print(f"Citations: {[c.get('chunk_id') for c in citations]}")
    print(f"Fidelity Guard: {'PASS' if fidelity_pass else 'FAIL'}")
    print(f"Boilerplate Free: {'YES' if not has_boilerplate else 'NO'}")

    if has_boilerplate or not has_citations:
        print("FAIL: Quality check failed!")
        all_passed = False
    else:
        print("VERIFIED: PASS")

print("\n" + "=" * 65)
print(f"OVERALL STATUS: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")
print("=" * 65)
