"""
api/main.py — NutriKid Phase 2 FastAPI Backend

Endpoints:
  POST /api/ask              — Full RAG pipeline (frozen retrieval + Qwen generation)
  POST /api/ask/stream       — Streaming RAG pipeline (SSE stage updates & live tokens)
  POST /api/similarity-search/faiss  — FAISS vector similarity search
  POST /api/similarity-search/chroma — ChromaDB vector similarity search
  GET  /api/health           — Health check
"""

import os, sys, json
from contextlib import asynccontextmanager
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Validate retrieval assets once at startup
    print("[FastAPI Startup] Validating retrieval assets once...")
    config_path = os.path.join(BASE_DIR, "preprocessing", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    from preprocessing.retrieve import (
        validate_assets_once, get_corpus, get_bm25,
        get_faiss_index, get_dense_map, get_model
    )
    validate_assets_once(config)

    # 2. Warm up corpus & indexes into RAM
    print("[FastAPI Startup] Pre-warming corpus and retrieval indices into memory...")
    get_corpus(config["preprocessed_corpus_path"])
    get_bm25(config["bm25_index_path"])
    get_faiss_index(config["dense_index_path"])
    get_dense_map(config["dense_map_path"])
    get_model(config.get("embedding_model_name", "BAAI/bge-small-en-v1.5"))

    # 3. Warm up Cross-Encoder model
    print("[FastAPI Startup] Pre-warming Cross-Encoder (BAAI/bge-reranker-base)...")
    from preprocessing.rerank import get_reranker
    get_reranker("BAAI/bge-reranker-base")

    # 4. Warm up Qwen 2.5 1.5B Instruct model once and hold in memory
    print("[FastAPI Startup] Pre-warming Qwen 2.5 Instruct into RAM...")
    from generation.qwen_generator import _load_qwen
    _load_qwen()
    print("[FastAPI Startup] ALL MODELS & ASSETS READY IN MEMORY.")
    yield
    print("[FastAPI Shutdown] API terminating.")

app = FastAPI(
    title="NutriKid RAG API",
    description="Pediatric Nutrition RAG system — Phase 2. Qwen 2.5 generation + ChromaDB/FAISS vector search.",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response schemas ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., description="User question about pediatric nutrition")
    age: Optional[float] = Field(None, description="Child age in years (5-15)")

class SimilarityRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")

class HealthResponse(BaseModel):
    status: str
    message: str

# ── /api/health ──────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "message": "NutriKid RAG API v2.1 is running (pre-warmed)"}

def extract_age(req: AskRequest) -> Optional[float]:
    if req.age is not None:
        return float(req.age)
    import re
    m = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:-|–|\s+)?(?:year|yr|yo)\b', req.question, re.I)
    if m:
        return float(m.group(1))
    return None

# ── /api/ask ─────────────────────────────────────────────────────────────────

@app.post("/api/ask")
def ask(req: AskRequest):
    """
    Full RAG pipeline (non-streaming): frozen BM25+FAISS+RRF+BGE reranker → Qwen 2.5 generation.
    Returns grounded answer with citations, evidence, and perf metrics.
    """
    try:
        from generation.qwen_generator import run_qwen_pipeline
        target_age = extract_age(req)
        result = run_qwen_pipeline(
            query=req.question,
            child_age=target_age if target_age is not None else 10.0,
            candidate_k=20,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

# ── /api/ask/stream ──────────────────────────────────────────────────────────

@app.post("/api/ask/stream")
def ask_stream(req: AskRequest):
    """
    Streaming RAG pipeline:
    Yields SSE events for real-time progressive display of stage progress and generation tokens.
    """
    try:
        from generation.qwen_generator import run_qwen_pipeline_stream
        target_age = extract_age(req)

        def event_generator():
            for event_data in run_qwen_pipeline_stream(
                query=req.question,
                child_age=target_age if target_age is not None else 10.0,
                candidate_k=20,
            ):
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")

# ── /api/similarity-search/faiss ─────────────────────────────────────────────

@app.post("/api/similarity-search/faiss")
def faiss_search(req: SimilarityRequest):
    """
    FAISS similarity search using the frozen Phase 1 FAISS index.
    Returns top-k chunks ranked by inner-product similarity.
    """
    try:
        from generation.chroma_retriever import similarity_search_faiss
        results = similarity_search_faiss(req.query, k=req.k)
        return {"backend": "faiss", "query": req.query, "k": req.k, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAISS search error: {str(e)}")

# ── /api/similarity-search/chroma ────────────────────────────────────────────

@app.post("/api/similarity-search/chroma")
def chroma_search(req: SimilarityRequest):
    """
    ChromaDB similarity search (Phase 2 second vector backend).
    Returns top-k chunks ranked by cosine similarity.
    """
    try:
        from generation.chroma_retriever import similarity_search_chroma
        results = similarity_search_chroma(req.query, k=req.k)
        return {"backend": "chromadb", "query": req.query, "k": req.k, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ChromaDB search error: {str(e)}")

# ── /api/pdf/{file_name} ─────────────────────────────────────────────────────

@app.get("/api/pdf/{file_name:path}")
def get_pdf(file_name: str):
    """
    Serves authoritative pediatric nutrition PDF documents from knowledge_corpus.
    Supports case-insensitive matching and URL-decoded filenames.
    """
    from urllib.parse import unquote
    decoded_name = unquote(file_name).strip()
    base_target = os.path.basename(decoded_name).lower()
    
    corpus_base = os.path.join(BASE_DIR, "knowledge_corpus")
    for root, dirs, files in os.walk(corpus_base):
        for f in files:
            if f.lower() == base_target or f.lower() == decoded_name.lower():
                pdf_path = os.path.join(root, f)
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=f,
                    headers={
                        "Content-Disposition": f"inline; filename=\"{f}\"",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
    raise HTTPException(status_code=404, detail=f"PDF document '{file_name}' not found in knowledge corpus.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
