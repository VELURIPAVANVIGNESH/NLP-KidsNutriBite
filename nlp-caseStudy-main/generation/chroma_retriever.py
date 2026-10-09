"""
generation/chroma_retriever.py — NutriKid Phase 2 ChromaDB Vector Search

Implements a SECOND vector search system (independent of FAISS) using ChromaDB.
Same 6,422 canonical chunks, same BAAI/bge-small-en-v1.5 embeddings (384-dim).

This is NOT part of the frozen production retrieval path.
The production path remains: BM25 + FAISS → RRF → BGE reranker → Top-5.

ChromaDB is used for:
  - API demonstration of vector search
  - Comparison against FAISS similarity search
  - Research/evaluation component
"""

import os, sys, json
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "data", "processed", "chroma_db")
COLLECTION_NAME    = "nutrikid_corpus"
EMBEDDING_MODEL    = "BAAI/bge-small-en-v1.5"
CORPUS_PATH        = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")

_CHROMA_CLIENT     = None
_CHROMA_COLLECTION = None
_EMBED_MODEL       = None


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    return _EMBED_MODEL


def _get_collection():
    global _CHROMA_CLIENT, _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is None:
        import chromadb
        _CHROMA_CLIENT = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        try:
            _CHROMA_COLLECTION = _CHROMA_CLIENT.get_collection(COLLECTION_NAME)
        except Exception:
            _CHROMA_COLLECTION = None
    return _CHROMA_COLLECTION


def build_chroma_collection(force_rebuild=False):
    """
    Build (or load) the ChromaDB collection from the canonical 6,422-chunk corpus.
    Uses BAAI/bge-small-en-v1.5 embeddings (same as FAISS).
    Persists to disk for reuse.
    """
    import chromadb
    import numpy as np

    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Check if collection exists and is populated
    try:
        col = client.get_collection(COLLECTION_NAME)
        existing_count = col.count()
        if existing_count >= 6422 and not force_rebuild:
            print(f"[ChromaRetriever] Collection already has {existing_count} chunks. Skipping rebuild.")
            global _CHROMA_CLIENT, _CHROMA_COLLECTION
            _CHROMA_CLIENT = client
            _CHROMA_COLLECTION = col
            return col
        elif force_rebuild:
            client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection doesn't exist yet

    print(f"[ChromaRetriever] Building collection from {CORPUS_PATH} ...")
    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = json.load(f)
    print(f"[ChromaRetriever] Loaded {len(corpus)} chunks.")

    embed_model = _get_embed_model()
    col = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # cosine distance (analogous to inner-product after normalisation)
    )

    BATCH = 256
    for i in range(0, len(corpus), BATCH):
        batch = corpus[i:i+BATCH]
        texts = [c.get("text", "") for c in batch]
        ids   = [c["chunk_id"] for c in batch]
        metas = []
        for c in batch:
            m = {
                "source_id":  str(c.get("source_id",  "")),
                "source_name":str(c.get("source_name","") or ""),
                "file_name":  str(c.get("file_name",  "") or ""),
                "page_numbers": json.dumps(c.get("page_numbers", [])),
                "age_min":    float(c.get("age_min", 5.0)  if c.get("age_min")  is not None else 5.0),
                "age_max":    float(c.get("age_max", 15.0) if c.get("age_max")  is not None else 15.0),
            }
            metas.append(m)
        embeds = embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        col.add(documents=texts, embeddings=embeds, ids=ids, metadatas=metas)
        print(f"[ChromaRetriever]  Indexed {min(i+BATCH, len(corpus))}/{len(corpus)}")

    print(f"[ChromaRetriever] Collection built: {col.count()} chunks.")
    _CHROMA_CLIENT = client
    _CHROMA_COLLECTION = col
    return col


def similarity_search_chroma(query: str, k: int = 5) -> list:
    """
    ChromaDB similarity search API.

    Encodes query with BAAI/bge-small-en-v1.5, queries ChromaDB collection,
    returns top-k ranked results.

    Returns:
        list of dicts: [{chunk_id, score, text, metadata}]

    Note: ChromaDB returns cosine DISTANCE (lower = more similar).
          We report 1 - distance as similarity score for clarity.
          Do NOT compare raw magnitudes directly with FAISS inner-product scores.
    """
    col = _get_collection()
    if col is None:
        col = build_chroma_collection()

    embed_model = _get_embed_model()
    q_emb = embed_model.encode([query], normalize_embeddings=True, show_progress_bar=False).tolist()

    results = col.query(query_embeddings=q_emb, n_results=k, include=["documents","distances","metadatas"])

    output = []
    ids       = results["ids"][0]
    distances = results["distances"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for cid, dist, doc, meta in zip(ids, distances, documents, metadatas):
        similarity = max(0.0, 1.0 - dist)  # cosine sim from cosine dist
        output.append({
            "chunk_id": cid,
            "score": round(similarity, 6),
            "text": doc,
            "metadata": {
                "source":      meta.get("source_id", ""),
                "source_name": meta.get("source_name", ""),
                "page":        meta.get("page_numbers", "[]"),
                "title":       meta.get("file_name", ""),
            }
        })
    return output


def similarity_search_faiss(query: str, k: int = 5) -> list:
    """
    FAISS similarity search API (wraps existing frozen FAISS index).
    Uses the same BAAI/bge-small-en-v1.5 embeddings.
    Does NOT modify the FAISS index.

    Returns:
        list of dicts: [{chunk_id, score, text, metadata}]
    """
    import faiss, json, numpy as np

    # Load frozen FAISS assets
    faiss_path  = os.path.join(BASE_DIR, "data", "processed", "dense_index.faiss")
    map_path    = os.path.join(BASE_DIR, "data", "processed", "dense_index_map.json")
    corpus_path = CORPUS_PATH

    index = faiss.read_index(faiss_path)
    with open(map_path, encoding="utf-8") as f:
        id_map = json.load(f)
    with open(corpus_path, encoding="utf-8") as f:
        corpus_list = json.load(f)
    corpus_dict = {c["chunk_id"]: c for c in corpus_list}

    embed_model = _get_embed_model()
    q_emb = embed_model.encode([query], normalize_embeddings=True, show_progress_bar=False).astype(np.float32)

    scores, indices = index.search(q_emb, k)

    output = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        cid = id_map[int(idx)] if isinstance(id_map, list) else id_map[str(idx)]
        chunk = corpus_dict.get(cid, {})
        output.append({
            "chunk_id": cid,
            "score": float(score),
            "text": chunk.get("text", ""),
            "metadata": {
                "source":      chunk.get("source_id", ""),
                "source_name": chunk.get("source_name", ""),
                "page":        json.dumps(chunk.get("page_numbers", [])),
                "title":       chunk.get("file_name", ""),
            }
        })
    return output


if __name__ == "__main__":
    build_chroma_collection()
    results = similarity_search_chroma("protein requirements for children", k=3)
    for r in results:
        print(r["chunk_id"], r["score"], r["text"][:80])
