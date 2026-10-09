Absolutely. Below is a **complete `phase1.md`** that is simple enough to read and explain to your teacher, but still technically strong. You can directly replace your existing `phase_docs/phase1.md` with this.

````markdown
# Phase 1 — PDF Corpus Ingestion & Metadata Manifest

**Project:** NutriKid Pediatric Nutrition RAG  
**Phase:** 1 — Corpus Ingestion & Manifest  
**Primary Owner:** Abhiram  
**Status:** PASS  
**Automated Tests:** 15/15 PASS

---

# 1. Purpose of Phase 1

Phase 1 is the starting point of the NutriKid RAG pipeline.

The main purpose is to:

1. Find all PDF documents in the knowledge corpus.
2. Assign a unique ID to every document.
3. Collect important metadata about each document.
4. Record which documents are allowed to participate in retrieval.
5. Calculate file hashes to verify document integrity.
6. Store all information in a central manifest file.

The output of this phase is:

```text
knowledge_corpus/
        ↓
PDF Discovery
        ↓
Metadata Collection
        ↓
Integrity Checking
        ↓
Retrieval Eligibility
        ↓
corpus_manifest.csv
````

The manifest becomes the control registry used by later phases.

---

# 2. Input

The main input is the:

```text
knowledge_corpus/
```

directory.

It contains:

```text
32 PDF documents
```

distributed across the project's authority/domain folders.

The PDFs are the original knowledge sources. They are not modified during Phase 1.

---

# 3. Main Components

Phase 1 contains three main Python components.

## 3.1 `generate_manifest.py`

Location:

```text
preprocessing/generate_manifest.py
```

This is the main ingestion script.

It performs:

* PDF discovery
* metadata collection
* MD5 hash calculation
* deterministic source ID assignment
* retrieval eligibility assignment
* manifest generation

---

## 3.2 `validate_manifest.py`

Location:

```text
preprocessing/validate_manifest.py
```

This validates the generated manifest.

It checks:

* CSV schema
* source IDs
* duplicate IDs
* PDF paths
* required metadata
* retrieval flags

---

## 3.3 `test_phase1_manifest.py`

Location:

```text
preprocessing/test_phase1_manifest.py
```

This is the automated Phase 1 test suite.

It contains:

```text
15 automated tests
```

covering:

* PDF discovery
* document count
* manifest existence
* source ID uniqueness
* metadata validation
* active/disabled partitioning
* path validation
* file integrity

---

# 4. PDF Discovery

The first operation is discovering all PDFs inside the corpus.

The important code concept is:

```python
for root, dirs, files in os.walk(corpus_dir):
    for file in files:
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(root, file)
            pdf_files.append(pdf_path)
```

## What this does

`os.walk()` recursively searches the entire corpus directory.

For example:

```text
knowledge_corpus/
├── folder1/
│   ├── document1.pdf
│   └── document2.pdf
├── folder2/
│   ├── document3.pdf
│   └── document4.pdf
└── ...
```

The script finds PDFs even when they are inside subdirectories.

### Result

```text
Physical PDFs = 32
Discovered PDFs = 32
```

Therefore:

```text
Discovery Coverage = 32 / 32 × 100
                   = 100%
```

---

# 5. Deterministic Sorting

After discovering the PDFs, they are sorted.

Important concept:

```python
pdf_files.sort()
```

Sorting is important because the source IDs are assigned according to the order of the files.

Without deterministic sorting, IDs could potentially change between executions.

---

# 6. Source ID Assignment

Each PDF receives a unique NutriKid source ID.

The important code is:

```python
source_id = f"NK-{index:03d}"
```

Examples:

```text
1  → NK-001
2  → NK-002
3  → NK-003
...
32 → NK-032
```

These IDs provide stable document-level identifiers.

They are later useful for:

* provenance
* retrieval
* citations
* debugging
* document mapping

---

# 7. Relative File Paths

The manifest stores a relative path rather than depending on an absolute computer-specific path.

The important code is:

```python
relative_path = os.path.relpath(
    pdf_path,
    corpus_dir
)
```

For example:

```text
Absolute path:
C:/project/knowledge_corpus/WHO/guideline.pdf

Relative path:
WHO/guideline.pdf
```

This makes the project easier to move between machines.

---

# 8. Metadata Collection

Every document receives metadata.

The manifest contains 13 fields:

```text
source_id
source_name
file_name
relative_path
folder
publisher
publication_year
document_type
authority_tier
domain
age_min
age_max
retrieval_enabled
```

These fields provide information about:

* where the document came from
* who published it
* when it was published
* what type of document it is
* its authority level
* its nutrition domain
* applicable age range
* whether it can participate in retrieval

---

# 9. MD5 File Integrity

Phase 1 also calculates a cryptographic fingerprint for the PDFs.

The important code pattern is:

```python
def calculate_md5(file_path):
    md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)

    return md5.hexdigest()
