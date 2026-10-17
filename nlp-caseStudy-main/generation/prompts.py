import os
import sys

PEDIATRIC_NUTRITION_SYSTEM_PROMPT = """You are NutriKid, an evidence-grounded pediatric nutrition assistant.

Answer the user's question directly using ONLY the supplied evidence.

If the supplied evidence does NOT directly answer the question, or if the query is unrelated to the retrieved passages, respond ONLY with:
"Insufficient relevant evidence was retrieved."

Do not summarize unrelated evidence.

Give the relevant value when available, but ALWAYS explain what the value means in a complete sentence.

Never output a bare number or isolated value.

Do not copy unrelated text from the evidence.

Do not invent information.

Keep the answer concise: 1–3 complete sentences or short bullets."""

SYSTEM_PROMPT = PEDIATRIC_NUTRITION_SYSTEM_PROMPT

USER_QUERY_PROMPT_TEMPLATE = """### PEDIATRIC NUTRITION QUERY
Target Child Age: {child_age} years
User Query: {query_text}

### RETRIEVED EVIDENCE PASSAGES ({evidence_count} items):
{evidence_block}

### INSTRUCTIONS FOR RESPONSE GENERATION:
Provide a clear, structured, evidence-grounded response addressing the user's query. Include inline provenance citations for all clinical claims and nutrient figures.
"""

import re

def format_evidence_block(evidence_items):
    if not evidence_items:
        return "No evidence passages available."
    
    # Filter out pure boilerplate / reprint metadata
    clean_items = []
    for item in evidence_items:
        txt = item.get("text", "")
        if re.search(r'\b(request for reprints|e-mail:\s*<EMAIL>|editorial correspondence)\b', txt, re.I) and not re.search(r'\b(Table\s+\d+|RDA|EAR|g/d|mg/d|µg/d)\b', txt, re.I):
            continue
        clean_items.append(item)
    if not clean_items:
        clean_items = evidence_items

    formatted_blocks = []
    for idx, item in enumerate(clean_items[:2]):
        sid = item.get("source_id", "UNKNOWN")
        sname = item.get("source_name", item.get("file_name", "UNKNOWN"))
        pages = item.get("page_numbers", [])
        page_str = ", ".join(str(p) for p in pages) if pages else "N/A"
        text = item.get("text", "").strip()
        text = re.sub(r'E-mail:\s*<EMAIL>', '', text)
        text = re.sub(r'Request for reprints:.*', '', text)
        if len(text) > 350:
            text = text[:350] + "..."
        
        block = f"[{sid}: {sname}, p. {page_str}]\n{text}"
        formatted_blocks.append(block)
        
    return "\n\n".join(formatted_blocks)

