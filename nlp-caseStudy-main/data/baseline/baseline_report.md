# NutriKid Frozen Retrieval Baseline Report (Phase 3.4.2)

**Baseline Lock Version:** `v1.0.0-frozen`  
**Freeze Date:** 2026-08-11  
**Demographic Target Scope:** Children Aged 5.0 to 15.0 Years  

> **OFFICIAL FREEZE DECLARATION:**  
> *"This is the frozen retrieval baseline against which all downstream reranking, refinement, generation and safety improvements will be measured."*

---

## 1. Frozen Baseline System Specifications

| System Layer | Frozen Implementation Details |
| :--- | :--- |
| **Corpus** | 22 active core PDFs parsed into 2,339 pages containing 6,021,221 characters. |
| **Chunking** | 6,429 retrieval-eligible chunks (4,879 prose + 1,550 IFCT structured table chunks). |
| **Sparse Index** | BM25 index over 6,429 documents ($k_1=1.5, b=0.75$, vocab size = 32,939). |
| **Dense Index** | FAISS `IndexFlatIP` embedding vectors generated using `BAAI/bge-small-en-v1.5` (384 dim). |
| **Hybrid Fusion** | Reciprocal Rank Fusion (RRF $k=60$) over top $k_{cand}=100$ sparse & dense candidates. |
| **Safety Gate** | Hard pediatric age compatibility enforcement ($5.0 \le \text{child\_age} \le 15.0$). |

---

## 2. Quantitative Baseline Benchmark Performance

Evaluated over the 30-query independent ground-truth evaluation benchmark (`data/eval/evaluation_queries.json`):

| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@1 | Precision@3 | Precision@5 | Precision@10 | nDCG@1 | nDCG@3 | nDCG@5 | nDCG@10 | MRR | MAP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25** | 0.0000 | 0.0500 | 0.0667 | 0.0667 | 0.0000 | 0.0333 | 0.0267 | 0.0133 | 0.0000 | 0.0353 | 0.0466 | 0.0466 | 0.0361 | 0.0292 |
| **DENSE** | 0.0000 | 0.0167 | 0.0333 | 0.0500 | 0.0000 | 0.0111 | 0.0133 | 0.0100 | 0.0000 | 0.0131 | 0.0233 | 0.0270 | 0.0178 | 0.0137 |
| **HYBRID** | **0.0167** | **0.0333** | **0.0500** | **0.0500** | **0.0333** | **0.0222** | **0.0200** | **0.0100** | **0.0333** | **0.0333** | **0.0435** | **0.0435** | **0.0400** | **0.0367** |

---

## 3. Regression Verification & Integrity

- **Automated Regression Suite:** Verified 100% passing across all 8 regression gates via `python -m unittest discover -s tests`.
- **Determinism:** Two consecutive benchmark executions produced 100% identical rank order and metric scores within $10^{-6}$ tolerance.
- **Read-Only Data Integrity:** Checked and locked MD5 checksums across all 77 baseline data assets, `retrieve.py`, and `config.json`.
