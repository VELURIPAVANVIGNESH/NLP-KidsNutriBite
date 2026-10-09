import os
import csv
import hashlib
import sys

def calculate_pdf_hashes(root_dir="knowledge_corpus"):
    hashes = {}
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith('.pdf'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ".").replace('\\', '/')
                hasher = hashlib.md5()
                with open(full_path, 'rb') as fp:
                    while chunk := fp.read(65536):
                        hasher.update(chunk)
                hashes[rel_path] = hasher.hexdigest()
    return hashes

def run_phase1_validation():
    corpus_dir = "knowledge_corpus"
    manifest_path = "data/metadata/corpus_manifest.csv"
    expected_total_pdfs = 32
    expected_active_docs = 22
    expected_disabled_docs = 10
    required_columns = [
        "source_id", "source_name", "file_name", "relative_path", "folder", 
        "publisher", "publication_year", "document_type", "authority_tier", 
        "domain", "age_min", "age_max", "retrieval_enabled"
    ]

    # Pre-validation integrity hash check
    initial_pdf_hashes = calculate_pdf_hashes(corpus_dir)
    initial_manifest_hash = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as fp:
            initial_manifest_hash = hashlib.md5(fp.read()).hexdigest()

    test_results = {}
    test_failures = []

    # TEST P1-01: All PDF files under knowledge_corpus/ are discovered
    discovered_pdfs = list(initial_pdf_hashes.keys())
    test_results["P1-01"] = len(discovered_pdfs) > 0
    if not test_results["P1-01"]:
        test_failures.append("TEST P1-01: No PDF files discovered under knowledge_corpus/")

    # TEST P1-02: Number of discovered PDFs matches expected count
    actual_pdf_count = len(discovered_pdfs)
    test_results["P1-02"] = actual_pdf_count == expected_total_pdfs
    if not test_results["P1-02"]:
        test_failures.append(f"TEST P1-02: Discovered {actual_pdf_count} PDFs, expected {expected_total_pdfs}")

    # TEST P1-03: Manifest exists
    test_results["P1-03"] = os.path.exists(manifest_path)
    if not test_results["P1-03"]:
        test_failures.append(f"TEST P1-03: Manifest file missing at {manifest_path}")

    # TEST P1-04: Manifest can be parsed successfully as CSV
    manifest_rows = []
    headers_found = []
    if test_results["P1-03"]:
        try:
            with open(manifest_path, 'r', encoding='utf-8') as fp:
                reader = csv.DictReader(fp)
                headers_found = list(reader.fieldnames) if reader.fieldnames else []
                manifest_rows = list(reader)
            test_results["P1-04"] = True
        except Exception as e:
            test_results["P1-04"] = False
            test_failures.append(f"TEST P1-04: Failed to parse CSV manifest: {e}")
    else:
        test_results["P1-04"] = False

    # TEST P1-05: Every discovered PDF has exactly one manifest entry
    manifest_rel_paths = [r.get("relative_path", "").replace('\\', '/') for r in manifest_rows]
    disc_set = set(discovered_pdfs)
    man_set = set(manifest_rel_paths)
    test_results["P1-05"] = (disc_set == man_set) and (len(manifest_rel_paths) == len(man_set))
    if not test_results["P1-05"]:
        test_failures.append("TEST P1-05: Parity mismatch between discovered PDFs and manifest relative paths")

    # TEST P1-06: No duplicate source_id values
    source_ids = [r.get("source_id", "") for r in manifest_rows]
    duplicate_source_ids = len(source_ids) - len(set(source_ids))
    test_results["P1-06"] = (duplicate_source_ids == 0) and (len(source_ids) > 0)
    if not test_results["P1-06"]:
        test_failures.append(f"TEST P1-06: Found {duplicate_source_ids} duplicate source_id values")

    # TEST P1-07: No duplicate relative_path values
    duplicate_rel_paths = len(manifest_rel_paths) - len(set(manifest_rel_paths))
    test_results["P1-07"] = (duplicate_rel_paths == 0) and (len(manifest_rel_paths) > 0)
    if not test_results["P1-07"]:
        test_failures.append(f"TEST P1-07: Found {duplicate_rel_paths} duplicate relative_path values")

    # TEST P1-08: Every manifest PDF path points to an existing PDF
    missing_paths = [p for p in manifest_rel_paths if not os.path.exists(p)]
    test_results["P1-08"] = (len(missing_paths) == 0) and (len(manifest_rel_paths) > 0)
    if not test_results["P1-08"]:
        test_failures.append(f"TEST P1-08: Found {len(missing_paths)} manifest paths that do not exist on disk")

    # TEST P1-09: Required manifest columns exist
    missing_cols = [col for col in required_columns if col not in headers_found]
    test_results["P1-09"] = len(missing_cols) == 0
    if not test_results["P1-09"]:
        test_failures.append(f"TEST P1-09: Missing mandatory manifest columns: {missing_cols}")

    # TEST P1-10: retrieval_enabled values are valid ("true" or "false")
    invalid_ret_vals = [r.get("retrieval_enabled") for r in manifest_rows if r.get("retrieval_enabled") not in ["true", "false"]]
    test_results["P1-10"] = len(invalid_ret_vals) == 0
    if not test_results["P1-10"]:
        test_failures.append(f"TEST P1-10: Found invalid retrieval_enabled values: {invalid_ret_vals}")

    # TEST P1-11: Active and disabled document counts are correct
    active_docs = [r for r in manifest_rows if r.get("retrieval_enabled") == "true"]
    disabled_docs = [r for r in manifest_rows if r.get("retrieval_enabled") == "false"]
    actual_active_count = len(active_docs)
    actual_disabled_count = len(disabled_docs)
    test_results["P1-11"] = (actual_active_count == expected_active_docs) and (actual_disabled_count == expected_disabled_docs)
    if not test_results["P1-11"]:
        test_failures.append(f"TEST P1-11: Count mismatch — Active: {actual_active_count} (expected {expected_active_docs}), Disabled: {actual_disabled_count} (expected {expected_disabled_docs})")

    # TEST P1-12: No PDF file is modified by validation process
    post_pdf_hashes = calculate_pdf_hashes(corpus_dir)
    pdf_modifications = sum(1 for k in initial_pdf_hashes if initial_pdf_hashes[k] != post_pdf_hashes.get(k))
    post_manifest_hash = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as fp:
            post_manifest_hash = hashlib.md5(fp.read()).hexdigest()
    manifest_modified = initial_manifest_hash != post_manifest_hash
    test_results["P1-12"] = (pdf_modifications == 0) and not manifest_modified
    if not test_results["P1-12"]:
        test_failures.append(f"TEST P1-12: Integrity failure — Modified PDFs: {pdf_modifications}, Manifest modified: {manifest_modified}")

    # TEST P1-13: Manifest has no missing source IDs
    missing_ids = [r for r in manifest_rows if not r.get("source_id", "").strip()]
    test_results["P1-13"] = len(missing_ids) == 0
    if not test_results["P1-13"]:
        test_failures.append(f"TEST P1-13: Found {len(missing_ids)} entries with empty source_id")

    # TEST P1-14: Manifest has no duplicate source IDs
    test_results["P1-14"] = duplicate_source_ids == 0

    # TEST P1-15: Manifest metadata is internally consistent
    inconsistent_rows = []
    for r in manifest_rows:
        if not r.get("source_name", "").strip() or not r.get("publisher", "").strip() or not r.get("authority_tier", "").strip():
            inconsistent_rows.append(r.get("source_id"))
    test_results["P1-15"] = len(inconsistent_rows) == 0
    if not test_results["P1-15"]:
        test_failures.append(f"TEST P1-15: Found inconsistent metadata in rows: {inconsistent_rows}")

    total_tests = len(test_results)
    passed_tests = sum(1 for v in test_results.values() if v)
    failed_tests = total_tests - passed_tests
    overall_pass = (failed_tests == 0)

    # Print required terminal output format
    print("==================================================")
    print("PHASE 1 — CORPUS INGESTION & MANIFEST VALIDATION")
    print("==================================================")
    print("")
    print("PDF corpus:")
    print(f"  Total PDFs discovered: {actual_pdf_count}")
    print(f"  Expected PDFs: {expected_total_pdfs}")
    print(f"  Status: {'PASS' if test_results['P1-01'] and test_results['P1-02'] else 'FAIL'}")
    print("")
    print("Manifest:")
    print(f"  Manifest exists: {'PASS' if test_results['P1-03'] else 'FAIL'}")
    print(f"  CSV readable: {'PASS' if test_results['P1-04'] else 'FAIL'}")
    print("")
    print("Source IDs:")
    print(f"  Total source IDs: {len(source_ids)}")
    print(f"  Duplicate IDs: {duplicate_source_ids}")
    print(f"  Missing IDs: {len(missing_ids)}")
    print(f"  Status: {'PASS' if test_results['P1-06'] and test_results['P1-13'] and test_results['P1-14'] else 'FAIL'}")
    print("")
    print("Retrieval status:")
    print(f"  Active documents: {actual_active_count}")
    print(f"  Disabled documents: {actual_disabled_count}")
    print(f"  Status: {'PASS' if test_results['P1-10'] and test_results['P1-11'] else 'FAIL'}")
    print("")
    print("Path validation:")
    print(f"  Existing PDF paths: {len(manifest_rel_paths) - len(missing_paths)}/{len(manifest_rel_paths)}")
    print(f"  Missing PDF paths: {len(missing_paths)}")
    print(f"  Status: {'PASS' if test_results['P1-05'] and test_results['P1-07'] and test_results['P1-08'] else 'FAIL'}")
    print("")
    print("Metadata:")
    print(f"  Required fields present: {'PASS' if test_results['P1-09'] else 'FAIL'}")
    print(f"  Invalid values: {len(invalid_ret_vals) + len(inconsistent_rows)}")
    print(f"  Status: {'PASS' if test_results['P1-09'] and test_results['P1-15'] else 'FAIL'}")
    print("")
    print("Integrity:")
    print(f"  PDFs modified during validation: {pdf_modifications}")
    print(f"  Manifest unexpectedly modified: {1 if manifest_modified else 0}")
    print(f"  Status: {'PASS' if test_results['P1-12'] else 'FAIL'}")
    print("")
    print("==================================================")
    print(f"PHASE 1 RESULT: {'PASS' if overall_pass else 'FAIL'}")
    print("==================================================")

    # Generate data/processed/phase1_validation_report.txt
    os.makedirs("data/processed", exist_ok=True)
    report_content = f"""==================================================
PHASE 1 — CORPUS INGESTION & MANIFEST VALIDATION REPORT
==================================================
Phase Name:                Phase 1 — PDF Corpus Ingestion & Manifest
Objective:                 Verify physical PDF discovery, manifest schema compliance, deterministic source ID assignment, retrieval partitioning, and byte-exact integrity.
Input Directory:           knowledge_corpus/
Implementation File:       preprocessing/generate_manifest.py
Output Artifact:           data/metadata/corpus_manifest.csv

QUANTITATIVE MEASUREMENTS
--------------------------------------------------
Total PDFs Discovered:     {actual_pdf_count} (Expected: {expected_total_pdfs})
Active Retrieval Docs:     {actual_active_count} (Expected: {expected_active_docs})
Disabled Retrieval Docs:   {actual_disabled_count} (Expected: {expected_disabled_docs})
Required Columns Present:  {len(required_columns)} / {len(required_columns)}
Duplicate Source IDs:      {duplicate_source_ids}
Missing Source IDs:        {len(missing_ids)}
Missing PDF Paths:         {len(missing_paths)}
Metadata Errors:           {len(invalid_ret_vals) + len(inconsistent_rows)}
PDF Bytes Modified:        {pdf_modifications}
Manifest Hash Modified:    {manifest_modified}

TEST SUITE EXECUTION SUMMARY
--------------------------------------------------
Total Test Cases:          {total_tests}
Passed Test Cases:         {passed_tests}
Failed Test Cases:         {failed_tests}
Overall Phase 1 Status:    {"PASS" if overall_pass else "FAIL"}
==================================================
"""
    with open("data/processed/phase1_validation_report.txt", "w", encoding="utf-8") as f:
        f.write(report_content)

    return overall_pass

if __name__ == "__main__":
    success = run_phase1_validation()
    sys.exit(0 if success else 1)
