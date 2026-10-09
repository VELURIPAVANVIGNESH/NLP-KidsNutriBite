Yes. Below is a **complete `phase_docs/phase2.md`** in the same style as Phase 1: readable for your teacher, technically accurate, with the important code snippets you should understand for viva.

You can copy this directly into `phase_docs/phase2.md`.

````markdown
# Phase 2 — PDF Parsing & Text Extraction

**Project:** NutriKid Pediatric Nutrition RAG  
**Phase:** 2 — PDF Parsing & Text Extraction  
**Primary Owner:** Pavan  
**Status:** PASS  
**Automated Tests:** 17/17 PASS  
**Phase 3 Readiness:** READY

---

# 1. Purpose of Phase 2

Phase 2 converts the original PDF documents into structured JSON files containing page-level extracted text.

The main purpose is to:

1. Read the Phase 1 manifest.
2. Select only retrieval-enabled documents.
3. Open each PDF.
4. Extract text page-by-page.
5. Preserve page numbers.
6. Preserve document metadata.
7. Classify pages according to extracted text.
8. Store the parsed information as JSON.
9. Validate extraction quality and integrity.

The pipeline is:

```text
Phase 1
corpus_manifest.csv
        ↓
Select retrieval_enabled = true
        ↓
Read PDF using pypdf
        ↓
Extract text page-by-page
        ↓
Classify page status
        ↓
Attach metadata
        ↓
Structured JSON
        ↓
Phase 2 Validation
````

---

# 2. Input

Phase 2 uses the Phase 1 manifest:

```text
data/metadata/corpus_manifest.csv
```

The manifest contains 32 documents.

However, only documents marked:

```text
retrieval_enabled = true
```

are parsed.

Current corpus:

```text
Total PDFs              = 32
Retrieval-enabled       = 22
Retrieval-disabled      = 10
```

Therefore:

```text
22 PDFs → parsed
10 PDFs → not parsed
```

The disabled documents remain registered in the Phase 1 manifest but are not part of the active retrieval corpus.

---

# 3. Main Components

Phase 2 contains three important components.

## 3.1 `parse_documents.py`

Location:

```text
preprocessing/parse_documents.py
```

This is the main PDF parser.

It performs:

* configuration loading
* manifest loading
* active-document filtering
* PDF opening
* page extraction
* page classification
* metadata preservation
* JSON generation
* parser reports

---

## 3.2 `config.json`

Location:

```text
preprocessing/config.json
```

The parser configuration contains important paths and parameters such as:

```json
{
    "manifest_path": "data/metadata/corpus_manifest.csv",
    "parsed_dir": "data/processed/parsed",
    "min_character_threshold": 10
}
```

The `min_character_threshold` is used to distinguish meaningful extracted text from very short pages.

---

## 3.3 `test_phase2_parser.py`

Location:

```text
preprocessing/test_phase2_parser.py
```

This is the automated Phase 2 contract test suite.

It contains:

```text
17 automated tests
```

covering:

* document count
* disabled-document exclusion
* JSON validity
* schema validity
* page numbering
* text extraction
* character statistics
* metadata inheritance
* Unicode integrity
* deterministic structure
* frozen asset integrity

---

# 4. Selecting Active Documents

Phase 2 reads the manifest and selects only retrieval-enabled documents.

The important logic is conceptually:

```python
for row in manifest_rows:
    if row["retrieval_enabled"].lower() == "true":
        active_documents.append(row)
```

This ensures that disabled sources do not accidentally enter the retrieval pipeline.

Current result:

```text
Active documents   = 22
Disabled documents = 10
```

Therefore:

```text
22/22 active documents parsed
0 disabled documents parsed
```

---

# 5. Opening the PDF

The parser uses `pypdf`.

The important code concept is:

```python
from pypdf import PdfReader

reader = PdfReader(pdf_path)
```

`PdfReader` loads the PDF structure and gives access to its pages.

---

# 6. Page-by-Page Extraction

The parser processes every page individually.

The important code pattern is:

```python
for page_number, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""
```

### Why process pages individually?

Because page-level provenance is important for a RAG system.

Later, when a retrieved chunk is used to answer a question, we need to know:

```text
Which document?
Which page?
```

For example:

```text
NK-008
Page 60
```

can later become a source citation.

---

# 7. Handling Empty Extraction

Sometimes:

```python
page.extract_text()
```

can return `None`.

Therefore the parser safely converts it to an empty string:

```python
text = page.extract_text() or ""
```

This prevents errors such as:

```text
AttributeError
```

when trying to calculate the length of a `None` value.

---

# 8. Page Text Classification

The parser uses a minimum text threshold:

```text
min_character_threshold = 10
```

Pages can therefore be classified as:

```text
ok
low_text
empty
```

Conceptually:

```python
if len(text.strip()) == 0:
    status = "empty"

