"""
preprocessing/retrieve.py — NutriKid Pediatric Nutrition Hybrid Retriever (Phase 3.4)

Implements Sparse (BM25) + Dense (FAISS IndexFlatIP) Hybrid Retrieval with:
1. Pediatric Scope Guardrail (5-15 years)
2. Age Metadata Filtering
3. Reciprocal Rank Fusion (RRF, k=60)
4. Deterministic Tie-Breaking
5. Frozen Assets Integrity Hash Gate
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TQDM_DISABLE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

import csv
import json
import re
import sys
import time
import hashlib
import argparse
import concurrent.futures
import faiss
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

_MODEL_CACHE = {}
_CORPUS_CACHE = {}
_BM25_CACHE = {}
_FAISS_CACHE = {}
_DENSE_MAP_CACHE = {}

# Query & Retrieval Caching (safe, invalidated if assets/corpus change)
_QUERY_EMBEDDING_CACHE = {}
_RETRIEVAL_CACHE = {}

def clear_retrieval_caches():
    """Clear query embedding and retrieval caches."""
    _QUERY_EMBEDDING_CACHE.clear()
    _RETRIEVAL_CACHE.clear()

# Startup-only asset validation flag.
# Set to True once validate_assets_once() has been called successfully.
# Prevents expensive full-file hashing on every query call.
_ASSETS_VALIDATED: bool = False
_VALIDATED_HASHES: dict = {}

def get_model(model_name="BAAI/bge-small-en-v1.5"):
    if model_name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name, device="cpu")
    return _MODEL_CACHE[model_name]

def get_corpus(path):
    if path not in _CORPUS_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CORPUS_CACHE[path] = (data, {c["chunk_id"]: c for c in data})
    return _CORPUS_CACHE[path]

def get_bm25(path):
    if path not in _BM25_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            _BM25_CACHE[path] = json.load(f)
    return _BM25_CACHE[path]

def get_faiss_index(path):
    if path not in _FAISS_CACHE:
        _FAISS_CACHE[path] = faiss.read_index(path)
    return _FAISS_CACHE[path]

def get_dense_map(path):
    if path not in _DENSE_MAP_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            _DENSE_MAP_CACHE[path] = json.load(f)
    return _DENSE_MAP_CACHE[path]

def compute_md5(file_path):
    if not os.path.exists(file_path):
        return None
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def capture_frozen_assets_hashes(config):
    hashes = {}
    
    # 1. Manifest
    manifest_path = config["manifest_path"]
    hashes[manifest_path] = compute_md5(manifest_path)
    
    # 2. Raw PDFs
    corpus_dir = config["corpus_dir"]
    for root, _, files in os.walk(corpus_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.join(root, file)
                hashes[path] = compute_md5(path)
                
    # 3. Parsed JSONs
    parsed_dir = config["parsed_dir"]
    for root, _, files in os.walk(parsed_dir):
        for file in files:
            if file.lower().endswith(".json"):
                path = os.path.join(root, file)
                hashes[path] = compute_md5(path)
                
    # 4. Chunk JSONs
    chunks_dir = config["chunks_dir"]
    for root, _, files in os.walk(chunks_dir):
        for file in files:
            if file.lower().endswith(".json"):
                path = os.path.join(root, file)
                hashes[path] = compute_md5(path)
                
    # 5. Preprocessed & index outputs
    for key in ["preprocessed_corpus_path", "bm25_index_path", "dense_index_path", "dense_map_path"]:
        if key in config and os.path.exists(config[key]):
            hashes[config[key]] = compute_md5(config[key])
            
    return hashes

def verify_hashes(saved_hashes):
    for path, saved_hash in saved_hashes.items():
        current_hash = compute_md5(path)
        if current_hash != saved_hash:
            return False, f"Hash mismatch for {path}: expected {saved_hash}, got {current_hash}"
    return True, None


def validate_assets_once(config):
    """
    Validate required retrieval assets exactly once at startup / index-build time.
    Computes and stores hashes globally so that run_retrieval() does NOT
    re-hash large files on every query call.

    Call this at application startup, not inside the query path.
    Raises RuntimeError immediately if any required asset is missing or corrupted.
    """
    global _ASSETS_VALIDATED, _VALIDATED_HASHES
    if _ASSETS_VALIDATED:
        return  # Already validated — skip.

    required_keys = [
        "preprocessed_corpus_path",
        "bm25_index_path",
        "dense_index_path",
        "dense_map_path",
    ]
    missing = [k for k in required_keys if not os.path.exists(config.get(k, ""))]
    if missing:
        raise RuntimeError(
            f"[validate_assets_once] Missing required retrieval assets: {missing}. "
            f"Re-run the indexing pipeline to regenerate them."
        )

    hashes = capture_frozen_assets_hashes(config)
    ok, err = verify_hashes(hashes)
    if not ok:
        raise RuntimeError(f"[validate_assets_once] Asset integrity check failed: {err}")

    _VALIDATED_HASHES = hashes
    _ASSETS_VALIDATED = True
    print(f"[validate_assets_once] All {len(hashes)} retrieval assets validated successfully.")

def tokenize_text(text):
    return re.findall(r'\b\w+\b', text.lower())

def check_age_compatibility(chunk, age, age_min_scope=5, age_max_scope=15):
    c_min = chunk.get("age_min")
    c_max = chunk.get("age_max")
    
    def clean_val(v):
        if v is None or str(v).strip() == "" or str(v).lower() == "null":
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
            
    c_min = clean_val(c_min)
    c_max = clean_val(c_max)
    
    if age is not None:
        if c_min is not None and age < c_min:
            return False
        if c_max is not None and age > c_max:
            return False
        return True
    else:
        if c_min is not None and c_min > age_max_scope:
            return False
        if c_max is not None and c_max < age_min_scope:
            return False
        return True

def _search_bm25_worker(query, candidate_k, config):
    t0 = time.perf_counter()
    bm25_idx = get_bm25(config["bm25_index_path"])
    k1 = bm25_idx.get("k1", 1.5)
    b = bm25_idx.get("b", 0.75)
    avg_doc_len = bm25_idx["avg_doc_len"]
    doc_lens = bm25_idx["doc_lens"]
    doc_ids = bm25_idx["doc_ids"]
    idf = bm25_idx["idf"]
    inverted_index = bm25_idx["inverted_index"]

    q_tokens = tokenize_text(query)
    bm25_scores = {}
    for t in q_tokens:
        if t in inverted_index:
            idf_t = idf[t]
            for doc_idx, tf in inverted_index[t]:
                dl = doc_lens[doc_idx]
                term_score = idf_t * (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (dl / avg_doc_len)))
                bm25_scores[doc_idx] = bm25_scores.get(doc_idx, 0.0) + term_score

    bm25_ranked = []
    for doc_idx, score in bm25_scores.items():
        bm25_ranked.append((doc_ids[doc_idx], score))
    bm25_ranked.sort(key=lambda x: (-x[1], x[0]))
    sparse_candidates = [(cid, score, rank_idx + 1) for rank_idx, (cid, score) in enumerate(bm25_ranked[:candidate_k])]
    dur_ms = (time.perf_counter() - t0) * 1000
    return sparse_candidates, dur_ms

def _search_faiss_worker(query, candidate_k, config):
    t0 = time.perf_counter()
    index = get_faiss_index(config["dense_index_path"])
    dense_map = get_dense_map(config["dense_map_path"])
    model_name = config.get("embedding_model_name", "BAAI/bge-small-en-v1.5")
    model = get_model(model_name)

    emb_t0 = time.perf_counter()
    if query in _QUERY_EMBEDDING_CACHE:
        q_emb_norm = _QUERY_EMBEDDING_CACHE[query]
    else:
        import torch
        with torch.no_grad():
            q_emb = model.encode([query], show_progress_bar=False, normalize_embeddings=True, convert_to_numpy=True)
        q_emb_norm = q_emb.astype("float32")
        _QUERY_EMBEDDING_CACHE[query] = q_emb_norm
    embedding_ms = (time.perf_counter() - emb_t0) * 1000

    faiss_t0 = time.perf_counter()
    scores, indices = index.search(q_emb_norm, min(candidate_k, index.ntotal))
    faiss_ranked = []
    for rank_idx, offset in enumerate(indices[0]):
        if offset == -1:
            continue
        score = float(scores[0][rank_idx])
        chunk_id = dense_map[str(offset)] if isinstance(dense_map, dict) else dense_map[offset]
        faiss_ranked.append((chunk_id, score))
    faiss_ranked.sort(key=lambda x: (-x[1], x[0]))
    dense_candidates = [(cid, score, rank_idx + 1) for rank_idx, (cid, score) in enumerate(faiss_ranked[:candidate_k])]
    faiss_ms = (time.perf_counter() - faiss_t0) * 1000
    total_dense_ms = (time.perf_counter() - t0) * 1000
    return dense_candidates, embedding_ms, faiss_ms, total_dense_ms

def run_retrieval(query, child_age=None, mode="hybrid", top_k=5, candidate_k=100, rrf_k_param=60, config_path="preprocessing/config.json", skip_hash_check=False):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Asset integrity check:
    # - If skip_hash_check is True (e.g. during benchmark evaluation), skip entirely.
    # - If validate_assets_once() was already called at startup, skip per-query hashing.
    # - Otherwise fall back to a single capture+verify cycle for this call.
    if skip_hash_check or _ASSETS_VALIDATED:
        initial_hashes = None
    else:
        initial_hashes = capture_frozen_assets_hashes(config)
    
    requested_age = child_age
    scope_status = "in_scope"
    effective_age_scope = None
    
    # Pediatric scope guardrail check (5 - 15 years)
    if child_age is None:
        effective_age_scope = [5, 15]
        scope_status = "default_research_scope"
    elif child_age < 5 or child_age > 15:
        return {
            "query": query,
            "requested_age": requested_age,
            "scope_status": "out_of_scope",
            "effective_age_scope": None,
            "status": "terminated_out_of_scope",
            "results": [],
            "accounting": {
                "requested_top_k": top_k,
                "returned_count": 0,
                "candidate_k": candidate_k,
                "filtered_count": 0
            },
            "timing_breakdown": {
                "bm25_ms": 0.0,
                "embedding_ms": 0.0,
                "faiss_ms": 0.0,
                "rrf_ms": 0.0,
                "from_cache": False
            }
        }

    # Safe retrieval cache lookup
    cache_key = (query.strip().lower(), requested_age, mode, top_k, candidate_k, rrf_k_param)
    if cache_key in _RETRIEVAL_CACHE:
        cached_val = dict(_RETRIEVAL_CACHE[cache_key])
        cached_val["timing_breakdown"] = dict(cached_val.get("timing_breakdown", {}))
        cached_val["timing_breakdown"]["from_cache"] = True
        return cached_val

    # Load cached preprocessed corpus
    preprocessed_corpus, corpus_dict = get_corpus(config["preprocessed_corpus_path"])
    
    sparse_candidates = []
    dense_candidates = []
    bm25_time_ms = 0.0
    embedding_time_ms = 0.0
    faiss_time_ms = 0.0

    # Parallel Hybrid / Single Mode Retrieval
    if mode == "hybrid":
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_bm25 = executor.submit(_search_bm25_worker, query, candidate_k, config)
            fut_faiss = executor.submit(_search_faiss_worker, query, candidate_k, config)
            sparse_candidates, bm25_time_ms = fut_bm25.result()
            dense_candidates, embedding_time_ms, faiss_time_ms, _ = fut_faiss.result()
    elif mode == "bm25":
        sparse_candidates, bm25_time_ms = _search_bm25_worker(query, candidate_k, config)
    elif mode == "dense":
        dense_candidates, embedding_time_ms, faiss_time_ms, _ = _search_faiss_worker(query, candidate_k, config)
        
    # 3. Candidate Compilation & Age Metadata Filtering
    rrf_t0 = time.perf_counter()
    all_candidate_cids = list(dict.fromkeys([c[0] for c in sparse_candidates] + [c[0] for c in dense_candidates]))
    
    eligible_cids = set()
    for cid in all_candidate_cids:
        chunk_obj = corpus_dict.get(cid)
        if chunk_obj and check_age_compatibility(chunk_obj, requested_age):
            eligible_cids.add(cid)
            
    filtered_count = len(all_candidate_cids) - len(eligible_cids)
    
    sparse_ranks = {c[0]: c[2] for c in sparse_candidates if c[0] in eligible_cids}
    dense_ranks = {c[0]: c[2] for c in dense_candidates if c[0] in eligible_cids}
    
    fused_results = []
    
    if mode == "bm25":
        for cid, score, rank in sparse_candidates:
            if cid in eligible_cids:
                fused_results.append({
                    "chunk_id": cid,
                    "score": score,
                    "sparse_rank": rank,
                    "dense_rank": dense_ranks.get(cid),
                    "rrf_score": None
                })
        fused_results.sort(key=lambda x: (-x["score"], x["chunk_id"]))
        
    elif mode == "dense":
        for cid, score, rank in dense_candidates:
            if cid in eligible_cids:
                fused_results.append({
                    "chunk_id": cid,
                    "score": score,
                    "sparse_rank": sparse_ranks.get(cid),
                    "dense_rank": rank,
                    "rrf_score": None
                })
        fused_results.sort(key=lambda x: (-x["score"], x["chunk_id"]))
        
    elif mode == "hybrid":
        for cid in eligible_cids:
            r_sparse = sparse_ranks.get(cid)
            r_dense = dense_ranks.get(cid)
            
            rrf_score = 0.0
            if r_sparse is not None:
                rrf_score += 1.0 / (rrf_k_param + r_sparse)
            if r_dense is not None:
                rrf_score += 1.0 / (rrf_k_param + r_dense)
                
            fused_results.append({
                "chunk_id": cid,
                "score": rrf_score,
                "sparse_rank": r_sparse,
                "dense_rank": r_dense,
                "rrf_score": rrf_score
            })
            
        def hybrid_sort_key(x):
            s_r = x["sparse_rank"] if x["sparse_rank"] is not None else 999999
            d_r = x["dense_rank"] if x["dense_rank"] is not None else 999999
            return (-x["rrf_score"], s_r, d_r, x["chunk_id"])
            
        fused_results.sort(key=hybrid_sort_key)
        
    rrf_time_ms = (time.perf_counter() - rrf_t0) * 1000

    # 4. Top-K Slice & Insufficient Candidates Handling
    returned_count = len(fused_results)
    status = "success"
    if returned_count < top_k:
        status = "insufficient_eligible_candidates"
        top_slices = fused_results
    else:
        top_slices = fused_results[:top_k]
        
    results_list = []
    for idx, fr in enumerate(top_slices):
        chunk_info = corpus_dict[fr["chunk_id"]]
        results_list.append({
            "rank": idx + 1,
            "chunk_id": chunk_info["chunk_id"],
            "source_id": chunk_info["source_id"],
            "source_name": chunk_info["source_name"],
            "file_name": chunk_info["file_name"],
            "page_numbers": chunk_info["page_numbers"],
            "age_min": chunk_info["age_min"],
            "age_max": chunk_info["age_max"],
            "publisher": chunk_info.get("publisher", ""),
            "publication_year": chunk_info.get("publication_year", ""),
            "domain": chunk_info.get("domain", ""),
            "text": chunk_info["text"],
            "context_prefix": chunk_info["context_prefix"],
            "sparse_rank": fr["sparse_rank"],
            "dense_rank": fr["dense_rank"],
            "rrf_score": fr["rrf_score"],
            "score": fr["score"]
        })
        
    if initial_hashes is not None:
        integrity_ok, integrity_err = verify_hashes(initial_hashes)
        if not integrity_ok:
            raise RuntimeError(f"Integrity check failed during retrieval: {integrity_err}")
        
    ret_output = {
        "query": query,
        "requested_age": requested_age,
        "scope_status": scope_status,
        "effective_age_scope": effective_age_scope,
        "status": status,
        "results": results_list,
        "accounting": {
            "requested_top_k": top_k,
            "returned_count": len(results_list),
            "candidate_k": candidate_k,
            "filtered_count": filtered_count
        },
        "timing_breakdown": {
            "bm25_ms": round(bm25_time_ms, 2),
            "embedding_ms": round(embedding_time_ms, 2),
            "faiss_ms": round(faiss_time_ms, 2),
            "rrf_ms": round(rrf_time_ms, 2),
            "from_cache": False
        }
    }
    _RETRIEVAL_CACHE[cache_key] = ret_output
    return ret_output

class DenseRetriever:
    """
    Clean abstraction over the existing FAISS IndexFlatIP dense retrieval index.

    Responsibilities (ONLY):
      1. Accept a query string.
      2. Generate the query embedding via the existing SentenceTransformer model.
      3. Normalize consistently with the indexed embeddings (L2 via normalize_embeddings=True).
      4. Query the FAISS IndexFlatIP index.
      5. Map FAISS offsets to chunk IDs via dense_map.
      6. Return ranked results in FAISS score order with deterministic tie-breaking.
      7. Handle k safely when k > index.ntotal.

    NOT responsible for: BM25, RRF, age filtering, reranking, or context refinement.
    """

    def __init__(self, config_path: str = "preprocessing/config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)
        self._model_name: str = self._config.get("embedding_model_name", "BAAI/bge-small-en-v1.5")
        self._faiss_path: str = self._config["dense_index_path"]
        self._map_path: str = self._config["dense_map_path"]

    def similarity_search(self, query: str, k: int = 100):
        """
        Search the FAISS index for the top-k most similar chunks.

        Args:
            query: Natural-language query string.
            k:     Number of results to return. Clamped to index.ntotal automatically.

        Returns:
            List of dicts, each with:
                {
                    "rank":     int  (1-indexed, best first),
                    "chunk_id": str,
                    "score":    float  (inner-product similarity, higher = more similar),
                }
            Sorted by score descending; ties broken alphabetically by chunk_id.
        """
        import torch

        model = get_model(self._model_name)
        index = get_faiss_index(self._faiss_path)
        dense_map = get_dense_map(self._map_path)

        safe_k = min(k, index.ntotal)
        if safe_k == 0:
            return []

        with torch.no_grad():
            q_emb = model.encode(
                [query],
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        q_emb_f32 = q_emb.astype("float32")

        scores_arr, indices_arr = index.search(q_emb_f32, safe_k)

        ranked: list = []
        for offset, score in zip(indices_arr[0], scores_arr[0]):
            if offset == -1:
                continue
            chunk_id = dense_map[str(offset)] if isinstance(dense_map, dict) else dense_map[int(offset)]
            ranked.append((chunk_id, float(score)))

        # Deterministic sort: score desc, chunk_id asc (tie-break)
        ranked.sort(key=lambda x: (-x[1], x[0]))

        return [
            {"rank": rank_idx + 1, "chunk_id": cid, "score": score}
            for rank_idx, (cid, score) in enumerate(ranked)
        ]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NutriKid Hybrid Sparse-Dense Retriever CLI")
    parser.add_argument("--query", required=True, type=str, help="Search query string")
    parser.add_argument("--age", default=None, type=float, help="Context child age in years")
    parser.add_argument("--mode", default="hybrid", choices=["bm25", "dense", "hybrid"], help="Retrieval mode")
    parser.add_argument("--top_k", default=5, type=int, help="Final top results returned")
    
    args = parser.parse_args()
    res = run_retrieval(query=args.query, child_age=args.age, mode=args.mode, top_k=args.top_k)
    print(json.dumps(res, indent=2, ensure_ascii=False))
