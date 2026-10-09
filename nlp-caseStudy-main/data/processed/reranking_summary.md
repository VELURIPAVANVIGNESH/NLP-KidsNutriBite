# NutriKid Phase 3.5 Reranking Evaluation Report

**Timestamp:** 2026-10-03T13:12:51Z  
**Evaluation Benchmark Size:** 30 Curated Pediatric Nutrition Queries  
**Candidate Pool Size ($k_{cand}$):** 50 Candidates from Frozen Hybrid RRF  
**Final Evidence Window ($k_{final}$):** Top 5 Candidates  
**Baseline Anchor:** Frozen Phase 3.4.2 Hybrid RRF Baseline  

---

## 1. Comprehensive Model Performance Comparison

The table below compares the frozen retrieval baselines against candidate Cross-Encoder rerankers across all 30 benchmark queries:

| Retrieval / Reranker Mode | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@1 | Precision@3 | Precision@5 | Precision@10 | nDCG@1 | nDCG@3 | nDCG@5 | nDCG@10 | MRR | MAP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25 (Frozen)** | 0.0167 | 0.0667 | 0.1167 | 0.1333 | 0.0333 | 0.0444 | 0.0467 | 0.0267 | 0.0333 | 0.0570 | 0.0839 | 0.0922 | **0.0958** | **0.0629** |
| **Dense BGE-Small (Frozen)** | 0.0500 | 0.1167 | 0.1500 | 0.2500 | 0.1000 | 0.0778 | 0.0600 | 0.0500 | 0.0810 | 0.1095 | 0.1310 | 0.1691 | **0.1884** | **0.1123** |
| **Hybrid RRF (Frozen Baseline)** | 0.0167 | 0.1000 | 0.2167 | 0.3167 | 0.0333 | 0.0667 | 0.0867 | 0.0633 | 0.0333 | 0.0878 | 0.1378 | 0.1820 | **0.1423** | **0.0987** |
| **BAAI/bge-reranker-base** | 0.0833 | 0.1833 | 0.2500 | 0.3500 | 0.1667 | 0.1222 | 0.1000 | 0.0700 | 0.1476 | 0.1848 | 0.2289 | 0.2657 | **0.2751** | **0.1644** |

---

## 2. Absolute & Relative Improvement vs. Hybrid RRF Baseline

Metrics comparison against the frozen **Hybrid RRF Baseline** ($	ext{MRR} = 0.0400, 	ext{MAP} = 0.0367, 	ext{nDCG}@5 = 0.0435$):

| Evaluated Reranker | Metric | Baseline Value | Reranked Value | Absolute Gain | Relative Improvement (%) | Target (>= +25% MRR) Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| BAAI/bge-reranker-base | MRR | 0.1423 | 0.2751 | +0.1328 | **+93.29%** | **ACHIEVED** |
| BAAI/bge-reranker-base | MAP | 0.0987 | 0.1644 | +0.0657 | **+66.63%** | N/A |
| BAAI/bge-reranker-base | NDCG@5 | 0.1378 | 0.2289 | +0.0911 | **+66.14%** | N/A |
| BAAI/bge-reranker-base | RECALL@5 | 0.2167 | 0.2500 | +0.0333 | **+15.38%** | N/A |

---

## 3. Key Experimental Research Findings

1. **Best Reranker Model:** `BAAI/bge-reranker-base` achieved top overall metrics.
2. **Target >= +25% Relative MRR Improvement:** **ACHIEVED** (Observed relative MRR gain: BGE-Reranker-Base: **+93.29%**).
3. **Top-Rank Precision:** Cross-Encoder self-attention over candidate pairs successfully boosted relevant passage placement in the top 3 spots.
4. **Baseline Integrity:** All 77 frozen baseline assets remained 100% untouched during evaluation.

---
