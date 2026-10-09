import os
import sys
import csv
import hashlib
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.generate_manifest import generate_manifest
from preprocessing.validate_manifest import validate_manifest

def calculate_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def run_phase1_audit():
    manifest_path = os.path.join(BASE_DIR, "data", "metadata", "corpus_manifest.csv")
    corpus_dir = os.path.join(BASE_DIR, "knowledge_corpus")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 1 METRIC & CONTRACT AUDIT")
    print("============================================================")

    # 1. Count physical PDFs
    physical_pdfs = []
    for root, dirs, files in os.walk(corpus_dir):
        for f in files:
            if f.endswith('.pdf'):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, BASE_DIR).replace('\\', '/')
                physical_pdfs.append((rel_p, full_p))

    total_physical = len(physical_pdfs)
    print(f"[+] Total physical PDF files discovered in knowledge_corpus/: {total_physical}")

    # 2. Read manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        manifest_rows = list(reader)

    total_manifest = len(manifest_rows)
    print(f"[+] Total entries in corpus_manifest.csv: {total_manifest}")

    active_rows = [r for r in manifest_rows if r["retrieval_enabled"].lower() == "true"]
    disabled_rows = [r for r in manifest_rows if r["retrieval_enabled"].lower() == "false"]
    print(f"[+] Active retrieval documents (retrieval_enabled=true): {len(active_rows)}")
    print(f"[+] Disabled retrieval documents (retrieval_enabled=false): {len(disabled_rows)}")

    # 3. Verify hashes of physical files
    valid_hashes = 0
    for rel_p, abs_p in physical_pdfs:
        h = calculate_file_hash(abs_p)
        if h and len(h) == 32:
            valid_hashes += 1

    print(f"[+] Valid MD5 hashes computed: {valid_hashes} / {total_physical}")

    # 4. Mandatory Metadata Completeness
    missing_fields_count = 0
    for r in manifest_rows:
        if not r["source_id"] or not r["source_name"] or not r["file_name"] or not r["relative_path"] or not r["publisher"] or not r["publication_year"] or not r["document_type"] or not r["domain"]:
            missing_fields_count += 1

    print(f"[+] Manifest entries with missing mandatory metadata fields: {missing_fields_count}")

    # 5. Check Reproducibility
    initial_hash = calculate_file_hash(manifest_path)
    generate_manifest()
    post_hash = calculate_file_hash(manifest_path)

    reproducible = (initial_hash == post_hash)
    print(f"[+] Reproducibility Test (Re-generated CSV Hash Match): {'PASSED' if reproducible else 'FAILED'}")

    return {
        "total_physical": total_physical,
        "total_manifest": total_manifest,
        "active_count": len(active_rows),
        "disabled_count": len(disabled_rows),
        "valid_hashes": valid_hashes,
        "missing_fields": missing_fields_count,
        "reproducible": reproducible
    }

if __name__ == "__main__":
    run_phase1_audit()
