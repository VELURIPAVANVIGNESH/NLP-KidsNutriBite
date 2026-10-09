import urllib.request
import json
import time

print("="*60)
print("NUTRIKID SYSTEM VERIFICATION SUITE")
print("="*60)

# 1. Health check
try:
    with urllib.request.urlopen("http://localhost:8000/api/health") as resp:
        health_data = json.loads(resp.read().decode())
        print(f"[1] Backend Health Check: {health_data.get('status')} - {health_data.get('message')}")
except Exception as e:
    print(f"[1] Backend Health Check FAILED: {e}")

# 2. Next.js UI Frontend Check
try:
    with urllib.request.urlopen("http://localhost:3000/ask") as resp:
        print(f"[2] Frontend UI Check: Status {resp.status} OK (http://localhost:3000/ask reachable)")
except Exception as e:
    print(f"[2] Frontend UI Check FAILED: {e}")

# 3. Stream API Check
print("\n[3] Testing Streaming Pipeline (/api/ask/stream)...")
req = urllib.request.Request(
    'http://localhost:8000/api/ask/stream',
    data=json.dumps({
        'question': 'Recommended protein intake for 10-year-old child (ICMR-NIN RDA)',
        'age': 10.0
    }).encode(),
    headers={'Content-Type': 'application/json'}
)

t0 = time.perf_counter()
first_token_t = None
stage_times = {}
tokens = []
final_res = None

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
            stage_idx = payload.get('stage')
            stage_name = payload.get('name')
            elapsed = time.perf_counter() - t0
            stage_times[stage_idx] = (stage_name, elapsed)
            print(f"   [Stage {stage_idx}] {stage_name:<12} at {elapsed:.2f}s")
        elif evt == 'token':
            if first_token_t is None:
                first_token_t = time.perf_counter() - t0
                print(f"   >>> FIRST TOKEN (TTFT) at {first_token_t:.2f}s <<<")
            tokens.append(payload.get('token'))
        elif evt == 'done':
            final_res = payload.get('result')
            total_elapsed = time.perf_counter() - t0
            print(f"   >>> DONE event at {total_elapsed:.2f}s <<<")

total_t = time.perf_counter() - t0
print(f"\nTotal Pipeline Execution: {total_t:.2f}s")
print(f"Tokens streamed: {len(tokens)}")
if final_res:
    print("\n--- FINAL ANSWER ---")
    print(final_res.get('answer'))
    print("\n--- PROVENANCE CITATIONS ---")
    for c in final_res.get('citations', []):
        print(f"[{c.get('chunk_id')}] {c.get('source')} - {c.get('title')}")
    print("\n--- DETAILED PERFORMANCE METRICS ---")
    print(json.dumps(final_res.get('perf_metrics'), indent=2))
print("="*60)
