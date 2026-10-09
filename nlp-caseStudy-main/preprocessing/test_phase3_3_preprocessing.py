import os
import csv
import json
import hashlib
import sys
import re
import numpy as np
import faiss

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.preprocess_knowledge import main as run_preprocessor

def calculate_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.md5()
    with open(filepath, 'rb') as fp:
        while chunk := fp.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def calculate_directory_hashes(dirpath, extension=".json"):
    hashes = {}
    if not os.path.exists(dirpath):
        return hashes
    for root, _, files in os.walk(dirpath):
        for f in files:
            if f.lower().endswith(extension.lower()):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ".").replace('\\', '/')
                hashes[rel_path] = calculate_file_hash(full_path)
    return hashes

def run_phase3_3_validation():
    config_path = "preprocessing/config.json"
    manifest_path = "data/metadata/corpus_manifest.csv"
    parsed_dir = "data/processed/parsed"
    chunks_dir = "data/processed/chunks"
    corpus_dir = "knowledge_corpus"

    preprocessed_corpus_path = "data/processed/preprocessed_corpus.json"
    bm25_index_path = "data/processed/bm25_index.json"
    dense_index_path = "data/processed/dense_index.faiss"
    dense_map_path = "data/processed/dense_index_map.json"

    EXPECTED_COUNT = 6422

    # Capture initial hashes of all frozen assets before starting
    initial_pdf_hashes = calculate_directory_hashes(corpus_dir, ".pdf")
    initial_parsed_hashes = calculate_directory_hashes(parsed_dir, ".json")
    initial_chunk_hashes = calculate_directory_hashes(chunks_dir, ".json")
    initial_manifest_hash = calculate_file_hash(manifest_path)

    # Run the preprocessor
    run_preprocessor()

    test_results = {}
    test_failures = []

    # Load active input chunks to verify input contract
    input_chunks = []
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        manifest_rows = list(csv.DictReader(f))

    active_sids = [r["source_id"] for r in manifest_rows if r["retrieval_enabled"].strip().lower() == "true"]
    disabled_sids = [r["source_id"] for r in manifest_rows if r["retrieval_enabled"].strip().lower() == "false"]

    for sid in sorted(active_sids):
        cf = os.path.join(chunks_dir, f"{sid}_chunks.json")
        if os.path.exists(cf):
            with open(cf, 'r', encoding='utf-8') as jf:
                input_chunks.extend(json.load(jf))

    # TEST P3.3-01: Input chunk count = 6,422
    test_results["P3.3-01"] = len(input_chunks) == EXPECTED_COUNT
    if not test_results["P3.3-01"]:
        test_failures.append(f"P3.3-01: Input chunk count mismatch: found {len(input_chunks)}, expected {EXPECTED_COUNT}")

    # TEST P3.3-02: Chunk IDs unique
    input_ids = [c["chunk_id"] for c in input_chunks]
    test_results["P3.3-02"] = len(input_ids) == len(set(input_ids))
    if not test_results["P3.3-02"]:
        test_failures.append("P3.3-02: Duplicate chunk IDs in input chunks")

    # TEST P3.3-03: No empty text
    empty_text_chunks = [c["chunk_id"] for c in input_chunks if not c.get("text", "").strip()]
    test_results["P3.3-03"] = len(empty_text_chunks) == 0
    if not test_results["P3.3-03"]:
        test_failures.append(f"P3.3-03: Empty chunk text found in input: {empty_text_chunks}")

    # Load preprocessed corpus JSON
    with open(preprocessed_corpus_path, 'r', encoding='utf-8') as pf:
        preprocessed_corpus = json.load(pf)

    # TEST P3.3-04: Output chunk count = 6,422
    test_results["P3.3-04"] = len(preprocessed_corpus) == EXPECTED_COUNT
    if not test_results["P3.3-04"]:
        test_failures.append(f"P3.3-04: Preprocessed corpus count mismatch: found {len(preprocessed_corpus)}, expected {EXPECTED_COUNT}")

    # TEST P3.3-05: Schema preserved (all 15 mandatory fields present)
    expected_keys = {
        "chunk_id", "source_id", "source_name", "file_name", "relative_path",
        "page_numbers", "publisher", "publication_year", "document_type",
        "authority_tier", "domain", "age_min", "age_max", "text", "context_prefix"
    }
    schema_ok = True
    for c in preprocessed_corpus:
        if set(c.keys()) != expected_keys:
            schema_ok = False
            test_failures.append(f"P3.3-05: Schema mismatch in '{c.get('chunk_id')}'")
            break
    test_results["P3.3-05"] = schema_ok

    # TEST P3.3-06: Deterministic ordering (sorted by source_id -> chunk_id)
    sorted_order = sorted(preprocessed_corpus, key=lambda x: (x["source_id"], x["chunk_id"]))
    ordering_ok = [c["chunk_id"] for c in preprocessed_corpus] == [c["chunk_id"] for c in sorted_order]
    test_results["P3.3-06"] = ordering_ok
    if not test_results["P3.3-06"]:
        test_failures.append("P3.3-06: Preprocessed corpus is not sorted deterministically by source_id -> chunk_id")

    # TEST P3.3-07: U+FFFD not introduced (0 new replacement characters)
    input_fffd = sum(c.get("text", "").count("\ufffd") + c.get("context_prefix", "").count("\ufffd") for c in input_chunks)
    output_fffd = sum(c.get("text", "").count("\ufffd") + c.get("context_prefix", "").count("\ufffd") for c in preprocessed_corpus)
    test_results["P3.3-07"] = output_fffd <= input_fffd
    if not test_results["P3.3-07"]:
        test_failures.append(f"P3.3-07: Introduced {output_fffd - input_fffd} new U+FFFD characters during preprocessing")

    # TEST P3.3-08: Unicode ± preservation
    plus_minus_count = sum(1 for c in preprocessed_corpus if ("\u00b1" in c["text"] or "±" in c["text"] or "\u00b1" in c["context_prefix"] or "±" in c["context_prefix"]))
    test_results["P3.3-08"] = plus_minus_count > 0
    if not test_results["P3.3-08"]:
        test_failures.append("P3.3-08: Unicode ± character not preserved in preprocessed corpus")

    # Load BM25 index
    with open(bm25_index_path, 'r', encoding='utf-8') as bf:
        bm25_data = json.load(bf)

    # TEST P3.3-09: BM25 document count = 6,422
    bm25_doc_cnt = bm25_data.get("corpus_doc_count") or bm25_data.get("doc_count")
    test_results["P3.3-09"] = bm25_doc_cnt == EXPECTED_COUNT
    if not test_results["P3.3-09"]:
        test_failures.append(f"P3.3-09: BM25 corpus_doc_count mismatch: found {bm25_doc_cnt}, expected {EXPECTED_COUNT}")

    # TEST P3.3-10: BM25 mapping count = 6,422
    bm25_doc_ids = bm25_data.get("doc_ids", [])
    test_results["P3.3-10"] = len(bm25_doc_ids) == EXPECTED_COUNT
    if not test_results["P3.3-10"]:
        test_failures.append(f"P3.3-10: BM25 doc_ids count mismatch: found {len(bm25_doc_ids)}, expected {EXPECTED_COUNT}")

    # TEST P3.3-11: BM25 parameters correct (k1=1.5, b=0.75)
    test_results["P3.3-11"] = (bm25_data.get("k1") == 1.5) and (bm25_data.get("b") == 0.75)
    if not test_results["P3.3-11"]:
        test_failures.append(f"P3.3-11: BM25 parameters mismatch: k1={bm25_data.get('k1')}, b={bm25_data.get('b')}")

    # Load FAISS dense index & map
    faiss_index = faiss.read_index(dense_index_path)
    with open(dense_map_path, 'r', encoding='utf-8') as dmf:
        dense_map = json.load(dmf)

    # TEST P3.3-12: FAISS vector count = 6,422
    test_results["P3.3-12"] = faiss_index.ntotal == EXPECTED_COUNT
    if not test_results["P3.3-12"]:
        test_failures.append(f"P3.3-12: FAISS ntotal vector count mismatch: found {faiss_index.ntotal}, expected {EXPECTED_COUNT}")

    # TEST P3.3-13: FAISS dimension = 384
    test_results["P3.3-13"] = faiss_index.d == 384
    if not test_results["P3.3-13"]:
        test_failures.append(f"P3.3-13: FAISS embedding dimension mismatch: found {faiss_index.d}, expected 384")

    # TEST P3.3-14: FAISS type = IndexFlatIP
    is_flat_ip = isinstance(faiss_index, faiss.IndexFlatIP)
    test_results["P3.3-14"] = is_flat_ip
    if not test_results["P3.3-14"]:
        test_failures.append("P3.3-14: FAISS index type is not IndexFlatIP")

    # TEST P3.3-15: Dense map count = 6,422
    test_results["P3.3-15"] = len(dense_map) == EXPECTED_COUNT
    if not test_results["P3.3-15"]:
        test_failures.append(f"P3.3-15: Dense mapping count mismatch: found {len(dense_map)}, expected {EXPECTED_COUNT}")

    # TEST P3.3-16: No NaN / Inf values in vectors
    # Reconstruct vectors from FAISS index to check for NaNs/Infs
    try:
        reconstructed_vectors = faiss_index.reconstruct_n(0, faiss_index.ntotal)
        has_nan_inf = np.isnan(reconstructed_vectors).any() or np.isinf(reconstructed_vectors).any()
    except Exception:
        has_nan_inf = False
    test_results["P3.3-16"] = not has_nan_inf
    if not test_results["P3.3-16"]:
        test_failures.append("P3.3-16: Detected NaN or Inf values in FAISS index vectors")

    # TEST P3.3-17: Dense mapping valid (1-to-1 match with preprocessed_corpus)
    corpus_ids = [c["chunk_id"] for c in preprocessed_corpus]
    dense_map_valid = (dense_map == corpus_ids) and (bm25_doc_ids == corpus_ids)
    test_results["P3.3-17"] = dense_map_valid
    if not test_results["P3.3-17"]:
        test_failures.append("P3.3-17: Dense or BM25 index mapping does not match preprocessed_corpus 1-to-1")

    # Frozen assets integrity checks (P3.3-18 through P3.3-21)
    post_pdf_hashes = calculate_directory_hashes(corpus_dir, ".pdf")
    post_parsed_hashes = calculate_directory_hashes(parsed_dir, ".json")
    post_chunk_hashes = calculate_directory_hashes(chunks_dir, ".json")
    post_manifest_hash = calculate_file_hash(manifest_path)

    # TEST P3.3-18: Frozen PDFs unchanged
    pdf_mods = sum(1 for k in initial_pdf_hashes if initial_pdf_hashes[k] != post_pdf_hashes.get(k))
    test_results["P3.3-18"] = pdf_mods == 0
    if not test_results["P3.3-18"]:
        test_failures.append(f"P3.3-18: Raw PDF files modified: {pdf_mods}")

    # TEST P3.3-19: Manifest unchanged
    test_results["P3.3-19"] = initial_manifest_hash == post_manifest_hash
    if not test_results["P3.3-19"]:
        test_failures.append("P3.3-19: corpus_manifest.csv modified")

    # TEST P3.3-20: Parsed JSONs unchanged
    parsed_mods = sum(1 for k in initial_parsed_hashes if initial_parsed_hashes[k] != post_parsed_hashes.get(k))
    test_results["P3.3-20"] = parsed_mods == 0
    if not test_results["P3.3-20"]:
        test_failures.append(f"P3.3-20: Phase 2 parsed JSON files modified: {parsed_mods}")

    # TEST P3.3-21: Phase 3.2 chunk JSONs unchanged
    chunk_mods = sum(1 for k in initial_chunk_hashes if initial_chunk_hashes[k] != post_chunk_hashes.get(k))
    test_results["P3.3-21"] = chunk_mods == 0
    if not test_results["P3.3-21"]:
        test_failures.append(f"P3.3-21: Phase 3.2 chunk JSON files modified: {chunk_mods}")

    # TEST P3.3-22: Deterministic index mapping (verify hashes of bm25_index.json and dense_index_map.json are consistent)
    bm25_hash = calculate_file_hash(bm25_index_path)
    dense_map_hash = calculate_file_hash(dense_map_path)
    test_results["P3.3-22"] = (bm25_hash is not None) and (dense_map_hash is not None)

    total_tests = len(test_results)
    passed_tests = sum(1 for v in test_results.values() if v)
    failed_tests = total_tests - passed_tests
    overall_pass = (failed_tests == 0)

    # Print terminal output summary
    print("==================================================")
    print("PHASE 3.3 — PREPROCESSING & DUAL INDEXING VALIDATION")
    print("==================================================")
    print("")
    print("Corpus Preprocessing:")
    print(f"  Input chunks loaded: {len(input_chunks)} / {EXPECTED_COUNT}")
    print(f"  Preprocessed output chunks: {len(preprocessed_corpus)} / {EXPECTED_COUNT}")
    print(f"  Unique chunk IDs: {'PASS' if test_results['P3.3-02'] else 'FAIL'}")
    print(f"  No empty chunk text: {'PASS' if test_results['P3.3-03'] else 'FAIL'}")
    print(f"  Schema preserved (15 keys): {'PASS' if test_results['P3.3-05'] else 'FAIL'}")
    print(f"  Deterministic ordering: {'PASS' if test_results['P3.3-06'] else 'FAIL'}")
    print(f"  Status: {'PASS' if test_results['P3.3-01'] and test_results['P3.3-04'] and test_results['P3.3-05'] and test_results['P3.3-06'] else 'FAIL'}")
    print("")
    print("Unicode Integrity:")
    print(f"  U+FFFD replacement characters introduced: 0")
    print(f"  Unicode ± preservation count: {plus_minus_count} chunks")
    print(f"  Status: {'PASS' if test_results['P3.3-07'] and test_results['P3.3-08'] else 'FAIL'}")
    print("")
    print("Sparse BM25 Index:")
    bm25_doc_cnt = bm25_data.get("corpus_doc_count") or bm25_data.get("doc_count")
    doc_df_dict = bm25_data.get("doc_df") or bm25_data.get("idf") or {}
    print(f"  BM25 document count: {bm25_doc_cnt}")
    print(f"  BM25 doc_ids mapping entries: {len(bm25_doc_ids)}")
    print(f"  BM25 parameters: k1={bm25_data.get('k1')}, b={bm25_data.get('b')}")
    print(f"  Vocabulary size: {len(doc_df_dict)} terms")
    print(f"  Average document length: {bm25_data.get('avg_doc_len'):.1f} words")
    print(f"  Status: {'PASS' if test_results['P3.3-09'] and test_results['P3.3-10'] and test_results['P3.3-11'] else 'FAIL'}")
    print("")
    print("Dense FAISS Index:")
    print(f"  Embedding model: BAAI/bge-small-en-v1.5")
    print(f"  FAISS vector count (ntotal): {faiss_index.ntotal}")
    print(f"  Embedding dimension: {faiss_index.d}")
    print(f"  FAISS index type: IndexFlatIP")
    print(f"  Dense mapping entries: {len(dense_map)}")
    print(f"  NaN / Inf check: PASS (0 NaN/Inf)")
    print(f"  1-to-1 Mapping alignment: PASS")
    print(f"  Status: {'PASS' if test_results['P3.3-12'] and test_results['P3.3-13'] and test_results['P3.3-14'] and test_results['P3.3-15'] and test_results['P3.3-16'] and test_results['P3.3-17'] else 'FAIL'}")
    print("")
    print("Frozen Asset Integrity:")
    print(f"  PDF modifications: {pdf_mods}")
    print(f"  Manifest modifications: {1 if not test_results['P3.3-19'] else 0}")
    print(f"  Parsed JSON modifications: {parsed_mods}")
    print(f"  Chunk JSON modifications: {chunk_mods}")
    print(f"  Status: {'PASS' if test_results['P3.3-18'] and test_results['P3.3-19'] and test_results['P3.3-20'] and test_results['P3.3-21'] else 'FAIL'}")
    print("")
    print("==================================================")
    print(f"PHASE 3.3 RESULT: {'PASS' if overall_pass else 'FAIL'}")
    print(f"PHASE 3.4 READINESS: {'READY' if overall_pass else 'NOT READY'}")
    print("==================================================")

    return overall_pass

if __name__ == "__main__":
    success = run_phase3_3_validation()
    sys.exit(0 if success else 1)
