import urllib.request
import json
import time

req = urllib.request.Request(
    'http://localhost:8000/api/ask/stream',
    data=json.dumps({
        'question': 'Recommended protein intake for 10-year-old child (ICMR-NIN RDA)',
        'age': 10.0
    }).encode(),
    headers={'Content-Type': 'application/json'}
)

print("Sending request to /api/ask/stream ...")
t0 = time.perf_counter()
first_token_time = None
tokens = []
final_done = None

with urllib.request.urlopen(req) as resp:
    while True:
        line = resp.readline()
        if not line:
            break
        line_str = line.decode('utf-8').strip()
        if not line_str.startswith('data: '):
            continue
        try:
            payload = json.loads(line_str[6:])
        except Exception:
            continue
        evt = payload.get('event')
        if evt == 'stage':
            print(f"[{time.perf_counter()-t0:.2f}s] STAGE {payload.get('stage')}: {payload.get('name')}", flush=True)
        elif evt == 'token':
            if first_token_time is None:
                first_token_time = time.perf_counter() - t0
                print(f"\n*** FIRST TOKEN RECEIVED AT: {first_token_time:.2f}s (TTFT) ***", flush=True)
                print("Streaming tokens: ", end="", flush=True)
            tok = payload.get('token', '')
            tokens.append(tok)
            print(tok, end="", flush=True)
        elif evt == 'done':
            final_done = payload.get('result')
            print(f"\n[{time.perf_counter()-t0:.2f}s] DONE!", flush=True)

total_time = time.perf_counter() - t0
print(f"Total streaming time: {total_time:.2f}s")
print(f"Tokens received: {len(tokens)}")
if final_done:
    print("\n--- FINAL ANSWER ---")
    print(final_done.get('answer'))
    print("\n--- CITATIONS ---")
    for c in final_done.get('citations', []):
        print(f"[{c.get('chunk_id')}] {c.get('source')} - {c.get('title')}")
    print("\n--- PERF METRICS ---")
    print(json.dumps(final_done.get('perf_metrics'), indent=2))
