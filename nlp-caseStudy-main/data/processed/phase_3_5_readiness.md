# Phase 3.5 Readiness & Research Specification — Reranking & Context Refinement

**Document Version:** `v1.0.0`  
**Target Phase:** Phase 3.5 (Reranking + Context Refinement)  
**Status:** Architecture Specification Ready (Phase 3.4.2 Baseline Frozen)  

---

## 1. Current Baseline Performance Summary

The frozen Phase 3.4.2 baseline provides the starting point for Phase 3.5 evaluation:
- **Hybrid RRF Baseline:** MRR = **0.0400**, MAP = **0.0367**, nDCG@5 = **0.0435**, Recall@5 = **0.0500**.
- **Key Observation:** The initial retrieval candidate pool ($k_{cand}=100$) captures broad relevant contexts, but first-stage lexical/dense rankings suffer from score dilution when matching complex multi-sentence clinical queries or tabular food codes.

---

## 2. Candidate Reranker Design

Phase 3.5 will introduce a second-stage **Cross-Encoder Reranker** layer downstream of Hybrid RRF candidate generation:

```text
User Query + Age Context
           ↓
Hybrid RRF First-Stage Search (Retrieve Top-K Candidates, e.g. K_cand = 50)
           ↓
Cross-Encoder Reranking (Joint Query-Document Self-Attention Scoring)
           ↓
Context Refinement & Deduplication (Redundancy Filter + Provenance Header Insertion)
           ↓
Final Refined Top-K Context Window (K_final = 5)
```

---

## 3. Candidate Reranker Model Selection

Selected candidate reranker models for experimental comparison:
1. **Primary Candidate:** `BAAI/bge-reranker-small` (Lightweight, aligned vector space with BGE-small embeddings).
2. **Secondary Candidate:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (Established baseline cross-encoder for passagereranking).

---

## 4. Input / Output Contract for Reranker

- **Input:**
  - `query_text`: String
  - `candidate_chunks`: List of chunk objects from Phase 3.4 Hybrid RRF (containing `chunk_id`, `text`, `context_prefix`, `age_min`, `age_max`)
  - `top_n`: Integer (Number of reranked items to return, default = 5)
- **Output:**
  - `reranked_chunks`: List of chunk objects ordered by cross-encoder relevance score descending, containing original provenance metadata and new `rerank_score`.

---

## 5. Candidate Pool Top-K Expansion Contract

- **Candidate Pool Size ($k_{cand}$):** Pass top $k_{cand} = 50$ (or 100) candidates from Hybrid RRF to the reranker.
- **Final Return Size ($k_{final}$):** Return top $k_{final} = 5$ reranked chunks for downstream generation.

---

## 6. Evaluation Methodology for Reranking

Reranking performance will be evaluated using `retrieval_evaluation.py` on the exact 30-query benchmark dataset (`evaluation_queries.json`):
- Compare **Hybrid RRF Baseline** vs. **Hybrid RRF + Cross-Encoder Reranking**.
- Primary evaluation metrics: **nDCG@1**, **nDCG@3**, **nDCG@5**, **MRR**, and **MAP**.

---

## 7. Context Refinement & Deduplication Strategy

To maximize information density in the final context window:
1. **Near-Duplicate Sentence Filter:** Deduplicate highly overlapping sentences across chunks from the same source document.
2. **Provenance Header Normalization:** Clean context prefixes (Publisher, Source Title, Page Numbers) so LLM context remains clean and structured.
3. **Table Formatting Preservation:** Retain IFCT food table headers and numeric column formatting without truncating cell values.

---

## 8. Context Quality Measurement Metrics

In addition to standard IR metrics, context refinement will be evaluated on:
- **Redundancy Ratio:** Percentage of duplicate n-grams across top-5 context chunks (Target: $< 15\%$).
- **Context Density:** Token count ratio of informative text vs formatting overhead.

---

## 9. Frozen Components Guarantee

To maintain strict scientific comparability, the following layers MUST remain frozen during Phase 3.5:
- Source PDF corpus (22 core PDFs)
- Corpus manifest (`corpus_manifest.csv`)
- Parsed JSONs and 6,429 preprocessed chunks
- BM25 index & FAISS dense vector embeddings
- Phase 3.4.1 ground-truth evaluation dataset (`evaluation_queries.json`)

---

## 10. Quantitative Success Criteria for Phase 3.5

Phase 3.5 will be deemed successful if the Reranking + Refinement module achieves:
1. **MRR Improvement:** Relative improvement of $\ge +25\%$ over Hybrid RRF baseline ($\text{MRR} \ge 0.0500$).
2. **nDCG@5 Improvement:** Relative improvement of $\ge +20\%$ over Hybrid RRF baseline ($\text{nDCG}@5 \ge 0.0522$).
3. **Determinism:** 100% deterministic reproducibility across multiple runs.
