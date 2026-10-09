import os
import sys
import json
import csv
import hashlib
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.parse_documents import parse_documents

def calculate_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def run_phase2_audit():
    manifest_path = os.path.join(BASE_DIR, "data", "metadata", "corpus_manifest.csv")
    parsed_dir = os.path.join(BASE_DIR, "data", "processed", "parsed")
    report_path = os.path.join(BASE_DIR, "data", "processed", "parser_report.csv")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 2 METRIC & CONTRACT AUDIT")
    print("============================================================")

    # 1. Read manifest active documents
    with open(manifest_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        active_sids = [r["source_id"] for r in reader if r["retrieval_enabled"].lower() == "true"]

    total_active = len(active_sids)
    print(f"[+] Total active documents in manifest: {total_active}")

    # 2. Read parser report CSV
    with open(report_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        report_rows = list(reader)

    total_parsed_docs = len(report_rows)
    total_pages = sum(int(r["pages_processed"]) for r in report_rows)
    pages_with_text = sum(int(r["pages_with_text"]) for r in report_rows)
    empty_pages = sum(int(r["empty_pages"]) for r in report_rows)
    low_text_pages = sum(int(r["low_text_pages"]) for r in report_rows)
    total_chars = sum(int(r["character_count"]) for r in report_rows)
    total_words = sum(int(r["word_count"]) for r in report_rows)
    total_errors = sum(int(r["extraction_errors"]) for r in report_rows)

    page_coverage_pct = ((pages_with_text + low_text_pages) / float(total_pages) * 100.0) if total_pages > 0 else 0.0

    # 3. Unicode Corruption Inspection across all JSON files
    corrupted_pages_count = 0
    for fname in os.listdir(parsed_dir):
        if not fname.endswith("_parsed.json"):
            continue
        fpath = os.path.join(parsed_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get("pages", []):
            txt = p.get("text", "")
            if "\ufffd" in txt or "\uFFFD" in txt:
                corrupted_pages_count += 1

    corrupted_rate_pct = (corrupted_pages_count / float(total_pages) * 100.0) if total_pages > 0 else 0.0

    print(f"[+] Total active documents parsed: {total_parsed_docs} / {total_active}")
    print(f"[+] Total pages processed across 22 docs: {total_pages}")
    print(f"[+] Pages with text (>=10 chars): {pages_with_text}")
    print(f"[+] Empty pages (0 chars): {empty_pages}")
    print(f"[+] Low-text pages (<10 chars): {low_text_pages}")
    print(f"[+] Page coverage rate: {page_coverage_pct:.2f}%")
    print(f"[+] Total characters extracted: {total_chars:,}")
    print(f"[+] Total words extracted: {total_words:,}")
    print(f"[+] Extraction errors: {total_errors}")
    print(f"[+] Unicode corrupted pages rate: {corrupted_rate_pct:.4f}% ({corrupted_pages_count} pages)")

    # 4. Check Reproducibility across parsed JSON files
    initial_hashes = {f: calculate_file_hash(os.path.join(parsed_dir, f)) for f in os.listdir(parsed_dir) if f.endswith("_parsed.json")}
    parse_documents()
    post_hashes = {f: calculate_file_hash(os.path.join(parsed_dir, f)) for f in os.listdir(parsed_dir) if f.endswith("_parsed.json")}

    reproducible = (initial_hashes == post_hashes)
    print(f"[+] Reproducibility Test (Re-parsed JSON Hashes Match): {'PASSED' if reproducible else 'FAILED'}")

    return {
        "total_active": total_active,
        "total_parsed": total_parsed_docs,
        "total_pages": total_pages,
        "pages_with_text": pages_with_text,
        "empty_pages": empty_pages,
        "low_text_pages": low_text_pages,
        "page_coverage_pct": page_coverage_pct,
        "total_chars": total_chars,
        "total_words": total_words,
        "total_errors": total_errors,
        "corrupted_pages_count": corrupted_pages_count,
        "reproducible": reproducible
    }

if __name__ == "__main__":
    run_phase2_audit()
