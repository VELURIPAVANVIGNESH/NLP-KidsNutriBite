# NutriKid Complete Repository Audit Report (Phase 3.4.2)

**Audit Date:** 2026-08-11  
**Auditor Role:** Senior NLP / RAG Research Engineer  
**Target Repository:** `NutriKid — FlexRAG-inspired Pediatric Nutrition RAG`  

---

## 1. Discovered Architecture

The NutriKid repository implements a modular, reproducible Knowledge Pipeline and Retrieval Engine designed specifically for the pediatric nutrition domain (target scope: children aged **5.0 to 15.0 years**). The overall dataflow is structured as follows:

```text
Source Corpus (32 PDFs in knowledge_corpus/)
      ↓
Phase 3.0: Manifest & Metadata Verification (generate_manifest.py, validate_manifest.py, verify_metadata.py)
      ↓
Phase 3.1: Document Parsing & Text Extraction (parse_documents.py → 22 Parsed JSONs)
      ↓
Phase 3.2: Domain-Aware Content Chunking (chunk_documents.py → Prose & IFCT Table Chunks → 6,429 Chunks)
      ↓
Phase 3.3: Preprocessing & Dual Indexing (preprocess_knowledge.py → BM25 Sparse Index & FAISS Dense Index)
      ↓
Phase 3.4: Hybrid RRF Retrieval & Pediatric Age Filter (retrieve.py → BM25 + FAISS + Age Filter + RRF k=60)
      ↓
Phase 3.4.1: IR Evaluation & Benchmarking (retrieval_evaluation.py → 30 Curated Ground-Truth Queries)
```

---

## 2. Implemented Components

1. **Corpus Management & Tiering:** 32 PDFs classified across 5 authority tiers (`01_PRIMARY_KNOWLEDGE` through `05_REFERENCE_ONLY`). 22 documents marked active (`retrieval_enabled=true`).
2. **Document Parsing Engine (`parse_documents.py`):** 2,403 PDF pages processed; 2,339 pages extracted with 6,021,221 characters.
3. **Dual Chunking Engine (`chunk_documents.py`):**
   - **General Prose Chunker:** Sentence-boundary aware chunking ($\le 1000$ chars, max 1400), creating 4,879 chunks.
   - **IFCT Table Chunker:** Custom row-grouping parser (6 food rows per chunk) for Indian Food Composition Tables (`IFCT_BOOK.pdf`), producing 1,550 table chunks.
   - Total retrieval-eligible candidate pool: **6,429 chunks**.
4. **Dual Retrieval Indexing Engine (`preprocess_knowledge.py`):**
   - **BM25 Sparse Index:** 6,429 documents, vocabulary size 32,939 terms ($k_1=1.5, b=0.75$).
   - **Dense FAISS Index:** 384-dimensional vectors using `BAAI/bge-small-en-v1.5` normalized for cosine similarity matching (`IndexFlatIP`).
5. **Hybrid Retrieval & Age Filtering Engine (`retrieve.py`):**
   - Implements BM25, Dense, and Hybrid Reciprocal Rank Fusion (RRF $k=60$).
   - Enforces strict pediatric scope check ($5.0 \le \text{child\_age} \le 15.0$).
6. **IR Evaluation Engine (`retrieval_evaluation.py`):**
   - Evaluates Recall@k, Precision@k, nDCG@k ($k \in \{1, 3, 5, 10\}$), MRR, and MAP over 30 annotated benchmark queries (`evaluation_queries.json`).

---

## 3. Missing Components

1. **Top-Level `tests/` Directory:** Unit test scripts were embedded inside `preprocessing/test_retriever.py` rather than structured standard `pytest`/`unittest` directory (`tests/`).
2. **Frozen Baseline Lock Files (`data/baseline/`):** No central baseline directory containing static snapshot lockfiles (`baseline_manifest.json`, `baseline_metrics.json`, `baseline_report.md`).
3. **Formal Reranking & Context Refinement Layer (Phase 3.5):** Currently absent by research design (scheduled for Phase 3.5).

---

## 4. Duplicate & Stale Components

1. **Alternative PDF Version in Corpus:** `knowledge_corpus/01_PRIMARY_KNOWLEDGE/ref-1-txt-book.pdf` was flagged as a duplicate version of `DGI_07th_May_2024_fin.pdf` (`NK-008`). It is correctly flagged inactive (`retrieval_enabled=false`).
2. **Scratch Analysis Artifacts:** Temporary diagnostic files (`scratch_pdf_analysis.json`, `scratch_verified_metadata.txt`, `test_mp.py`) exist in workspace root and `scratch/`. These are diagnostic logs and do not interfere with indexing.

---

## 5. Technical Debt & Resolved Bugs

1. **[RESOLVED] Hardcoded Developer Paths in `retrieval_evaluation.py`:**
   - *Issue:* Lines 11 and 17-18 contained hardcoded path strings `r"c:\Users\pavan\Desktop\NLP-Implementation"`, causing `ModuleNotFoundError` when executed on other environments.
   - *Fix:* Replaced with dynamic project-root resolution using `os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))`.
2. **[RESOLVED] KeyError in `quality_check.py`:**
   - *Issue:* Line 15 accessed `config["output_dir"]`, which does not exist in `config.json`.
   - *Fix:* Updated to access `config["parsed_dir"]`.
3. **[RESOLVED] HuggingFace Offline Override in `retrieve.py`:**
   - *Issue:* `HF_HUB_OFFLINE="1"` threw `LocalEntryNotFoundError` when HuggingFace cache was not pre-populated.
   - *Fix:* Removed forced environment override to permit loading from local cache or HuggingFace Hub seamlessly.

---

## 6. Reproducibility Risks

- **Floating Point RRF Sort Ties:** Handled explicitly in `retrieve.py` with deterministic tie-breaking key: `(-rrf_score, sparse_rank, dense_rank, chunk_id)`.
- **Index Integrity:** Verified by automatic MD5 checksum validation before and after retrieval execution.

---

## 7. Security & Safety Risks

- **Medical / Pediatric Safety Risk:** Presenting infant (< 5 years) or adult recommendations for children could lead to medical advice errors. The retrieval engine mitigates this via the **Pediatric Age Scope Gate**, which rejects queries for ages $<5.0$ or $>15.0$ with zero retrieved results.

---

## 8. Recommended Improvements

1. **Build Automated Regression Suite:** Establish `tests/test_regression.py` running automated assertions across document parsing, chunking, preprocessor stats, BM25 vocabulary, FAISS dimensions, age filtering, and evaluation metrics.
2. **Freeze Retrieval Baseline:** Export static lock files (`baseline_manifest.json`, `baseline_metrics.json`, `baseline_report.md`) to `data/baseline/`.
3. **Phase 3.5 Readiness Plan:** Document the input/output contracts and target metrics for candidate reranking in `data/processed/phase_3_5_readiness.md`.

---

## 9. Current Phase Status

- **Phase 3.0 (Corpus & Manifest):** **COMPLETE & VERIFIED**
- **Phase 3.1 (Document Parsing):** **COMPLETE & VERIFIED**
- **Phase 3.2 (Domain Chunking):** **COMPLETE & VERIFIED**
- **Phase 3.3 (Dual Indexing):** **COMPLETE & VERIFIED**
- **Phase 3.4 (Hybrid Retrieval & Age Filtering):** **COMPLETE & VERIFIED**
- **Phase 3.4.1 (Retrieval Evaluation & Benchmarking):** **COMPLETE & VERIFIED**
- **Phase 3.4.2 (Repository Audit & Foundation Freeze):** **IN PROGRESS (Final Freeze Stage)**
