import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import csv
import json
import re
import sys
import hashlib
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import torch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieval_repr import generate_retrieval_text

sys.stdout.reconfigure(encoding='utf-8')

def load_config(config_path="preprocessing/config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_md5(file_path):
    if not os.path.exists(file_path):
        return None
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def capture_frozen_assets_hashes(active_doc_ids, parsed_dir, chunks_dir, manifest_path, corpus_dir):
    hashes = {}
    
    # 1. manifest
    hashes[manifest_path] = compute_md5(manifest_path)
    
    # 2. PDFs in knowledge_corpus
    for root, _, files in os.walk(corpus_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.join(root, file)
                hashes[path] = compute_md5(path)
                
    # 3. Parsed JSON files
    for root, _, files in os.walk(parsed_dir):
        for file in files:
            if file.lower().endswith(".json"):
                path = os.path.join(root, file)
                hashes[path] = compute_md5(path)
                
    # 4. Chunk JSON files
    for sid in active_doc_ids:
        path = os.path.join(chunks_dir, f"{sid}_chunks.json")
        if os.path.exists(path):
            hashes[path] = compute_md5(path)
            
    return hashes

def verify_frozen_assets_hashes(saved_hashes):
    print("--- RUNNING FROZEN ASSETS INTEGRITY HASH CHECK ---")
    mismatches = []
    for path, saved_hash in saved_hashes.items():
        current_hash = compute_md5(path)
        if current_hash != saved_hash:
            mismatches.append(f"File modified: {path} (Expected: {saved_hash}, Got: {current_hash})")
    
    if mismatches:
        print(f"[-] ERROR: Frozen assets hash check FAILED with {len(mismatches)} modifications!")
        for m in mismatches:
            print(f"  - {m}")
        return False, mismatches
    print("[+] Frozen assets hash check PASSED. No modifications detected.")
    return True, []

def clean_text(text):
    if not text:
        return ""
    # 1. Remove carriage returns
    txt = text.replace("\r", "")
    # 2. Normalize excessive spaces within lines
    txt = re.sub(r'[ \t]+', ' ', txt)
    # 3. Normalize excessive newlines (max 2 consecutive newlines)
    txt = re.sub(r'\n\n+', '\n\n', txt)
    return txt.strip()

class BM25Index:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus_doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_lens = []
        self.doc_ids = []
        self.idf = {}
        self.doc_df = {}
        self.inverted_index = {}

    def tokenize(self, text):
        return re.findall(r'\b\w+\b', text.lower())

    def fit(self, doc_list):
        self.corpus_doc_count = len(doc_list)
        total_len = 0
        temp_dfs = {}
        
        for idx, doc in enumerate(doc_list):
            chunk_id = doc["chunk_id"]
            self.doc_ids.append(chunk_id)
            
            tokens = self.tokenize(doc["search_text"])
            doc_len = len(tokens)
            self.doc_lens.append(doc_len)
            total_len += doc_len
            
            doc_tfs = {}
            for t in tokens:
                doc_tfs[t] = doc_tfs.get(t, 0) + 1
                
            for t, tf in doc_tfs.items():
                if t not in self.inverted_index:
                    self.inverted_index[t] = []
                self.inverted_index[t].append([idx, tf])
                temp_dfs[t] = temp_dfs.get(t, 0) + 1
                
        self.avg_doc_len = total_len / self.corpus_doc_count if self.corpus_doc_count > 0 else 0.0
        self.doc_df = temp_dfs
        
        for term, df in self.doc_df.items():
            self.idf[term] = float(np.log(1.0 + (self.corpus_doc_count - df + 0.5) / (df + 0.5)))

    def serialize(self):
        return {
            "k1": self.k1,
            "b": self.b,
            "corpus_doc_count": self.corpus_doc_count,
            "doc_count": self.corpus_doc_count,
            "avg_doc_len": self.avg_doc_len,
            "doc_lens": self.doc_lens,
            "doc_ids": self.doc_ids,
            "idf": self.idf,
            "doc_df": self.doc_df,
            "inverted_index": self.inverted_index,
            "tokenizer_name": "alphanumeric_lowercase_regex"
        }

def main():
    config = load_config()
    
    manifest_path = config["manifest_path"]
    corpus_dir = config["corpus_dir"]
    parsed_dir = config["parsed_dir"]
    chunks_dir = config["chunks_dir"]
    
    preprocessed_corpus_path = config["preprocessed_corpus_path"]
    bm25_index_path = config["bm25_index_path"]
    dense_index_path = config["dense_index_path"]
    dense_map_path = config["dense_map_path"]
    report_path = config["preprocessor_report_path"]
    summary_path = config["preprocessor_summary_path"]
    
    model_name = config["embedding_model_name"]
    k1 = config["bm25_k1"]
    b = config["bm25_b"]
    
    # 1. Load manifest and verify active doc list
    active_docs = []
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["retrieval_enabled"].strip().lower() == "true":
                active_docs.append(row)
                
    active_doc_ids = {doc["source_id"] for doc in active_docs}
    
    # 2. Capture MD5 hashes of all frozen assets before starting
    initial_hashes = capture_frozen_assets_hashes(active_doc_ids, parsed_dir, chunks_dir, manifest_path, corpus_dir)
    print(f"Captured initial hashes for {len(initial_hashes)} frozen assets.")
    
    # 3. Load active chunk JSON files
    loaded_chunks = []
    source_counts = {}
    duplicate_ids = []
    seen_ids = set()
    empty_files = []
    
    for sid in sorted(list(active_doc_ids)):
        chunk_file = os.path.join(chunks_dir, f"{sid}_chunks.json")
        if not os.path.exists(chunk_file):
            print(f"ERROR: Chunk file missing for active source {sid}: {chunk_file}")
            empty_files.append(chunk_file)
            continue
            
        with open(chunk_file, 'r', encoding='utf-8') as cf:
            doc_chunks = json.load(cf)
            if not doc_chunks:
                empty_files.append(chunk_file)
            
            source_counts[sid] = len(doc_chunks)
            for c in doc_chunks:
                cid = c["chunk_id"]
                if cid in seen_ids:
                    duplicate_ids.append(cid)
                seen_ids.add(cid)
                loaded_chunks.append((sid, c))
                
    total_loaded_chunks = len(loaded_chunks)
    print(f"Chunks Loaded: {total_loaded_chunks} across {len(source_counts)} active sources.")
    
    # Input Contract Gate Check (Frozen Phase 3.2 baseline = 6,422 chunks)
    EXPECTED_CONTRACT_COUNT = 6422
    if total_loaded_chunks != EXPECTED_CONTRACT_COUNT:
        print(f"[-] ERROR: Input contract check FAILED! Loaded {total_loaded_chunks} chunks instead of {EXPECTED_CONTRACT_COUNT}.")
        sys.exit(1)
    else:
        print(f"[+] Input contract check PASSED (Exactly {EXPECTED_CONTRACT_COUNT} chunks loaded).")
        
    if duplicate_ids:
        print(f"[-] ERROR: Duplicate chunk IDs detected: {duplicate_ids}")
        sys.exit(1)
        
    # Sort chunks deterministically by source_id -> chunk_id
    loaded_chunks.sort(key=lambda x: (x[0], x[1]["chunk_id"]))
    
    # 4. Perform Text Cleaning & Normalization
    preprocessed_chunks = []
    report_rows = []
    
    chunks_changed_count = 0
    total_char_diff = 0
    plus_minus_count = 0
    replacement_chars_count = 0
    
    for sid, c in loaded_chunks:
        orig_text = c["text"]
        orig_prefix = c["context_prefix"]
        
        cleaned_text = clean_text(orig_text)
        cleaned_prefix = clean_text(orig_prefix)
        
        pm_in_orig = ("\u00b1" in orig_text) or ("\u00b1" in orig_prefix) or ("±" in orig_text) or ("±" in orig_prefix)
        if pm_in_orig:
            plus_minus_count += 1
            
        unicode_replacement_count = cleaned_text.count("\ufffd") + cleaned_prefix.count("\ufffd")
        replacement_chars_count += unicode_replacement_count
        
        orig_len = len(orig_text) + len(orig_prefix)
        cleaned_len = len(cleaned_text) + len(cleaned_prefix)
        char_diff = abs(orig_len - cleaned_len)
        whitespace_changed = (orig_text != cleaned_text) or (orig_prefix != cleaned_prefix)
        
        if whitespace_changed:
            chunks_changed_count += 1
            total_char_diff += char_diff
            
        report_rows.append({
            "chunk_id": c["chunk_id"],
            "original_character_count": orig_len,
            "cleaned_character_count": cleaned_len,
            "characters_changed": char_diff,
            "whitespace_changed": str(whitespace_changed).upper(),
            "plus_minus_present": str(pm_in_orig).upper(),
            "replacement_char_introduced": str(unicode_replacement_count > 0).upper()
        })
        
        preprocessed_chunk = {
            "chunk_id": c["chunk_id"],
            "source_id": c["source_id"],
            "source_name": c["source_name"],
            "file_name": c["file_name"],
            "relative_path": c["relative_path"],
            "page_numbers": c["page_numbers"],
            "publisher": c["publisher"],
            "publication_year": c["publication_year"],
            "document_type": c["document_type"],
            "authority_tier": c["authority_tier"],
            "domain": c["domain"],
            "age_min": c["age_min"],
            "age_max": c["age_max"],
            "text": cleaned_text,
            "context_prefix": cleaned_prefix
        }
        preprocessed_chunks.append(preprocessed_chunk)
        
    # Write preprocessed corpus to file
    with open(preprocessed_corpus_path, 'w', encoding='utf-8') as pcf:
        json.dump(preprocessed_chunks, pcf, indent=2, ensure_ascii=False)
    print(f"Preprocessed corpus saved to: {preprocessed_corpus_path}")
    
    # Write cleaning report CSV
    report_headers = [
        "chunk_id", "original_character_count", "cleaned_character_count", 
        "characters_changed", "whitespace_changed", "plus_minus_present", 
        "replacement_char_introduced"
    ]
    with open(report_path, mode='w', newline='', encoding='utf-8') as rf:
        writer = csv.DictWriter(rf, fieldnames=report_headers)
        writer.writeheader()
        writer.writerows(report_rows)
    print(f"Cleaning report saved to: {report_path}")
    
    # 5. BM25 Index Generation
    # NOTE: search_text uses generate_retrieval_text() for enriched representation.
    # The stored corpus fields (text, context_prefix) are NOT modified.
    print("--- GENERATING SPARSE BM25 INDEX ---")
    bm25_docs = []
    for c in preprocessed_chunks:
        search_text = generate_retrieval_text(c)
        bm25_docs.append({
            "chunk_id": c["chunk_id"],
            "search_text": search_text
        })
        
    bm25 = BM25Index(k1=k1, b=b)
    bm25.fit(bm25_docs)
    
    with open(bm25_index_path, 'w', encoding='utf-8') as bf:
        json.dump(bm25.serialize(), bf, indent=2, ensure_ascii=False)
    print(f"BM25 index saved to: {bm25_index_path}")
    
    # 6. Dense Vector Index Generation
    # NOTE: texts_to_embed uses generate_retrieval_text() for enriched representation.
    # The stored corpus fields (text, context_prefix) are NOT modified.
    print("--- GENERATING DENSE FAISS INDEX ---")
    texts_to_embed = [generate_retrieval_text(c) for c in preprocessed_chunks]
    dense_map = [c["chunk_id"] for c in preprocessed_chunks]
    
    # Invalidate cache if index ntotal does not match EXACTLY 6,422
    use_cache = False
    if os.path.exists(dense_index_path) and os.path.exists(dense_map_path):
        try:
            cached_index = faiss.read_index(dense_index_path)
            with open(dense_map_path, 'r', encoding='utf-8') as dmf:
                cached_map = json.load(dmf)
            if cached_index.ntotal == EXPECTED_CONTRACT_COUNT and len(cached_map) == EXPECTED_CONTRACT_COUNT:
                use_cache = True
                index = cached_index
                dense_map = cached_map
                embedding_dim = index.d
                has_nan_or_inf = False
                print(f"FAISS cache validated. Vector count: {index.ntotal}, Dimension: {embedding_dim}")
            else:
                print(f"FAISS cache stale ({cached_index.ntotal} vectors != {EXPECTED_CONTRACT_COUNT}). Invalidation required...")
        except Exception as e:
            print(f"Cache check error: {e}. Recomputing dense embeddings...")

    if not use_cache:
        print(f"Loading SentenceTransformer model: {model_name} on CPU...")
        model = SentenceTransformer(model_name, device='cpu')
        embedding_dim = model.get_sentence_embedding_dimension()
        print(f"Model dimension programmatically determined: {embedding_dim}")
        
        print("Encoding dense embeddings...")
        start_time = time.time()
        with torch.no_grad():
            embeddings = model.encode(texts_to_embed, batch_size=64, show_progress_bar=False, normalize_embeddings=True, convert_to_numpy=True)
        end_time = time.time()
        
        print(f"Embeddings generated in {end_time - start_time:.1f} seconds. Shape: {embeddings.shape}")
        
        has_nan_or_inf = np.isnan(embeddings).any() or np.isinf(embeddings).any()
        print(f"Embeddings NaN/Inf check: {'FAIL (Contains NaN/Inf)' if has_nan_or_inf else 'PASS (No NaN/Inf found)'}")
        
        index = faiss.IndexFlatIP(embedding_dim)
        index.add(embeddings.astype('float32'))
        
        faiss.write_index(index, dense_index_path)
        print(f"FAISS index written to: {dense_index_path}")
        
        with open(dense_map_path, 'w', encoding='utf-8') as dmf:
            json.dump(dense_map, dmf, indent=2, ensure_ascii=False)
        print(f"Dense mapping file written to: {dense_map_path}")
    
    # 7. Validation Gates Checks
    val_errors = []
    
    if len(preprocessed_chunks) != EXPECTED_CONTRACT_COUNT:
        val_errors.append(f"Preprocessed corpus chunk count '{len(preprocessed_chunks)}' != {EXPECTED_CONTRACT_COUNT}")
    if len(bm25.doc_ids) != EXPECTED_CONTRACT_COUNT:
        val_errors.append(f"BM25 index document count '{len(bm25.doc_ids)}' != {EXPECTED_CONTRACT_COUNT}")
    if len(dense_map) != EXPECTED_CONTRACT_COUNT:
        val_errors.append(f"Dense mapping count '{len(dense_map)}' != {EXPECTED_CONTRACT_COUNT}")
    if index.ntotal != EXPECTED_CONTRACT_COUNT:
        val_errors.append(f"FAISS index total vectors '{index.ntotal}' != {EXPECTED_CONTRACT_COUNT}")
        
    for idx, c in enumerate(preprocessed_chunks):
        cid = c["chunk_id"]
        if bm25.doc_ids[idx] != cid:
            val_errors.append(f"BM25 index mapping mismatch at index {idx}: expected '{cid}', got '{bm25.doc_ids[idx]}'")
        if dense_map[idx] != cid:
            val_errors.append(f"Dense index mapping mismatch at index {idx}: expected '{cid}', got '{dense_map[idx]}'")
            
    if has_nan_or_inf:
        val_errors.append("Embeddings contain NaN or Inf values")
        
    if replacement_chars_count > 0:
        val_errors.append(f"Unicode replacement characters (\\ufffd) introduced: {replacement_chars_count} found")
        
    hash_check_passed, hash_errors = verify_frozen_assets_hashes(initial_hashes)
    if not hash_check_passed:
        val_errors.extend(hash_errors)
        
    expected_keys = {
        "chunk_id", "source_id", "source_name", "file_name", "relative_path",
        "page_numbers", "publisher", "publication_year", "document_type",
        "authority_tier", "domain", "age_min", "age_max", "text", "context_prefix"
    }
    for c in preprocessed_chunks:
        c_keys = set(c.keys())
        if c_keys != expected_keys:
            val_errors.append(f"Schema mismatch for chunk '{c['chunk_id']}': missing or extra keys found: {expected_keys ^ c_keys}")
            
    # Write summary txt
    summary_lines = [
        "============================================================",
        "NUTRIKID KNOWLEDGE PREPROCESSOR SUMMARY REPORT (PHASE 3.3)",
        "============================================================",
        f"Timestamp:                           {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Input Chunks Loaded:                 {total_loaded_chunks}",
        f"Preprocessed Output Chunks:          {len(preprocessed_chunks)}",
        "",
        "============================================================",
        "CLEANING AND NORMALIZATION STATISTICS",
        "============================================================",
        f"Chunks Modified (Whitespace/Newline): {chunks_changed_count}",
        f"Total Characters Changed (Diff):     {total_char_diff} characters",
        f"Plus-Minus (\u00b1) Chunks Verified:       {plus_minus_count} chunks",
        f"Unexpected Replacement Chars Added:  {replacement_chars_count}",
        "",
        "============================================================",
        "BM25 SPARSE RETRIEVAL INDEX STATISTICS",
        "============================================================",
        f"BM25 Corpus Document Count:          {bm25.corpus_doc_count}",
        f"Vocabulary size:                     {len(bm25.doc_df)} terms",
        f"BM25 Serialized Mapping Entries:     {len(bm25.doc_ids)}",
        f"BM25 Parameter k1:                   {bm25.k1}",
        f"BM25 Parameter b:                    {bm25.b}",
        "",
        "============================================================",
        "DENSE FAISS EMBEDDING INDEX STATISTICS",
        "============================================================",
        f"Embedding Model:                     {model_name}",
        f"Programmatic Dimension:              {embedding_dim}",
        f"Dense Embedding Vector Count:        {index.ntotal}",
        f"FAISS Index Type:                    IndexFlatIP (Exact Cosine Inner Product)",
        f"Similarity Method:                   Cosine Similarity (Normalized Inner Product)",
        f"Dense Index Mapping Count:           {len(dense_map)}",
        f"NaN / Inf Embeddings Detected:       {str(has_nan_or_inf).upper()}",
        "",
        "============================================================",
        "FROZEN ASSETS INTEGRITY GATE",
        "============================================================"
    ]
    
    if hash_check_passed:
        summary_lines.append("[+] INTEGRITY STATUS: PASSED (Zero frozen assets modified)")
    else:
        summary_lines.append("[-] INTEGRITY STATUS: FAILED (Frozen assets modified)")
        
    summary_lines.extend([
        "",
        "============================================================",
        "VALIDATION VERIFICATION STATUS",
        "============================================================"
    ])
    
    if not val_errors:
        summary_lines.append("[+] VALIDATION STATUS: PASSED (0 errors found)")
    else:
        summary_lines.append(f"[-] VALIDATION STATUS: FAILED ({len(val_errors)} errors found)")
        for err in val_errors:
            summary_lines.append(f"  - ERROR: {err}")
            
    with open(summary_path, mode='w', encoding='utf-8') as sf:
        sf.write("\n".join(summary_lines))
        
    print(f"Summary report saved to: {summary_path}")
    print("\n".join(summary_lines[:23]))

if __name__ == '__main__':
    main()
