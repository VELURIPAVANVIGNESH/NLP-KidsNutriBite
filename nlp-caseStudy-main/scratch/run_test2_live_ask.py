import urllib.request, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:8000/api/ask"
payload = {
    "question": "What is the protein requirement for a 10-year-old child?",
    "age": 10.0
}
headers = {"Content-Type": "application/json"}
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

print(f"Calling LIVE /api/ask with question: '{payload['question']}', age: {payload['age']}")
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as response:
        elapsed = time.time() - t0
        data = json.loads(response.read().decode("utf-8"))
        print(f"HTTP {response.getcode()} received in {elapsed:.1f}s\n")
        
        answer = data.get("answer", "")
        citations = data.get("citations", [])
        evidence = data.get("evidence", [])
        fidelity = data.get("fidelity_check", {})
        
        print("=== GENERATED ANSWER ===")
        print(answer)
        print()
        
        print("=== CITATIONS ===")
        for c in citations:
            print(f"- {c.get('chunk_id')}: {c.get('source')} (Pages: {c.get('page_numbers')}) - {c.get('title')}")
        print()
        
        print("=== FIDELITY CHECK ===")
        print(json.dumps(fidelity, indent=2))
        print()
        
        with open("scratch/live_api_ask_verified.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("Saved result to scratch/live_api_ask_verified.json")
except Exception as e:
    print(f"Error after {time.time()-t0:.1f}s: {e}")
