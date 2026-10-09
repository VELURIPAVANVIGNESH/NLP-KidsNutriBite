import os
import sys
import json
import csv
import hashlib
import numpy as np
import faiss

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def calculate_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def run_phase3_3_indexing_audit():
    corpus_path = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")
    bm25_path = os.path.join(BASE_DIR, "data", "processed", "bm25_index.json")
    faiss_path = os.path.join(BASE_DIR, "data", "processed", "dense_index.faiss")
    dense_map_path = os.path.join(BASE_DIR, "data", "processed", "dense_index_map.json")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 3.3 DUAL INDEXING AUDIT")
    print("============================================================")

    # 1. Read BM25 index
    with open(bm25_path, 'r', encoding='utf-8') as f:
        bm25 = json.load(f)

    bm25_doc_count = bm25.get("corpus_doc_count", 0)
    bm25_vocab_size = len(bm25.get("idf", {}))
    print(f"[+] BM25 Index Doc Count: {bm25_doc_count} (Target: 6,429)")
    print(f"[+] BM25 Index Vocabulary Size: {bm25_vocab_size:,} unique terms")
    print(f"[+] BM25 Parameters: k1={bm25.get('k1')}, b={bm25.get('b')}")

    # 2. Read FAISS index
    index = faiss.read_index(faiss_path)
    faiss_total = index.ntotal
    faiss_dim = index.d
    print(f"[+] FAISS Index Total Vectors: {faiss_total} (Target: 6,429)")
    print(f"[+] FAISS Embedding Dimension: {faiss_dim} (BGE-small-en-v1.5 target: 384)")

    # 3. Vector NaN/Inf & L2 Normalization Check
    has_nan_or_inf = False
    unnormalized_count = 0
    for idx in range(faiss_total):
        vec = index.reconstruct(idx)
        if np.isnan(vec).any() or np.isinf(vec).any():
            has_nan_or_inf = True
        l2_norm = float(np.linalg.norm(vec))
        if abs(l2_norm - 1.0) > 1e-3:
            unnormalized_count += 1

    print(f"[+] FAISS Vectors NaN/Inf check: {'FAIL' if has_nan_or_inf else 'PASSED (0 NaN/Inf found)'}")
    print(f"[+] FAISS Vectors L2 Normalization check: {'FAIL' if unnormalized_count > 0 else 'PASSED (100% normalized)'}")

    # 4. Read Dense Map & Check Parity
    with open(dense_map_path, 'r', encoding='utf-8') as f:
        dense_map = json.load(f)
    print(f"[+] Dense Mapping Count: {len(dense_map)} (Target: 6,422)")

    with open(corpus_path, 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    parity_mismatches = 0
    for i in range(6422):
        if corpus[i]["chunk_id"] != bm25["doc_ids"][i] or corpus[i]["chunk_id"] != dense_map[i]:
            parity_mismatches += 1

    print(f"[+] Bi-directional Mapping Parity Mismatches: {parity_mismatches}")

    # 5. Check Index Hashes
    bm25_hash = calculate_md5(bm25_path)
    faiss_hash = calculate_md5(faiss_path)
    map_hash = calculate_md5(dense_map_path)
    print(f"[+] BM25 Index Hash: {bm25_hash}")
    print(f"[+] FAISS Index Hash: {faiss_hash}")
    print(f"[+] Dense Map Hash: {map_hash}")

    return {
        "bm25_doc_count": bm25_doc_count,
        "bm25_vocab_size": bm25_vocab_size,
        "faiss_total": faiss_total,
        "faiss_dim": faiss_dim,
        "has_nan_or_inf": has_nan_or_inf,
        "unnormalized_count": unnormalized_count,
        "parity_mismatches": parity_mismatches
    }

if __name__ == "__main__":
    run_phase3_3_indexing_audit()