```

## Why use binary mode?

```python
"rb"
```

means:

```text
read binary
```

PDFs are binary files, so they should be read as bytes for exact hashing.

## Why read in chunks?

Instead of loading an entire PDF into memory:

```python
f.read(8192)
```

reads 8192 bytes at a time.

This is more memory-efficient.

## Why MD5?

The hash acts as a file fingerprint.

If the PDF changes, its MD5 value changes.

Therefore we can detect accidental modification.

---

# 10. Retrieval Eligibility

Not every document in the corpus is necessarily used by the active retrieval system.

The manifest contains:

```text
retrieval_enabled
```

which can be:

```text
true
```

or:

```text
false
```

The current corpus contains:

```text
Total PDFs       = 32
Retrieval active = 22
Disabled         = 10
```

The 10 disabled documents are **still catalogued in the manifest**.

They are simply excluded from the active retrieval pipeline according to the project's corpus configuration.

This distinction is important:

```text
Corpus Registration
        ↓
       32 PDFs
        ↓
 ┌──────┴──────┐
 ↓             ↓
22 Active    10 Disabled
 ↓             ↓
Retrieval     Catalogued
```

---

# 11. Pediatric Age Metadata

The manifest contains:

```text
age_min
age_max
```

These fields provide age-scope information for downstream processing.

The NutriKid research population is:

```text
5.0 ≤ child_age ≤ 15.0
```

The important point is that Phase 1 **records age metadata**.

Later retrieval phases use this information for age compatibility filtering.

Phase 1 itself is primarily responsible for creating the metadata registry.

---

# 12. Manifest Generation

After collecting all records, the information is written to:

```text
data/metadata/corpus_manifest.csv
```

The basic CSV writing pattern is:

```python
with open(
    manifest_path,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(records)
```

This produces the central manifest.

---

# 13. Manifest Validation

After generation, the manifest is validated.

One important check is whether the referenced PDF exists.

The basic Python operation is:

```python
os.path.exists(pdf_path)
```

The system verifies that every recorded path points to an actual PDF.

Result:

```text
Existing PDF paths = 32/32
Missing paths      = 0
```

---

# 14. Source ID Uniqueness

Duplicate IDs could cause problems later during retrieval and provenance tracking.

A simple uniqueness concept is:

```python
ids = [row["source_id"] for row in records]

unique_ids = set(ids)

assert len(ids) == len(unique_ids)
```

Current result:

```text
Total IDs  = 32
Unique IDs = 32
Duplicates = 0
```

Therefore:

```text
ID Uniqueness = 32 / 32 × 100
              = 100%
```

---

# 15. Phase 1 Quality Metrics

Phase 1 uses several measurable quality checks.

## 15.1 Corpus Discovery Coverage

```text
Discovered PDFs / Physical PDFs × 100
```

Current result:

```text
32 / 32 × 100 = 100%
```

---

## 15.2 Metadata Completeness

All required manifest fields must be present.

Current result:

```text
32/32 documents
13/13 required fields
```

Therefore:

```text
Metadata Completeness = 100%
```

---

## 15.3 Identifier Uniqueness

```text
Unique IDs / Total IDs × 100
```

Current result:

```text
32 / 32 × 100 = 100%
```

---

## 15.4 Retrieval Partitioning

The corpus is divided into:

```text
22 Active
10 Disabled
```

Total:

```text
22 + 10 = 32
```

Therefore all documents are accounted for.

---

## 15.5 File Integrity

MD5 hashes are used to ensure the PDFs remain unchanged.

Result:

```text
Modified PDFs = 0
```

Therefore:

```text
MD5 Integrity = PASS
```

---

# 16. Phase 1 Test Suite

The automated test file is:

```text
preprocessing/test_phase1_manifest.py
```

Run it using:

```bash
python preprocessing/test_phase1_manifest.py
```

Expected result:

```text
==================================================
PHASE 1 — CORPUS INGESTION & MANIFEST VALIDATION
==================================================

PDF corpus:
  Total PDFs discovered: 32
  Expected PDFs: 32
  Status: PASS

Manifest:
  Manifest exists: PASS
  CSV readable: PASS

Source IDs:
  Total source IDs: 32
  Duplicate IDs: 0
  Missing IDs: 0
  Status: PASS

Retrieval status:
  Active documents: 22
  Disabled documents: 10
  Status: PASS

Path validation:
  Existing PDF paths: 32/32
  Missing PDF paths: 0
  Status: PASS

Metadata:
  Required fields present: PASS
  Invalid values: 0
  Status: PASS

Integrity:
  PDFs modified during validation: 0
  Manifest unexpectedly modified: 0
  Status: PASS

==================================================
PHASE 1 RESULT: PASS
==================================================
```

---

# 17. Expected vs Actual Results

| Check              | Expected | Actual | Result |
| ------------------ | -------: | -----: | ------ |
| Total PDFs         |       32 |     32 | PASS   |
| Active documents   |       22 |     22 | PASS   |
| Disabled documents |       10 |     10 | PASS   |
| Duplicate IDs      |        0 |      0 | PASS   |
| Missing paths      |        0 |      0 | PASS   |
| Metadata errors    |        0 |      0 | PASS   |
| PDF modifications  |        0 |      0 | PASS   |
| Automated tests    |       15 |     15 | PASS   |

---

# 18. Phase 1 Output Files

The main output is:

```text
data/metadata/corpus_manifest.csv
```

Testing/documentation outputs include:

```text
preprocessing/test_phase1_manifest.py

data/processed/phase1_validation_report.txt

docs/phase1_corpus_ingestion.md

docs/phase1_teacher_summary.txt

phase_docs/phase1.md
```

---

# 19. What Phase 1 Gives to Phase 2

Phase 1 produces the registry that controls the next stages.

The pipeline becomes:

```text
32 Source PDFs
       ↓
Phase 1
       ↓
corpus_manifest.csv
       ↓
Phase 2
       ↓
PDF Text Extraction
```

Phase 2 can use the manifest to determine:

* which documents exist
* their source IDs
* their metadata
* their file paths
* which documents are retrieval-enabled

---

# 20. What Was NOT Done in Phase 1

Phase 1 does not perform:

```text
PDF text extraction
       ✗

Text cleaning
       ✗

Chunking
       ✗

BM25 indexing
       ✗

FAISS embeddings
       ✗

Retrieval
       ✗

Reranking
       ✗

LLM generation
       ✗
```

Those belong to later phases.

---

# 21. Phase 1 Architecture

```text
             knowledge_corpus/
                    │
                    ▼
            PDF Discovery
              os.walk()
                    │
                    ▼
          Deterministic Sorting
                    │
                    ▼
           Source ID Assignment
              NK-001 ... NK-032
                    │
                    ▼
            Metadata Collection
                    │
                    ▼
             MD5 Calculation
                    │
                    ▼
        Retrieval Eligibility Flag
             /             \
            /               \
     22 Active           10 Disabled
            \               /
             \             /
              ▼           ▼
            corpus_manifest.csv
                    │
                    ▼
             Manifest Validation
                    │
                    ▼
              15/15 Tests PASS
```

---

# 22. Simple Explanation for Teacher

If asked:

### "What did you do in Phase 1?"

Say:

> "In Phase 1, we created the corpus ingestion and metadata management layer. We recursively discovered all 32 PDFs, assigned deterministic NK source IDs, collected metadata such as publisher, year, authority tier, domain and age range, calculated MD5 hashes for file integrity, and marked documents as retrieval-enabled or disabled. We then stored everything in `corpus_manifest.csv` and validated it using 15 automated tests. All tests passed with 100% discovery, metadata completeness and ID uniqueness."

---

# 23. Five Things to Remember for Viva

If you don't have time to remember everything, remember these:

### 1. `os.walk()`

```python
os.walk(corpus_dir)
```

**Purpose:** Discover PDFs recursively.

### 2. `hashlib.md5()`

```python
hashlib.md5()
```

**Purpose:** Verify file integrity.

### 3. Sorting

```python
pdf_files.sort()
```

**Purpose:** Deterministic processing.

### 4. Source IDs

```python
f"NK-{index:03d}"
```

**Purpose:** Stable document identifiers.

### 5. Manifest

```text
corpus_manifest.csv
```

**Purpose:** Central registry connecting PDFs with metadata and retrieval eligibility.

---

# 24. Final Verdict

```text
========================================
PHASE 1 — FINAL RESULT
========================================

PDFs discovered:          32/32
Active documents:         22
Disabled documents:       10
Duplicate IDs:             0
Missing paths:             0
Metadata errors:           0
PDF modifications:         0

Automated tests:        15/15 PASS

Discovery coverage:      100%
Metadata completeness:   100%
ID uniqueness:           100%
Integrity verification:  PASS

========================================
PHASE 1 STATUS: PASS
========================================
```

**Phase 1 is therefore frozen and ready for Phase 2 — PDF Parsing & Text Extraction.**

```

### One correction I would make before showing this to your teacher

Don't say **"immutable metadata registry"** too strongly. The CSV is a generated registry, and your validation verifies it wasn't unexpectedly modified during testing. A safer phrase is:

> **"validated metadata registry used as the frozen Phase 1 contract."**

That is technically more defensible in a viva.
```
