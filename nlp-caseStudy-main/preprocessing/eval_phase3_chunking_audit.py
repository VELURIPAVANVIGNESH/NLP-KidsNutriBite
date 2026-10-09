import os
import sys
import json
import csv
import hashlib
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.chunk_documents import main as run_chunker

def calculate_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb', encoding='utf-8') as f:
        buf = f.read(65536).encode('utf-8')
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536).encode('utf-8')
    return hasher.hexdigest()

def calculate_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def run_phase3_chunking_audit():
    corpus_path = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")
    chunks_dir = os.path.join(BASE_DIR, "data", "processed", "chunks")

    print("============================================================")
    print("STARTING INDEPENDENT PHASE 3.0-3.2 CHUNKING AUDIT")
    print("============================================================")

    # 1. Read preprocessed_corpus.json
    with open(corpus_path, 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    total_chunks = len(corpus)
    print(f"[+] Total chunks in preprocessed_corpus.json: {total_chunks}")

    total_chars = sum(len(c["text"]) for c in corpus)
    avg_char_len = (total_chars / float(total_chunks)) if total_chunks > 0 else 0.0
    print(f"[+] Total characters in chunked corpus: {total_chars:,}")
    print(f"[+] Average chunk character length: {avg_char_len:.1f} characters")

    # 2. Check unique chunk IDs
    unique_ids = set(c["chunk_id"] for c in corpus)
    duplicate_ids_count = total_chunks - len(unique_ids)
    print(f"[+] Unique chunk IDs: {len(unique_ids)} / {total_chunks} (Duplicate IDs: {duplicate_ids_count})")

    # 3. IFCT Table Chunks Analysis
    ifct_chunks = [c for c in corpus if c["source_id"] == "NK-010"]
    ifct_table_chunks = [c for c in ifct_chunks if "Category:" in c.get("context_prefix", "")]
    print(f"[+] Total IFCT document chunks (NK-010): {len(ifct_chunks)}")
    print(f"[+] IFCT specialized table-row chunks: {len(ifct_table_chunks)}")

    # 4. Metadata Completeness
    meta_incomplete = 0
    page_incomplete = 0
    mandatory_fields = ["chunk_id", "source_id", "source_name", "file_name", "relative_path", "page_numbers", "publisher", "publication_year", "document_type", "authority_tier", "domain", "text"]

    for c in corpus:
        if any(f not in c or c[f] is None for f in mandatory_fields):
            meta_incomplete += 1
        if not c.get("page_numbers") or not isinstance(c.get("page_numbers"), list):
            page_incomplete += 1

    print(f"[+] Chunks with incomplete metadata fields: {meta_incomplete}")
    print(f"[+] Chunks with incomplete page provenance: {page_incomplete}")

    # 5. Reproducibility Test
    initial_corpus_hash = calculate_md5(corpus_path)
    run_chunker()
    post_corpus_hash = calculate_md5(corpus_path)

    reproducible = (initial_corpus_hash == post_corpus_hash)
    print(f"[+] Reproducibility Test (Re-generated Corpus JSON Hash Match): {'PASSED' if reproducible else 'FAILED'}")

    return {
        "total_chunks": total_chunks,
        "avg_char_len": avg_char_len,
        "unique_ids": len(unique_ids),
        "duplicate_ids": duplicate_ids_count,
        "ifct_total_chunks": len(ifct_chunks),
        "ifct_table_chunks": len(ifct_table_chunks),
        "meta_incomplete": meta_incomplete,
        "page_incomplete": page_incomplete,
        "reproducible": reproducible
    }

if __name__ == "__main__":
    run_phase3_chunking_audit()
