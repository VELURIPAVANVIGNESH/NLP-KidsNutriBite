# Phase 3.3 — Knowledge Preprocessing & Dual Indexing Documentation

## 1. Overview & Core Objectives
Phase 3.3 of the NutriKid Pediatric Nutrition RAG pipeline establishes the unified preprocessed knowledge representation and constructs dual sparse-dense search indexes over the frozen Phase 3.2 retrieval-eligible chunks.

The primary deliverables of Phase 3.3 are:
1. **Unified Preprocessed Knowledge Corpus**: A standardized JSON repository of cleaned and structured chunks.
2. **Deterministic BM25 Sparse Index**: An inverted BM25 index ($k_1=1.5, b=0.75$) tokenized via regex word boundaries.
3. **Dense FAISS Vector Index**: Normalized 384-dimensional inner product embeddings generated via `BAAI/bge-small-en-v1.5` for exact Cosine similarity.
4. **Frozen Assets Integrity Verification**: MD5 hash gates confirming zero changes to prior frozen phase outputs (PDFs, manifest, parsed JSONs, chunk JSONs).

---

## 2. Frozen Contract Count Baseline
- **Active Documents**: 22 / 22
- **Disabled Documents**: 10 excluded
- **Input Chunks**: 6,422 retrieval-eligible chunks
- **Output Chunks**: 6,422 preprocessed chunks
- **Unique Chunk IDs**: 6,422 (`NK-001-C00001` .. `NK-024-C00424`)
- **Ordering Guarantee**: Strict deterministic sorting by `source_id` $\rightarrow$ `chunk_id`.

---

## 3. Text Preprocessing & Cleaning Architecture
- **Carriage Return Strip**: All `\r` carriage return characters removed.
- **Space Normalization**: Multiple horizontal whitespace characters (`[ \t]+`) normalized to single space `' '`.
- **Newline Normalization**: 3 or more consecutive newlines (`\n\n+`) collapsed to `\n\n`.
- **Preserved Structure**: Single newlines preserved to retain IFCT nutritional table structure.
- **Unicode Integrity**: Zero U+FFFD replacement characters introduced. Full preservation of mathematical $\pm$ (`U+00B1`) across 886 chunks.

---

## 4. Sparse BM25 Index Specifications
- **Corpus Document Count**: 6,422 documents
- **Vocabulary Size**: 33,038 unique terms
- **Tokenization Engine**: `re.findall(r'\b\w+\b', text.lower())`
- **BM25 $k_1$ Parameter**: `1.5`
- **BM25 $b$ Parameter**: `0.75`
- **Average Document Length**: 155.6 words
- **Serialized Output**: `data/processed/bm25_index.json`

---

## 5. Dense FAISS Embedding Index Specifications
- **Embedding Model**: `BAAI/bge-small-en-v1.5`
- **Programmatic Dimension**: `384`
- **Normalization**: $L_2$ normalized vector embeddings ($|v|_2 = 1.0$)
- **FAISS Index Type**: `faiss.IndexFlatIP` (Exact Cosine Inner Product)
- **Vector Count**: 6,422 vectors
- **NaN / Inf Check**: `PASS` (0 NaN/Inf values detected)
- **Serialized Output**: `data/processed/dense_index.faiss`
- **Dense Mapping Output**: `data/processed/dense_index_map.json`

---

## 6. Dual Index Mapping & Alignment
- **1-to-1 Correspondence**: Position $i$ in `dense_index.faiss` maps directly to key `str(i)` in `dense_index_map.json`, item $i$ in `bm25_index.json["doc_ids"]`, and index $i$ in `preprocessed_corpus.json`.
- **Deterministic Identifier Linking**: All retrieval engines resolve to the exact chunk ID contract (e.g. `NK-001-C00001`).

---

## 7. Frozen Assets Integrity Gate
MD5 hash verification was conducted across all prior pipeline assets before and after execution:
- **Raw PDFs (`knowledge_corpus/`)**: 0 modified
- **Manifest (`corpus_manifest.csv`)**: 0 modified
- **Parsed JSONs (`data/processed/parsed/`)**: 0 modified (2,403 pages)
- **Chunk JSONs (`data/processed/chunks/`)**: 0 modified (6,422 chunks)
- **Integrity Status**: `PASSED`

---

## 8. Output Artifacts Inventory
| File Path | Description | Record Count / Size |
|---|---|---|
| `data/processed/preprocessed_corpus.json` | Unified preprocessed chunks corpus | 6,422 objects |
| `data/processed/bm25_index.json` | Inverted BM25 sparse index | 6,422 doc IDs, 33,038 terms |
| `data/processed/dense_index.faiss` | FAISS IndexFlatIP dense vector index | 6,422 vectors (dim 384) |
| `data/processed/dense_index_map.json` | Dense vector ID map | 6,422 index-to-chunk_id mappings |
| `data/processed/preprocessor_report.csv` | Chunk-level text cleaning diff log | 6,422 rows |
| `data/processed/preprocessor_summary.txt` | Preprocessing summary report | Summary statistics |

---

## 9. Automated Unit Test Suite Summary
All 22 unit tests (`preprocessing/test_phase3_3_preprocessing.py`) passed successfully:

| Test ID | Test Name | Status |
|---|---|---|
| `P3.3-01` | Input chunk count = 6,422 | `PASS` |
| `P3.3-02` | Chunk ID uniqueness | `PASS` |
| `P3.3-03` | Non-empty chunk text | `PASS` |
| `P3.3-04` | Output corpus count = 6,422 | `PASS` |
| `P3.3-05` | 15-field schema completeness | `PASS` |
| `P3.3-06` | Deterministic chunk ordering | `PASS` |
| `P3.3-07` | 0 U+FFFD replacement characters | `PASS` |
| `P3.3-08` | Unicode $\pm$ preservation (886 chunks) | `PASS` |
| `P3.3-09` | BM25 document count = 6,422 | `PASS` |
| `P3.3-10` | BM25 doc_ids mapping entries = 6,422 | `PASS` |
| `P3.3-11` | BM25 parameters ($k_1=1.5, b=0.75$) | `PASS` |
| `P3.3-12` | FAISS vector count = 6,422 | `PASS` |
| `P3.3-13` | FAISS vector dimension = 384 | `PASS` |
| `P3.3-14` | FAISS index type = `IndexFlatIP` | `PASS` |
| `P3.3-15` | Dense map entries count = 6,422 | `PASS` |
| `P3.3-16` | 0 NaN / Inf embeddings | `PASS` |
| `P3.3-17` | 1-to-1 sparse/dense ID alignment | `PASS` |
| `P3.3-18` | Raw PDF assets unchanged | `PASS` |
| `P3.3-19` | Manifest asset unchanged | `PASS` |
| `P3.3-20` | Parsed JSON assets unchanged | `PASS` |
| `P3.3-21` | Chunk JSON assets unchanged | `PASS` |
| `P3.3-22` | Deterministic index reproducibility | `PASS` |
