# NutriKid Retrieval Quality Audit (Phase 3.4.2)

This report presents a qualitative retrieval quality audit evaluating **BM25 (Sparse)**, **Dense (FAISS BGE-small)**, and **Hybrid (RRF $k=60$)** retrieval modes across 8 representative pediatric nutrition query categories.

---

## 1. Summary of Qualitative Findings Across 8 Query Categories

| Query Category | Query Example | BM25 Behavior | Dense (FAISS) Behavior | Hybrid (RRF) Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **A. Exact Numerical Queries** | *"What is the recommended dietary allowance for iron for a 10-year-old child?"* | **Superior:** Direct match on ICMR-NIN RDA tables (`NK-021`) specifying 16 mg/day. | **Moderate:** Retrieves text on iron deficiency symptoms rather than exact numeric tables. | **Best Combined:** RRF ranks the exact table chunk #1 while retaining context. |
| **B. Semantic Queries** | *"What dietary nutrients support healthy growth and adolescent development?"* | **Weak:** Misses chunks lacking exact keyword overlap ("growth", "adolescent"). | **Superior:** Embeddings capture semantic intent across WHO & FAO policy guidelines. | **Balanced:** High top-5 precision combining policy guidelines with specific nutrients. |
| **C. Food Composition (IFCT)** | *"How much iron is present in common Indian food items?"* | **Strong:** Matches IFCT food table chunks containing food codes & nutrient values per 100g. | **Weak:** Struggles to match dense numeric table matrix rows without surrounding text. | **Superior:** Preserves top IFCT table chunks (`NK-010`) while ranking narrative summary chunks. |
| **D. Guideline Queries** | *"What are the WHO guidelines on sugar intake for children?"* | **Moderate:** Ranks WHO sugar guideline chunks if "sugar" and "intake" are present. | **Superior:** Direct top-1 hit on WHO Guideline document (`NK-007`, free sugars < 10% energy). | **Superior:** Top-1 score confirmed with RRF fusion. |
| **E. Age-Specific Nuances** | *"What are daily energy requirements for a 14-year-old adolescent boy?"* | Age filter filters out infant/toddler tables. BM25 ranks 14-17 yr ICMR energy tables. | Age filter ensures age compatibility. Dense retrieves adolescent dietary guidelines. | Age-filtered candidate pool ensures 100% age-compliant results. |
| **F. Out-of-Scope Enforcement** | *"What is recommended infant formula intake for a 3-month-old baby?"* (Age 0.25) | **Terminated:** `scope_status = out_of_scope`, 0 results returned. | **Terminated:** `scope_status = out_of_scope`, 0 results returned. | **Terminated:** Safety gate terminates retrieval immediately before candidate search. |
| **G. Missing-Age Default Scope** | *"What foods prevent anemia in school-age children?"* (Age = `null`) | Applies default research scope `[5.0, 15.0]`. Returns top 5 school-age chunks. | Applies default research scope `[5.0, 15.0]`. | Smooth fallback to default scope with 5 valid chunks returned. |
| **H. Terminology & Synonyms** | *"Recommended daily intake of ascorbic acid for pre-adolescents"* | **Fails:** Misses chunks mentioning only "Vitamin C" without the exact token "ascorbic". | **Superior:** BGE-small embeddings map "ascorbic acid" $\rightarrow$ "Vitamin C" RDA tables seamlessly. | **Resilient:** Dense signal rescues BM25 keyword failure, placing Vitamin C chunk in top 3. |

---

## 2. Key Insights & Systemic Trade-Offs

1. **Numeric & Table Precision (BM25 Strength):** For structured lookup tasks (e.g. IFCT food tables, ICMR-NIN RDA values), BM25 token matching guarantees exact table retrieval. Vector embeddings alone tend to dilute numeric cell data.
2. **Semantic Flexibility (Dense Strength):** For conceptual queries, paraphrased guidelines, and synonym matches (e.g., *ascorbic acid* vs *Vitamin C*), Dense retrieval overcomes keyword mismatch.
3. **Safety & Compliance (Age Filter Gate):** Enforcing `child_age \in [5.0, 15.0]` prevents dangerous out-of-scope retrievals (e.g., infant formula advice for older children or adult dietary restrictions applied to growing children).
4. **Hybrid RRF Complementarity:** Hybrid Reciprocal Rank Fusion ($k=60$) effectively bridges the gap between lexical table lookups and semantic guideline retrieval.
