# Phase 3.2 — Structure-Aware Chunking Documentation

**Phase Status:** **PASSED (18 / 18 Automated Unit Tests Passing — 100.0%)**  
**Phase 3.3 Readiness:** **`READY`**  

---

## 1. Executive Overview

Phase 3.2 is the domain- and structure-aware chunking engine for NutriKid. It ingests the 22 parsed layout JSON files from Phase 2 (`data/processed/parsed/*.json`), applying specialized sentence-aware boundary splitting for general clinical guidelines (WHO, ICMR-NIN) and domain-specific table grouping algorithms for the Indian Food Composition Tables 2017 (`NK-010` / `IFCT_BOOK.pdf`).

Every generated chunk inherits exact document metadata from [`corpus_manifest.csv`](file:///c:/Users/abhir/.android/OneDrive/Desktop/nlp-class/NLP-Implementation-casestudy/NLP-Implementation/data/metadata/corpus_manifest.csv), page provenance lists, and section context headers. Structural noise and orphan divider fragments are identified and excluded from the retrieval set while maintaining strict mathematical accounting.

---

## 2. Input Scope & Manifest Contracts

- **Active Documents Processed:** **22 Documents** (100.0% of active manifest rows where `retrieval_enabled == "true"`).
- **Disabled Documents Excluded:** **10 Documents** (100.0% of disabled manifest rows producing 0 chunks).
- **Input Source Files:** 22 parsed JSON files in `data/processed/parsed/`.

---

## 3. Chunking Accounting & Structural Exclusion

Raw text extraction produces initial structural candidates before orphan filtering. Chunks matching structural noise criteria (short divider lines, pure page numbers, isolated annex tags, or empty buffers) are classified as **structural/orphan chunks** and excluded from retrieval payloads.

$$ \text{Raw Chunks} = \text{Final Retrieval Chunks} + \text{Excluded Structural Chunks} $$
$$ 6,438 = 6,422 + 16 $$

| Accounting Category | Count | Percentage |
| :--- | :---: | :---: |
| **Raw Chunks Generated** | **6,438** | 100.0% |
| **Structural / Orphan Chunks Excluded** | **16** | 0.25% |
| **Final Retrieval-Eligible Chunks** | **6,422** | 99.75% |

---

## 4. Chunk Length Distinction Statistics

The pipeline enforces distinct chunking strategies based on document type:

1. **General Prose Documents (Target $\le 1000$ chars, Max $\le 1400$ chars, Overlap $200$ chars):**
   - Uses conservative sentence-aware boundary splitting.
   - Flushes chunks when accumulated length reaches target threshold (1000) or max boundary (1400).
   - Indivisible single-sentence units exceeding 1400 characters (e.g. dense legal/regulatory paragraphs) are retained intact to avoid sentence fragmentation.
   - **Multi-sentence chunks exceeding 1400 characters count: `0` (0 multi-sentence bugs)**.

2. **IFCT Structured Food Tables (`NK-010`):**
   - Groups food composition rows by `ifct_rows_per_chunk = 6`.
   - Propagates category context (`Category: ...`) and table column headers (`Table Columns: ...`).

| Chunk Type | Count | Avg Length | Min Length | Max Length |
| :--- | :---: | :---: | :---: | :---: |
| **General Prose Chunks** | **4,872** | 1,091.8 chars | 11 chars | 4,869 chars |
| **IFCT Structured Table Chunks** | **1,550** | 428.1 chars | 10 chars | 1,351 chars |
| **Total Retrieval Chunks** | **6,422** | 931.5 chars | 10 chars | 4,869 chars |

---

## 5. IFCT Table Structure & Category Reset Validation

For `NK-010` (`IFCT_BOOK.pdf`), the chunker performs dynamic table audit and category provenance tracking:

- **Total IFCT Pages Inspected:** 585 pages
- **Pages Containing Food Row Codes (`^[A-Z]\d{3}`):** 514 pages
- **Total Food Rows Detected:** **8,266 food composition rows**
- **Category-Prefixed Table Chunks:** **1,226 chunks**
- **Category Resets (>15 Page Gaps):** **3 Category Resets**
  - **Page 162:** Category `'L MILK AND MILK PRODUCTS'` reset (16 pages gap).
  - **Page 204:** Category `'O ANIMAL MEAT'` reset (16 pages gap).
  - **Page 486:** Category `'J MUSHROOMS'` reset (16 pages gap).

---

## 6. Metadata Inheritance & Page Provenance

Every chunk in `data/processed/chunks/*.json` and `data/processed/preprocessed_corpus.json` inherits 100% of parent document metadata:

- `chunk_id` (format `{source_id}-C{index:05d}`)
- `source_id`, `source_name`, `file_name`, `relative_path`
- `publisher`, `publication_year`, `document_type`, `authority_tier`, `domain`
- `age_min`, `age_max` (preserves `null` without mutation)
- `page_numbers` (sorted list of positive integers)

**Validation Result:**
- **Metadata Inheritance Errors:** **`0`**
- **Page Provenance Errors:** **`0`**
- **Duplicate Chunk IDs:** **`0`**
- **Meaningful Content Page Coverage:** **`100.0%` (0 uncovered content pages)**

---

## 7. Unicode Integrity & Determinism

- **U+FFFD Replacement Characters Added:** **`0`** (0.0000% corruption rate).
- **Unicode Symbol Preservation ($\pm$, $\mu g$, %):** **`PASSED`**.
- **Deterministic Output Reproducibility:** **`PASS`** (100.0% identical hashes across repeated executions).
- **Frozen Asset Integrity:** **`0`** raw PDFs, manifest rows, or Phase 2 parsed JSON files modified.

---

## 8. Verification Commands & Test Results

Run contract test suite:

```bash
python preprocessing/test_phase3_chunking.py
```

### Test Suite Execution Output
```text
==================================================
PHASE 3.2 — STRUCTURE-AWARE CHUNKING VALIDATION
==================================================

Document Scope:
  Active documents processed: 22 / 22
  Disabled documents excluded: 10
  Status: PASS

Chunk Accounting:
  Raw chunks generated: 6438
  Structural/orphan chunks excluded: 16
  Final retrieval-eligible chunks: 6422
  Duplicate chunk IDs: 0
  Status: PASS

Chunk Length Distinction Statistics:
  Prose chunks count: 4872 (avg len: 1091.8 chars)
  IFCT table chunks count: 1550 (avg len: 428.1 chars)
  Single indivisible sentence units >1400: 109
  Multi-sentence chunks >1400 (Bugs): 0
  Status: PASS

IFCT & Structural Audit:
  Total IFCT food rows detected: 8266
  Category-prefixed table chunks: 1226
  Category resets caused by >15-page gaps: 3
  Status: PASS

Metadata & Provenance Validation:
  Metadata inheritance errors: 0
  Page provenance errors: 0
  Meaningful page coverage: 100.0% (0 uncovered content pages)
  Status: PASS

Integrity & Determinism:
  Unicode U+FFFD corruption added: 0
  Unicode ± preservation: PASS
  Deterministic chunking reproducibility: PASS
  Frozen asset modifications: 0
  Status: PASS

==================================================
PHASE 3.2 RESULT: PASS
==================================================
```
