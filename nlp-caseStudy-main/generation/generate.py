import os
import sys
import json
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.rerank import run_reranking
from preprocessing.context_refiner import refine_context
from generation.prompts import PEDIATRIC_NUTRITION_SYSTEM_PROMPT, USER_QUERY_PROMPT_TEMPLATE, format_evidence_block

def synthesize_response_from_evidence(query, child_age, refined_package):
    """
    Deterministic synthesis engine:
    1. Checks age scope safety.
    2. Checks evidence availability.
    3. Synthesizes structured, evidence-grounded response with inline provenance citations.
    """
    scope_status = refined_package.get("scope_status", "in_scope")
    evidence_items = refined_package.get("evidence", [])
    
    # Gate 1: Out of Scope Safety Refusal
    if scope_status == "out_of_scope" or (child_age is not None and (child_age < 5.0 or child_age > 15.0)):
        return {
            "query": query,
            "child_age": child_age,
            "scope_status": "out_of_scope",
            "status": "terminated_out_of_scope",
            "answer": f"Out of Scope Notice: The target child age ({child_age} years) falls outside the NutriKid research scope (5.0 to 15.0 years). Please consult specialized guidelines for infants or adults.",
            "citations": [],
            "evidence_used_count": 0
        }
        
    # Gate 2: Insufficient Evidence Handling
    if not evidence_items:
        return {
            "query": query,
            "child_age": child_age,
            "scope_status": scope_status,
            "status": "insufficient_evidence",
            "answer": "Insufficient Evidence Notice: The retrieved knowledge corpus contains insufficient evidence to answer this specific pediatric nutrition query.",
            "citations": [],
            "evidence_used_count": 0
        }
        
    # Construct structured grounded synthesis
    response_paragraphs = []
    citations = []
    
    for idx, item in enumerate(evidence_items):
        sid = item.get("source_id", "")
        sname = item.get("source_name", "")
        fname = item.get("file_name", "")
        pages = item.get("page_numbers", [])
        page_str = ", ".join(str(p) for p in pages) if pages else "N/A"
        text = item.get("text", "")
        prefix = item.get("context_prefix", "")
        
        citation_str = f"[{sid}: {fname}, p. {page_str}]"
        citations.append({
            "source_id": sid,
            "source_name": sname,
            "file_name": fname,
            "page_numbers": pages,
            "citation_label": citation_str
        })
        
        # Format paragraph incorporating key evidence text
        para_header = f"According to official guidance from {sname} {citation_str}:"
        if prefix:
            para_body = f"{prefix}\n{text}"
        else:
            para_body = text
            
        response_paragraphs.append(f"{para_header}\n{para_body}")
        
    full_answer = f"Based on the authoritative pediatric nutrition evidence from official WHO and ICMR-NIN guidelines:\n\n" + "\n\n".join(response_paragraphs)
    
    return {
        "query": query,
        "child_age": child_age,
        "scope_status": scope_status,
        "status": "success",
        "answer": full_answer,
        "citations": citations,
        "evidence_used_count": len(evidence_items)
    }

def run_generation_pipeline(query, child_age, candidate_k=50, top_k=5, config_path="preprocessing/config.json"):
    """
    Full End-to-End Generation Pipeline:
    Phase 3.4 Retrieval -> Phase 3.5 Reranking -> Phase 3.5 Context Refinement -> Phase 4 Synthesis
    """
    # 1. Run Phase 3.5 Cross-Encoder Reranking
    rerank_out = run_reranking(
        query=query,
        child_age=child_age,
        reranker_model_name="BAAI/bge-reranker-base",
        candidate_k=candidate_k,
        top_k=top_k,
        config_path=config_path
    )
    
    # 2. Run Phase 3.5 Context Refinement
    refined_package = refine_context(rerank_out)
    
    # 3. Run Phase 4 Synthesis Engine
    synthesis_res = synthesize_response_from_evidence(query, child_age, refined_package)
    
    return synthesis_res

if __name__ == "__main__":
    test_query = "What is the recommended daily calcium allowance for a 10-year-old child?"
    res = run_generation_pipeline(query=test_query, child_age=10.0)
    print(json.dumps(res, indent=2, ensure_ascii=False))
