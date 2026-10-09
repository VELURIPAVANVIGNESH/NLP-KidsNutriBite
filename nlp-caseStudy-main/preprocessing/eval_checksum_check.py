import os
import sys
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import capture_frozen_assets_hashes, verify_hashes

config_path = os.path.join(BASE_DIR, "preprocessing", "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

hashes = capture_frozen_assets_hashes(config)
ok, msg = verify_hashes(hashes)
print(f"[PRE-EVAL CHECKSUM GATE] Status: {'PASSED' if ok else 'FAILED'}, Files checked: {len(hashes)}")
