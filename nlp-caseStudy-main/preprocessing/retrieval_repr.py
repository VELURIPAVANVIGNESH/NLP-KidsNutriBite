"""
preprocessing/retrieval_repr.py — Shared retrieval text representation builder.

Generates an enriched indexing/scoring text for a corpus chunk that includes:
- Source provenance (publisher, year, source name)
- Domain label
- Page numbers
- Detected table titles
- Expanded age-group tokens (e.g. "10-12y" -> "10, 11, 12 year old child/children")
- Acronym expansions (RDA, EAR)
- Original context_prefix and text

Used by BOTH the preprocessor (BM25/Dense indexing) and the reranker (cross-encoder
input text) so that structured table chunks receive the same rich representation
throughout the entire retrieval pipeline.

The stored `text` and `context_prefix` fields on the chunk are never modified.
"""

import re


def generate_retrieval_text(chunk: dict) -> str:
    """
    Build a retrieval-only text representation for a corpus chunk.

    Enriches the raw text with structured metadata headers so that tabular
    chunks (e.g. RDA tables) are lexically and semantically competitive with
    prose-heavy chunks for nutrition queries.

    Args:
        chunk: A preprocessed corpus chunk dict with fields:
               text, context_prefix, publisher, source_name, publication_year,
               domain, page_numbers.

    Returns:
        A single string: metadata header block + blank line + original text.
    """
    text   = chunk.get("text", "")
    prefix = chunk.get("context_prefix", "")
    meta_headers: list[str] = []

    # 1. Source provenance line
    pub   = chunk.get("publisher", "")
    sn    = chunk.get("source_name", "")
    yr    = chunk.get("publication_year", "")
    dom   = chunk.get("domain", "")
    pages = chunk.get("page_numbers", [])

    src_line = f"Source: {pub} ({yr}) - {sn}".strip() if (pub or sn) else ""
    if src_line:
        meta_headers.append(src_line)
    if dom:
        meta_headers.append(f"Domain: {dom}")
    if pages:
        meta_headers.append(f"Pages: {', '.join(str(p) for p in pages)}")
    if prefix:
        meta_headers.append(prefix)

    # 2. Structured table title detection
    tbl_titles = re.findall(r"(Table\s+[\w\d]+[.:\s][^\n]+)", text, re.I)
    if tbl_titles:
        meta_headers.append("Tables: " + " | ".join(t.strip() for t in tbl_titles[:3]))

    # 3. Age-group token expansion (e.g. "10-12y" -> "10, 11, 12 year old child/children")
    age_matches = re.findall(r"\b(\d+)\s*[-\u2013]\s*(\d+)\s*y(?:ears?)?\b", text, re.I)
    if age_matches:
        expanded = []
        for low_s, high_s in age_matches[:6]:
            low, high = int(low_s), int(high_s)
            expanded.append(
                f"{low}-{high} years "
                f"({', '.join(str(a) for a in range(low, high + 1))} year old child/children)"
            )
        meta_headers.append("Age groups: " + "; ".join(expanded))

    # 4. Acronym and clinical unit expansions for terms present in the chunk text
    expansions = []
    if re.search(r"\bRDA\b", text):
        expansions.append("Recommended Dietary Allowance (RDA)")
    if re.search(r"\bEAR\b", text):
        expansions.append("Estimated Average Requirement (EAR)")
    if re.search(r"\bg/d\b|\bg/day\b", text, re.I):
        expansions.append("grams per day (g/day)")
    if re.search(r"\bmg/d\b|\bmg/day\b", text, re.I):
        expansions.append("milligrams per day (mg/day)")
    if re.search(r"\bµg/d\b|\bµg/day\b|\bug/d\b", text, re.I):
        expansions.append("micrograms per day (µg/day)")
    if re.search(r"\brequirements?\b", text, re.I):
        expansions.append("daily requirement, daily need, dietary intake")
    if re.search(r"\bchildren\b", text, re.I) and not re.search(r"\bchild\b", text, re.I):
        expansions.append("child")
    if expansions:
        meta_headers.append("Terminology: " + "; ".join(expansions))

    header_block = "\n".join(meta_headers)
    return (header_block + "\n\n" + text).strip()
