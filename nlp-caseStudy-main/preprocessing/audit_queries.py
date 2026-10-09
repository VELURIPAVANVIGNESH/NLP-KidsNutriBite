import sys
import os
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.retrieve import run_retrieval

queries_to_test = [
    {
        "category_code": "A",
        "category_name": "Exact Numerical Query",
        "query": "What is the recommended dietary allowance for iron for a 10-year-old child?",
        "age": 10.0
    },
    {
        "category_code": "B",
        "category_name": "Semantic Query",
        "query": "What dietary nutrients support healthy growth and adolescent development?",
        "age": 12.0
    },
    {
        "category_code": "C",
        "category_name": "Food Composition Query (IFCT)",
        "query": "How much iron is present in common Indian food items?",
        "age": 8.0
    },
    {
        "category_code": "D",
        "category_name": "Guideline Query",
        "query": "What are the WHO guidelines on sugar intake for children?",
        "age": 9.0
    },
    {
        "category_code": "E",
        "category_name": "Age-Specific Query (14 yrs vs 5 yrs)",
        "query": "What are the daily energy requirements for a 14-year-old adolescent boy?",
        "age": 14.0
    },
    {
        "category_code": "F",
        "category_name": "Out-of-Scope Query (Age < 5)",
        "query": "What is the recommended infant formula intake for a 3-month-old baby?",
        "age": 0.25
    },
    {
        "category_code": "G",
        "category_name": "Missing-Age Query (Age=None)",
        "query": "What foods are recommended to prevent anemia in school-age children?",
        "age": None
    },
    {
        "category_code": "H",
        "category_name": "Terminology Variation / Synonyms",
        "query": "Recommended daily intake of ascorbic acid for pre-adolescents",
        "age": 11.0
    }
]

audit_results = []

for item in queries_to_test:
    q = item["query"]
    age = item["age"]
    cat_code = item["category_code"]
    cat_name = item["category_name"]
    
    modes_output = {}
    for mode in ["bm25", "dense", "hybrid"]:
        res = run_retrieval(query=q, child_age=age, mode=mode, top_k=5)
        modes_output[mode] = {
            "scope_status": res["scope_status"],
            "status": res["status"],
            "returned_count": len(res["results"]),
            "top_results": [
                {
                    "rank": r["rank"],
                    "chunk_id": r["chunk_id"],
                    "source_id": r["source_id"],
                    "source_name": r["source_name"],
                    "score": r["score"],
                    "age_min": r["age_min"],
                    "age_max": r["age_max"],
                    "text_snippet": r["text"][:150] + "..."
                }
                for r in res["results"]
            ]
        }
    
    audit_results.append({
        "category_code": cat_code,
        "category_name": cat_name,
        "query": q,
        "age": age,
        "modes": modes_output
    })

output_path = os.path.join(BASE_DIR, "data", "processed", "qualitative_retrieval_audit.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2, ensure_ascii=False)

print(f"[+] Qualitative retrieval audit completed across all 8 query categories. Saved to {output_path}")
