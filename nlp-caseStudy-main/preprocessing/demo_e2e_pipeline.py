import sys
import os
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from generation.generate import run_generation_pipeline

def main():
    print("=" * 70)
    print("      NUTRIKID PEDIATRIC NUTRITION RAG — END-TO-END DEMO")
    print("=" * 70)
    
    queries = [
        {
            "title": "DEMO 1: In-Scope RDA Query (Age 10)",
            "query": "What is the recommended dietary allowance for calcium for a 10-year-old child?",
            "child_age": 10.0
        },
        {
            "title": "DEMO 2: In-Scope Clinical Guideline Query (Age 7)",
            "query": "What foods are rich in iron and safe for school children?",
            "child_age": 7.0
        },
        {
            "title": "DEMO 3: Out-of-Scope Safety Gate Test (Age 3 - Underage Toddler)",
            "query": "What food should I give my 3-year-old toddler?",
            "child_age": 3.0
        }
    ]
    
    for q in queries:
        print(f"\n\n>>> {q['title']}")
        print(f"    Query: '{q['query']}'")
        print(f"    Target Child Age: {q['child_age']} years")
        print("-" * 70)
        
        res = run_generation_pipeline(query=q["query"], child_age=q["child_age"])
        
        print(f"[*] Scope Status       : {res['scope_status']}")
        print(f"[*] Pipeline Status    : {res['status']}")
        print(f"[*] Evidence Items Used: {res['evidence_used_count']}")
        print("\n--- SYNTHESIZED RESPONSE & CITATIONS ---")
        print(res["answer"])
        print("=" * 70)

if __name__ == "__main__":
    main()
