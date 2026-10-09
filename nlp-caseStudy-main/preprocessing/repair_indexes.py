"""
repair_indexes.py — Phase 3.3 Index Repair Script
Regenerates BM25 sparse index and FAISS dense index from existing
preprocessed_corpus.json (6,422 chunks). Run ONCE to fix corrupted indexes.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import json
import re
import math
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

CORPUS_PATH = "data/processed/preprocessed_corpus.json"
BM25_PATH   = "data/processed/bm25_index.json"
FAISS_PATH  = "data/processed/dense_index.faiss"
MAP_PATH    = "data/processed/dense_index_map.json"
MODEL_NAME  = "BAAI/bge-small-en-v1.5"
EXPECTED    = 6422

# ── 1. Load corpus ──────────────────────────────────────────────────────────
print("Loading preprocessed corpus...")
with open(CORPUS_PATH, encoding="utf-8") as f:
    corpus = json.load(f)
print(f"  Loaded {len(corpus)} chunks.")
assert len(corpus) == EXPECTED, f"Expected {EXPECTED}, got {len(corpus)}"

# ── 2. Build BM25 ───────────────────────────────────────────────────────────
print("\nBuilding BM25 sparse index...")

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

k1, b = 1.5, 0.75
N = len(corpus)
doc_ids   = []
doc_lens  = []
doc_tfs_list = []

for chunk in corpus:
    cid = chunk["chunk_id"]
    doc_ids.append(cid)
    tokens = tokenize(chunk.get("search_text", chunk.get("text", "")))
    doc_lens.append(len(tokens))
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    doc_tfs_list.append(tf)

avg_doc_len = sum(doc_lens) / N

# DF and IDF
doc_df = {}
for tf in doc_tfs_list:
    for term in tf:
        doc_df[term] = doc_df.get(term, 0) + 1

idf = {}
for term, df in doc_df.items():
    idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

# Build inverted index (store (doc_idx, tf) pairs)
inverted = {}
for didx, tf in enumerate(doc_tfs_list):
    for term, freq in tf.items():
        if term not in inverted:
            inverted[term] = []
        inverted[term].append([didx, freq])

bm25_data = {
    "doc_count": N,
    "avg_doc_len": avg_doc_len,
    "k1": k1,
    "b": b,
    "doc_ids": doc_ids,
    "doc_lens": doc_lens,
    "idf": idf,
    "inverted_index": inverted,
}

print(f"  Writing BM25 index with {N} docs, {len(idf)} vocab terms...")
with open(BM25_PATH, "w", encoding="utf-8") as f:
    json.dump(bm25_data, f, ensure_ascii=False)
print(f"  BM25 written to: {BM25_PATH}")

# ── 3. Build Dense FAISS ────────────────────────────────────────────────────
print("\nBuilding dense FAISS index...")
print(f"  Loading model: {MODEL_NAME}")
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import torch

model = SentenceTransformer(MODEL_NAME, device='cpu')
embedding_dim = model.get_sentence_embedding_dimension()
print(f"  Embedding dimension: {embedding_dim}")

texts = [chunk.get("search_text", chunk.get("text", "")) for chunk in corpus]

print(f"  Encoding {len(texts)} texts (batch_size=64)...")
t0 = time.time()
with torch.no_grad():
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
elapsed = time.time() - t0
print(f"  Encoded {len(embeddings)} vectors in {elapsed:.1f}s. Shape: {embeddings.shape}")

has_bad = bool(np.isnan(embeddings).any() or np.isinf(embeddings).any())
print(f"  NaN/Inf check: {'FAIL' if has_bad else 'PASS'}")

index = faiss.IndexFlatIP(embedding_dim)
index.add(embeddings.astype("float32"))
print(f"  FAISS index ntotal: {index.ntotal}")

faiss.write_index(index, FAISS_PATH)
print(f"  FAISS index written to: {FAISS_PATH}")

dense_map = {str(i): doc_ids[i] for i in range(N)}
with open(MAP_PATH, "w", encoding="utf-8") as f:
    json.dump(dense_map, f, ensure_ascii=False, indent=2)
print(f"  Dense map written to: {MAP_PATH}")

# ── 4. Final verification ───────────────────────────────────────────────────
print("\n=== VERIFICATION ===")
with open(BM25_PATH, encoding="utf-8") as f:
    bm25_check = json.load(f)
print(f"  BM25 doc_count: {bm25_check['doc_count']}")

idx2 = faiss.read_index(FAISS_PATH)
print(f"  FAISS ntotal: {idx2.ntotal}, dim: {idx2.d}")

with open(MAP_PATH, encoding="utf-8") as f:
    map_check = json.load(f)
print(f"  Dense map count: {len(map_check)}")

assert bm25_check["doc_count"] == EXPECTED
assert idx2.ntotal == EXPECTED
assert len(map_check) == EXPECTED
print(f"\n[+] ALL OK — {EXPECTED} chunks indexed in BM25 + FAISS.")