elif len(text.strip()) < min_character_threshold:
    status = "low_text"

else:
    status = "ok"
```

This distinction is useful because a page containing only:

```text
2
```

is technically non-empty but does not contain meaningful content.

---

# 9. Page Structure

Each parsed document stores page-level information.

A simplified structure looks like:

```json
{
    "page_number": 1,
    "text": "Extracted page text...",
    "status": "ok"
}
```

The exact top-level JSON structure is validated by the Phase 2 test suite.

The important idea is:

```text
Document
   ↓
Pages
   ↓
Page number + extracted text + status
```

---

# 10. Metadata Preservation

Phase 2 does not throw away the metadata collected in Phase 1.

Metadata such as:

```text
source_id
publisher
publication_year
document_type
authority_tier
domain
age_min
age_max
```

is carried into the parsed document.

This is important because later stages need metadata for:

* provenance
* age filtering
* source attribution
* retrieval
* citations

The validation checks that the parsed metadata matches the manifest.

---

# 11. Page Numbering

Pages are numbered sequentially.

The important code pattern is:

```python
enumerate(reader.pages, start=1)
```

This means the first PDF page is:

```text
page_number = 1
```

rather than:

```text
page_number = 0
```

This is useful because human-readable PDF citations normally use page numbers beginning at 1.

---

# 12. JSON Output

The parser generates one JSON file per active source.

Output directory:

```text
data/processed/parsed/
```

Examples:

```text
NK-001_parsed.json
NK-002_parsed.json
NK-003_parsed.json
...
```

There are:

```text
22 parsed JSON files
```

because there are 22 active documents.

---

# 13. Extraction Results

The Phase 2 parser produced:

```text
Active documents discovered:        22
Active documents parsed:            22
Failed documents:                    0

Total pages processed:            2403

Pages with >=10 characters:       2335
Empty pages:                         47
Low-text pages:                      21

Total characters:             6,014,229
Total words:                    884,020
```

Therefore:

```text
22 / 22 active documents successfully parsed
```

---

# 14. Text Extraction Coverage

The main extraction coverage metric is:

```text
Pages with meaningful text
-------------------------------- × 100
Total processed pages
```

Current values:

```text
Meaningful text pages = 2335
Total pages           = 2403
```

Therefore:

```text
2335 / 2403 × 100
= 97.17%
```

### Result

```text
Text Extraction Coverage = 97.17%
```

This means most pages produced meaningful extracted text.

---

# 15. Empty and Low-Text Pages

The parser found:

```text
Empty pages       = 47
Low-text pages    = 21
```

Total pages without >=10 characters:

```text
47 + 21 = 68
```

These pages are not automatically treated as parser failures.

A page can be:

* genuinely blank
* a divider
* a page number page
* a graphical page
* a scanned/image-only page
* a page with very little extractable text

Therefore these statistics are reported separately.

---

# 16. Character Statistics

The parser extracted:

```text
Total characters = 6,014,229
```

Average characters per page:

```text
6,014,229 / 2,403
≈ 2,502.8
```

Measured values:

```text
Minimum page text length = 0
Maximum page text length = 7,255
Average = 2,502.8
```

These measurements help identify unusual extraction behavior.

---

# 17. Unicode Integrity

One important validation is checking for the Unicode replacement character:

```text
U+FFFD
```

It usually appears as:

```text
�
```

and can indicate decoding or extraction corruption.

The validation checks:

```python
"\ufffd" in text
```

or counts:

```python
text.count("\ufffd")
```

Current result:

```text
U+FFFD characters = 0
```

Therefore:

```text
Unicode corruption detected = 0
```

---

# 18. Null Byte Validation

The parser also checks for unexpected null bytes:

```text
\x00
```

Conceptually:

```python
"\x00" in text
```

Current result:

```text
Null bytes = 0
```

Therefore no null-byte corruption was detected.

---

# 19. Metadata Inheritance Validation

The Phase 2 test suite compares parsed metadata against the Phase 1 manifest.

For example:

```python
assert parsed["source_id"] == manifest["source_id"]
```

Similar checks are performed for fields such as:

```text
publisher
publication_year
document_type
authority_tier
domain
age_min
age_max
```

Current result:

```text
22 / 22 documents matched
```

Therefore:

```text
Metadata inheritance = 100%
```

---

# 20. JSON Schema Validation

The parser output must be valid JSON.

The tests verify:

```python
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
```

The test suite then checks the required structure.

Current result:

```text
Valid JSON files = 22/22
Top-level schema valid = 22/22
```

Therefore:

```text
Schema validity = 100%
```

---

# 21. Deterministic Parsing

A good preprocessing pipeline should produce the same structure when run again on the same inputs.

The Phase 2 validation therefore checks deterministic output structure.

Conceptually, a canonical representation can be compared:

```python
json.dumps(
    data,
    sort_keys=True,
    ensure_ascii=False
)
```

The goal is:

```text
Same input
   ↓
