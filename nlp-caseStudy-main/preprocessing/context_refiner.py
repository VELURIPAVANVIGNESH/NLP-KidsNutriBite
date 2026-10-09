import os
import sys
import json
import re
import math

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def tokenize_for_similarity(text):
    """Clean and tokenize text into lowercase word tokens for Jaccard similarity."""
    if not text:
        return set()
    tokens = re.findall(r'\b\w+\b', text.lower())
    return set(tokens)

def compute_jaccard_similarity(text_a, text_b):
    """Computes Jaccard similarity between two text strings."""
    set_a = tokenize_for_similarity(text_a)
    set_b = tokenize_for_similarity(text_b)
    
    if not set_a or not set_b:
        return 0.0
        
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    
    return len(intersection) / float(len(union))

def refine_context(reranker_output, near_duplicate_threshold=0.85):
    """
    Deterministic Context Refinement Pipeline:
    1. Check scope status & empty evidence.
    2. Deduplicate exact chunk IDs.
    3. Detect & filter near-duplicate text chunks (Jaccard similarity > threshold).
    4. Preserve numerical values, RDA units, source provenance, and page numbers.
    5. Re-index rank order according to reranker score.
    6. Return clean structured context package for Phase 4 LLM generation.
    """
    query_text = reranker_output.get("query", "")
    child_age = reranker_output.get("requested_age", None)
    scope_status = reranker_output.get("scope_status", "in_scope")
    raw_results = reranker_output.get("results", [])
    query_id = reranker_output.get("query_id", "Q_CUSTOM")
    
    # Handle out of scope or empty input
    if scope_status == "out_of_scope" or not raw_results:
        return {
            "query_id": query_id,
            "query_text": query_text,
            "child_age": child_age,
            "scope_status": scope_status,
            "refinement_stats": {
                "raw_input_chunks": len(raw_results),
                "exact_duplicates_removed": 0,
                "near_duplicates_removed": 0,
                "final_evidence_chunks": 0
            },
            "evidence": []
        }
        
    seen_chunk_ids = set()
    exact_deduped_results = []
    exact_duplicates_count = 0
    
    # Step 1: Exact Chunk ID Deduplication
    for chunk in raw_results:
        cid = chunk.get("chunk_id")
        if cid in seen_chunk_ids:
            exact_duplicates_count += 1
            continue
        seen_chunk_ids.add(cid)
        exact_deduped_results.append(chunk)
        
    # Step 2: Near-Duplicate Text Detection & Filtering
    final_evidence_list = []
    near_duplicates_count = 0
    
    for candidate in exact_deduped_results:
        cand_text = candidate.get("text", "")
        is_near_dup = False
        
        for kept in final_evidence_list:
            kept_text = kept.get("text", "")
            sim = compute_jaccard_similarity(cand_text, kept_text)
            if sim >= near_duplicate_threshold:
                is_near_dup = True
                near_duplicates_count += 1
                break
                
        if not is_near_dup:
            final_evidence_list.append(candidate)
            
    # Step 3: Re-index rank order and clean metadata payload
    cleaned_evidence = []
    for idx, item in enumerate(final_evidence_list):
        cleaned_item = {
            "rank": idx + 1,
            "chunk_id": item.get("chunk_id"),
            "source_id": item.get("source_id"),
            "source_name": item.get("source_name"),
            "file_name": item.get("file_name"),
            "page_numbers": item.get("page_numbers"),
            "age_min": item.get("age_min"),
            "age_max": item.get("age_max"),
            "reranker_score": item.get("reranker_score", item.get("score")),
            "original_rank": item.get("original_rank", item.get("rank")),
            "context_prefix": item.get("context_prefix"),
            "text": item.get("text")
        }
        cleaned_evidence.append(cleaned_item)
        
    return {
        "query_id": query_id,
        "query_text": query_text,
        "child_age": child_age,
        "scope_status": scope_status,
        "refinement_stats": {
            "raw_input_chunks": len(raw_results),
            "exact_duplicates_removed": exact_duplicates_count,
            "near_duplicates_removed": near_duplicates_count,
            "final_evidence_chunks": len(cleaned_evidence)
        },
        "evidence": cleaned_evidence
    }

if __name__ == "__main__":
    # Quick CLI test
    sample_input = {
        "query": "What is the recommended dietary allowance for calcium for a 10-year-old child?",
        "requested_age": 10.0,
        "scope_status": "in_scope",
        "results": [
            {
                "rank": 1,
                "chunk_id": "NK-021-C00505",
                "source_id": "NK-021",
                "source_name": "Human Vitamin and Mineral Requirements",
                "file_name": "Human Vitamin .pdf",
                "page_numbers": [215, 216],
                "age_min": 10.0,
                "age_max": 12.0,
                "reranker_score": 3.142,
                "text": "Direct ICMR-NIN 2020 RDA table chunk specifying 850 mg/day calcium for children 10-12 yrs."
            },
            {
                "rank": 2,
                "chunk_id": "NK-021-C00505", # Exact duplicate chunk
                "source_id": "NK-021",
                "source_name": "Human Vitamin and Mineral Requirements",
                "file_name": "Human Vitamin .pdf",
                "page_numbers": [215, 216],
                "age_min": 10.0,
                "age_max": 12.0,
                "reranker_score": 3.142,
                "text": "Direct ICMR-NIN 2020 RDA table chunk specifying 850 mg/day calcium for children 10-12 yrs."
            }
        ]
    }
    refined = refine_context(sample_input)
    print(json.dumps(refined, indent=2, ensure_ascii=False))