Parser Run 1
   ↓
Output A

Same input
   ↓
Parser Run 2
   ↓
Output B

A == B
```

Current result:

```text
Deterministic parsing = PASS
```

---

# 22. Frozen Asset Integrity

Phase 2 must not modify the original knowledge sources.

The following are treated as frozen:

```text
knowledge_corpus/*.pdf
data/metadata/corpus_manifest.csv
```

The test suite verifies their hashes before and after parsing.

Current result:

```text
PDF modifications      = 0
Manifest modifications = 0
```

Therefore:

```text
Frozen asset integrity = PASS
```

---

# 23. Phase 2 Quality Metrics

The main Phase 2 metrics are:

## 23.1 Extraction Coverage

```text
2335 / 2403 × 100 = 97.17%
```

Result:

```text
97.17%
```

---

## 23.2 Unicode Corruption Rate

```text
U+FFFD characters / total characters × 100
```

Current:

```text
0 / 6,014,229 × 100
= 0%
```

Result:

```text
0.0000%
```

---

## 23.3 Schema Validity

```text
Valid parsed JSON files
----------------------- × 100
Active parsed documents
```

Current:

```text
22 / 22 × 100
= 100%
```

---

## 23.4 Metadata Inheritance

```text
Correctly inherited metadata
---------------------------- × 100
Active documents
```

Current:

```text
22 / 22 × 100
= 100%
```

---

## 23.5 Deterministic Reproducibility

```text
Matching outputs / total outputs × 100
```

Current result:

```text
100%
```

---

# 24. Expected vs Actual Results

| Check                   | Expected |    Actual | Status |
| ----------------------- | -------: | --------: | ------ |
| Active PDFs parsed      |       22 |        22 | PASS   |
| Disabled PDFs parsed    |        0 |         0 | PASS   |
| Total pages             |    ~2403 |      2403 | PASS   |
| Pages with >=10 chars   |    ~2339 |      2335 | PASS   |
| Extracted characters    |   ~6.02M | 6,014,229 | PASS   |
| Average characters/page |    ~2500 |    2502.8 | PASS   |
| U+FFFD characters       |        0 |         0 | PASS   |
| Null bytes              |        0 |         0 | PASS   |
| PDF modifications       |        0 |         0 | PASS   |
| Manifest modifications  |        0 |         0 | PASS   |
| Deterministic parsing   |     PASS |      PASS | PASS   |
| Automated tests         |       17 |        17 | PASS   |

---

# 25. Phase 2 Test Suite

The test file is:

```text
preprocessing/test_phase2_parser.py
```

Run:

```bash
python preprocessing/test_phase2_parser.py
```

If you want to regenerate the parsed files first:

```bash
python preprocessing/parse_documents.py
```

Then run:

```bash
python preprocessing/test_phase2_parser.py
```

---

# 26. Expected Test Result

The expected final result is:

```text
==================================================
PHASE 2 — PDF PARSING & TEXT EXTRACTION VALIDATION
==================================================

Parsed Documents:
Active PDFs parsed: 22 / 22
Disabled PDFs parsed: 0
Status: PASS

JSON Schema & Integrity:
Valid JSON files: 22 / 22
Top-level schema valid: 22 / 22
Source ID & metadata match: PASS
Status: PASS

Page Statistics:
Total pages processed: 2403
Pages with text (>=10 chars): 2335
Empty pages (0 chars): 47
Low-text pages (<10 chars): 21
Text extraction coverage: 97.17%
Status: PASS

Character Statistics:
Total extracted characters: 6,014,229
Average characters/page: 2502.8
Min page text length: 0 chars
Max page text length: 7,255 chars
U+FFFD replacement characters: 0
Null byte corruption: 0
Status: PASS

Integrity & Determinism:
PDFs modified during parsing: 0
Manifest modified during parsing: 0
Deterministic parsing verification: PASS
Status: PASS

==================================================
PHASE 2 RESULT: PASS
==================================================
```

---

# 27. Phase 2 Output Files

The primary parsed outputs are:

```text
data/processed/parsed/
```

containing:

```text
22 JSON files
```

The parser also generates reporting files such as:

```text
data/processed/parser_report.csv
data/processed/parser_summary.txt
```

The automated test suite is:

```text
preprocessing/test_phase2_parser.py
```

The phase documentation is:

```text
phase_docs/phase2.md
```

---

# 28. What Phase 2 Gives to Phase 3

Phase 2 transforms:

```text
PDF files
```

into:

```text
Structured page-level JSON
```

Therefore the pipeline becomes:

```text
Phase 1
PDF Corpus
    ↓
corpus_manifest.csv
    ↓
Phase 2
PDF Parsing
    ↓
22 Parsed JSON Documents
    ↓
Phase 3
Structure-Aware Chunking
```

Phase 3 can now use:

* page text
* page numbers
* source IDs
* metadata
* document structure

to create retrieval-ready chunks.

---

# 29. What Phase 2 Does NOT Do

Phase 2 only performs parsing and extraction.

It does NOT perform:

```text
Chunking                 ✗
Text normalization      ✗
BM25 indexing            ✗
FAISS embeddings         ✗
Dense retrieval          ✗
Hybrid retrieval         ✗
Reranking                ✗
LLM generation          ✗
```

Those belong to later phases.

---

# 30. Phase 2 Architecture

```text
                 corpus_manifest.csv
                         │
                         ▼
               Filter active documents
                  retrieval_enabled=true
                         │
                         ▼
                  22 Active PDFs
                         │
                         ▼
                  pypdf PdfReader
                         │
                         ▼
                 Page-by-page extraction
                         │
                         ▼
              Page text classification
              /          |          \
             /           |           \
          EMPTY       LOW_TEXT       OK
             \           |           /
              \          |          /
                       ▼
                Metadata attachment
                       │
                       ▼
                Structured JSON
                       │
                       ▼
                 Phase 2 Tests
                       │
                       ▼
                  17/17 PASS
```

---

# 31. Simple Explanation for Teacher

If asked:

### "What did you do in Phase 2?"

Say:

> "In Phase 2, we converted the 22 retrieval-enabled PDFs into structured page-level JSON documents. We used pypdf to extract text page-by-page while preserving source metadata and page provenance. We classified pages as normal, low-text or empty and generated 22 parsed JSON files. We then validated schema, metadata inheritance, extraction coverage, Unicode integrity, deterministic parsing and frozen-source integrity. We processed 2,403 pages and extracted about 6 million characters, with 97.17% meaningful text coverage and zero replacement-character corruption."

---

# 32. Five Important Code Concepts to Remember

For a viva, you do not need to memorize the entire parser.

Remember these five concepts.

## 1. Read the PDF

```python
from pypdf import PdfReader

reader = PdfReader(pdf_path)
```

**Purpose:** Open and read the PDF.

---

## 2. Iterate through pages

```python
for page_number, page in enumerate(
    reader.pages,
    start=1
):
```

**Purpose:** Process every page while keeping human-readable page numbers.

---

## 3. Extract text safely

```python
text = page.extract_text() or ""
```

**Purpose:** Extract page text and avoid `None` values.

---

## 4. Classify pages

```python
if len(text.strip()) == 0:
    status = "empty"
elif len(text.strip()) < 10:
    status = "low_text"
else:
    status = "ok"
```

**Purpose:** Identify meaningful, low-text and empty pages.

---

## 5. Preserve metadata

Conceptually:

```python
parsed_document = {
    "source_id": row["source_id"],
    "publisher": row["publisher"],
    "publication_year": row["publication_year"],
    "domain": row["domain"],
    "age_min": row["age_min"],
    "age_max": row["age_max"],
    "pages": pages
}
```

**Purpose:** Keep the connection between extracted text and its original source.

---

# 33. Phase 2 Final Verdict

```text
========================================
PHASE 2 — FINAL RESULT
========================================

Active PDFs parsed:       22/22
Disabled PDFs parsed:      0
Total pages:            2403
Text pages:             2335
Text coverage:          97.17%

Characters:          6,014,229
Words:                 884,020

U+FFFD corruption:          0
Null-byte corruption:       0

JSON validity:         22/22
Metadata parity:       22/22
Determinism:              PASS
PDF modifications:          0
Manifest modifications:     0

Automated tests:      17/17 PASS

========================================
PHASE 2 STATUS: PASS
PHASE 3 READINESS: READY
========================================
```

**Phase 2 is frozen and ready for Phase 3.2 — Structure-Aware Chunking.**

```

### The 5 lines I'd personally memorize for your viva

If ma'am suddenly asks you **"Explain Phase 2 technically"**, say:

> **"We read the Phase 1 manifest and selected the 22 retrieval-enabled PDFs. Using `pypdf.PdfReader`, we extracted text page-by-page and preserved page numbers and source metadata. We classified pages using a 10-character threshold into `ok`, `low_text`, and `empty`. We processed 2,403 pages, obtained 97.17% meaningful text coverage and 6,014,229 characters, with zero U+FFFD and null-byte corruption. Finally, 17 automated tests verified schema, provenance, metadata, determinism and frozen-source integrity."**

That is enough to demonstrate that you actually understand what the code is doing rather than just memorizing the report.
```
