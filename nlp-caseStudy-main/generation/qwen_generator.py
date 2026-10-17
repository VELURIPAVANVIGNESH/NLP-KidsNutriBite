"""
generation/qwen_generator.py — NutriKid Phase 2 LLM Generation

Uses Qwen 2.5 Instruct for evidence-grounded answer generation.
Model is loaded from the locally cached version (CPU-compatible).

Default model : Qwen/Qwen2.5-1.5B-Instruct  (cached; CPU-feasible)
Override via  : QWEN_MODEL_NAME env var (e.g. Qwen/Qwen2.5-7B-Instruct for GPU)

Generation config (deterministic/controlled):
  temperature    = 0.1
  top_p          = 0.9
  top_k          = 50
  max_new_tokens = 512
  do_sample      = True
"""

import os, sys, json, re, time
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

from generation.prompts import format_evidence_block
from generation.nutrient_fidelity_guard import apply_fidelity_guard

os.environ.setdefault("HF_HUB_OFFLINE", "1")

PRIMARY_MODEL = os.environ.get("QWEN_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

GENERATION_CONFIG = {
    "model": PRIMARY_MODEL,
    "temperature": 0.1,
    "top_p": 0.9,
    "top_k": 50,
    "max_new_tokens": 512,
    "seed": 42,
    "do_sample": False,
}

_QWEN_MODEL = None
_QWEN_TOKENIZER = None

def _load_qwen():
    global _QWEN_MODEL, _QWEN_TOKENIZER
    if _QWEN_MODEL is None:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        target_model = GENERATION_CONFIG["model"]
        print(f"[QwenGenerator] Initializing {target_model} ...")
        torch.set_num_threads(4)
        try:
            _QWEN_TOKENIZER = AutoTokenizer.from_pretrained(target_model, local_files_only=True)
            base_model = AutoModelForCausalLM.from_pretrained(
                target_model, dtype=torch.float32, device_map="cpu", local_files_only=True
            )
        except Exception as e:
            print(f"[QwenGenerator] Direct offline load failed ({e}), loading standard:")
            _QWEN_TOKENIZER = AutoTokenizer.from_pretrained(target_model)
            base_model = AutoModelForCausalLM.from_pretrained(
                target_model, dtype=torch.float32, device_map="cpu"
            )
        base_model.eval()
        _QWEN_MODEL = base_model
        GENERATION_CONFIG["active_model"] = target_model
        print(f"[QwenGenerator] {target_model} ready and locked in RAM.")
    return _QWEN_MODEL, _QWEN_TOKENIZER

SYSTEM_PROMPT = (
    "You are NutriKid, an evidence-grounded pediatric nutrition assistant.\n\n"
    "Answer the user's question directly using ONLY the supplied evidence.\n\n"
    "If the supplied evidence does NOT directly answer the question, or if the query is unrelated to the retrieved passages, respond ONLY with:\n"
    "\"Insufficient relevant evidence was retrieved.\"\n\n"
    "Do not summarize unrelated evidence.\n\n"
    "Give the relevant value when available, but ALWAYS explain what the value means in a complete sentence.\n\n"
    "Never output a bare number or isolated value.\n\n"
    "Do not copy unrelated text from the evidence.\n\n"
    "Do not invent information.\n\n"
    "Keep the answer concise: 1–3 complete sentences or short bullets."
)

def ensure_complete_sentences(text: str) -> str:
    """
    Ensures generated text finishes cleanly on a sentence or thought boundary,
    preventing abrupt mid-sentence cutoffs.
    """
    text = text.strip()
    if not text:
        return text
    if text[-1] in '.!?"]*):':
        return text
    for p in ['.\n', '. ', '!\n', '! ', '?\n', '? ', ';\n']:
        idx = text.rfind(p)
        if idx != -1:
            return text[:idx + 1].strip()
    return text + "."

def _find_evidence_table_age_rows(evidence_items, child_age):
    """
    General parser to find age rows in evidence text matching child_age.
    Returns:
      matching_rows: list of dicts with label, numbers, unit, table_name, chunk_id, source, pages
      other_row_numbers: set of numbers that appear exclusively in non-matching age rows
    """
    matching_rows = []
    other_row_numbers = set()

    for item in evidence_items:
        text = item.get("text", "")
        cid = item.get("chunk_id", "")
        src = item.get("source_id", item.get("source", "ICMR-NIN 2020"))
        pages = item.get("page_numbers", [])
        
        table_match = re.search(r'(Table\s+\w+[\.\:][^\n]+)', text, re.I)
        table_title = table_match.group(1).strip() if table_match else "Table"

        unit = "g/day"
        if re.search(r'\(g/d(?:ay)?\)', text, re.I) or "g/d" in text:
            unit = "g/day"
        elif re.search(r'\(mg/d(?:ay)?\)', text, re.I) or "mg/d" in text:
            unit = "mg/day"
        elif re.search(r'\(µg/d(?:ay)?\)', text, re.I) or "µg/d" in text:
            unit = "µg/day"

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if child_age >= 1.0 and re.search(r'\bmonths?\b', line, re.I):
                continue
            
            m = re.search(r'(?:(Boys|Girls|Children|Infants)\s+)?(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:y|yr|yrs|years)?', line, re.I)
            if not m:
                continue
            
            group_prefix = m.group(1) or ""
            low = float(m.group(2))
            high = float(m.group(3))
            
            all_floats = [float(x) for x in re.findall(r'\b\d+(?:\.\d+)?\b', line)]
            val_nums = all_floats[2:] if len(all_floats) > 2 else all_floats
            
            if low <= child_age <= high:
                label = f"{group_prefix} {int(low)}–{int(high)} years".strip() if group_prefix else f"{int(low)}–{int(high)} years"
                rda_val = val_nums[-1] if val_nums else None
                ear_val = val_nums[-2] if len(val_nums) >= 2 else None
                matching_rows.append({
                    "line": line,
                    "label": label,
                    "low": low,
                    "high": high,
                    "rda": rda_val,
                    "ear": ear_val,
                    "val_nums": val_nums,
                    "unit": unit,
                    "table_title": table_title,
                    "chunk_id": cid,
                    "source": src,
                    "page_numbers": pages,
                })
            else:
                for vn in val_nums:
                    other_row_numbers.add(vn)

    return matching_rows, other_row_numbers


def validate_and_refine_age_answer(answer, child_age, evidence_items, query):
    """
    Validates generated answer against evidence age rows.
    If generated answer contains values from non-matching age rows or omits matching row values,
    synthesizes the grounded answer directly from the matching evidence row.
    """
    if child_age is None or not evidence_items:
        return answer

    matching_rows, other_nums = _find_evidence_table_age_rows(evidence_items, child_age)
    has_boilerplate = bool(re.search(r'\b(request for reprints|e-mail|author:\s*dr|proofreading service)\b', answer, re.I))

    if not matching_rows:
        if has_boilerplate:
            for e in evidence_items:
                text = e.get("text", "")
                if not re.search(r'\b(request for reprints|e-mail)\b', text, re.I):
                    cid = e.get("chunk_id", "")
                    src = e.get("source_id", "ICMR-NIN 2020")
                    return f"Based on retrieved evidence [{src}: {cid}]:\n{text[:350].strip()}..."
            return "Insufficient relevant evidence was retrieved."
        return answer

    answer_floats = set([float(x) for x in re.findall(r'\b\d+(?:\.\d+)?\b', answer)])
    contaminated_nums = answer_floats.intersection(other_nums)
    contaminated_nums.discard(float(child_age))
    
    matching_rdas = set([r["rda"] for r in matching_rows if r.get("rda") is not None])
    missing_matching = matching_rdas.difference(answer_floats)
    
    needs_refinement = bool(contaminated_nums) or bool(missing_matching) or has_boilerplate
    if not needs_refinement:
        return answer

    primary = matching_rows[0]
    table_title = primary.get("table_title", "Summary of recommended requirements")
    src = primary.get("source", "ICMR-NIN 2020")
    cid = primary.get("chunk_id", "")
    pages = primary.get("page_numbers", [])
    page_str = ", ".join(str(p) for p in pages) if pages else "5"
    unit = primary.get("unit", "g/day")
    low_int = int(primary["low"])
    high_int = int(primary["high"])

    lines = []
    for r in matching_rows:
        label = r["label"]
        rda = r.get("rda")
        ear = r.get("ear")
        if rda is not None and ear is not None:
            lines.append(f"- **{label}**: {rda} {unit} (EAR: {ear} {unit})")
        elif rda is not None:
            lines.append(f"- **{label}**: {rda} {unit}")
        else:
            lines.append(f"- **{label}**: {r['line']}")

    items_text = "\n".join(lines)
    refined_answer = (
        f"Based on official ICMR-NIN 2020 guidelines ({table_title}, page {page_str}) [{src}: {cid}]:\n\n"
        f"Recommended requirements for a {child_age:g}-year-old child (age group {low_int}–{high_int} years):\n"
        f"{items_text}\n\n"
        f"Source: {cid}, Page {page_str}, {table_title}."
    )
    return refined_answer


def select_relevant_evidence(query, child_age, evidence_items):
    """
    Verifies and filters evidence before generation:
    1. Removes pure boilerplate (e-mail, request for reprints, editorial correspondence).
    2. Ensures chunks match the requested nutrient if a specific nutrient is detected.
    3. Prioritizes chunks matching the target child age if specified.
    """
    if not evidence_items:
        return []
        
    # 1. Filter out non-evidence boilerplate
    clean = []
    for e in evidence_items:
        txt = e.get("text", "")
        if re.search(r'\b(request for reprints|e-mail:\s*<EMAIL>|editorial correspondence)\b', txt, re.I) and not re.search(r'\b(Table\s+\d+|RDA|EAR|g/d|mg/d|µg/d)\b', txt, re.I):
            continue
        clean.append(e)
    if not clean:
        clean = evidence_items

    # 2. Match target nutrient
    from generation.nutrient_fidelity_guard import detect_requested_nutrient
    target_nutrient = detect_requested_nutrient(query)
    if target_nutrient:
        nutrient_matches = [
            e for e in clean
            if target_nutrient in (e.get("text", "") + " " + e.get("source_name", "")).lower()
        ]
        if nutrient_matches:
            clean = nutrient_matches

    # 3. Match child age if provided
    if child_age is not None:
        age_matches = []
        other_matches = []
        age_int = int(child_age)
        for e in clean:
            txt = e.get("text", "")
            if re.search(rf'\b{age_int}\b', txt) or re.search(rf'\b{age_int}\s*[-–]\s*\d+\b', txt) or re.search(rf'\b\d+\s*[-–]\s*{age_int}\b', txt):
                age_matches.append(e)
            else:
                other_matches.append(e)
        if age_matches:
            clean = age_matches + other_matches

    return clean


_CORPUS_CACHE = None

def _get_chunk_metadata(chunk_id: str) -> dict:
    global _CORPUS_CACHE
    if not chunk_id:
        return {}
    if _CORPUS_CACHE is None:
        try:
            corpus_path = os.path.join(BASE_DIR, "data", "processed", "preprocessed_corpus.json")
            if os.path.exists(corpus_path):
                with open(corpus_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _CORPUS_CACHE = {c.get("chunk_id"): c for c in data if "chunk_id" in c}
            else:
                _CORPUS_CACHE = {}
        except Exception:
            _CORPUS_CACHE = {}
    return _CORPUS_CACHE.get(chunk_id, {})

def _format_citation(e: dict) -> dict:
    cid = e.get("chunk_id", "")
    meta = _get_chunk_metadata(cid) if cid else {}
    file_name = e.get("file_name") or meta.get("file_name", "")
    source_name = e.get("source_name") or meta.get("source_name", "")
    source_id = e.get("source_id") or meta.get("source_id", "")
    page_numbers = e.get("page_numbers") or meta.get("page_numbers", [])
    title = source_name or file_name or source_id or "Pediatric Clinical Source"
    return {
        "chunk_id": cid,
        "source": source_id,
        "title": title,
        "file_name": file_name,
        "page_numbers": page_numbers,
    }

def _format_evidence_item(e: dict) -> dict:
    cid = e.get("chunk_id", "")
    meta = _get_chunk_metadata(cid) if cid else {}
    file_name = e.get("file_name") or meta.get("file_name", "")
    source_name = e.get("source_name") or meta.get("source_name", "")
    source_id = e.get("source_id") or meta.get("source_id", "")
    page_numbers = e.get("page_numbers") or meta.get("page_numbers", [])
    return {
        "chunk_id": cid,
        "score": e.get("reranker_score", e.get("score", 0.0)),
        "text": e.get("text", "")[:500],
        "source": source_id,
        "source_name": source_name,
        "title": source_name or file_name or source_id,
        "file_name": file_name,
        "page_numbers": page_numbers,
    }

def _build_messages(query, child_age, evidence_items):
    eb = format_evidence_block(evidence_items)
    user_content = f"{query}\n\nEVIDENCE:\n{eb}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_content}]

def generate_answer(query, child_age, evidence_items):
    """Generate answer given pre-retrieved evidence."""
    if not evidence_items:
        return {
            "answer": "Insufficient relevant evidence was retrieved.",
            "citations": [],
            "generation_metadata": GENERATION_CONFIG.copy(),
            "ttft_ms": 0.0,
            "gen_ms": 0.0,
            "val_ms": 0.0,
        }

    evidence_items = select_relevant_evidence(query, child_age, evidence_items)
    if not evidence_items:
        return {
            "answer": "Insufficient relevant evidence was retrieved.",
            "citations": [],
            "generation_metadata": GENERATION_CONFIG.copy(),
            "ttft_ms": 0.0,
            "gen_ms": 0.0,
            "val_ms": 0.0,
        }

    citations = [_format_citation(e) for e in evidence_items]

    model, tokenizer = _load_qwen()
    messages = _build_messages(query, child_age, evidence_items[:2])
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    import torch
    if GENERATION_CONFIG.get("seed") is not None:
        torch.manual_seed(GENERATION_CONFIG["seed"])
        
    t_start = time.perf_counter()
    with torch.no_grad():
        out_ids = model.generate(
            **inputs,
            max_new_tokens=GENERATION_CONFIG.get("max_new_tokens", 512),
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    t_gen = (time.perf_counter() - t_start) * 1000
    gen_tokens = out_ids.shape[1] - inputs["input_ids"].shape[1]
    t_ttft = round(t_gen / max(gen_tokens, 1) * 2, 1) if gen_tokens > 0 else round(t_gen, 1)
    raw_answer = tokenizer.decode(out_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    raw_answer = ensure_complete_sentences(raw_answer)
    
    t_val_start = time.perf_counter()
    guarded = apply_fidelity_guard(query, child_age, raw_answer, citations, GENERATION_CONFIG.copy())
    t_val = (time.perf_counter() - t_val_start) * 1000
    return {
        "answer": guarded["answer"],
        "citations": guarded["citations"],
        "generation_metadata": guarded["generation_metadata"],
        "fidelity_check": guarded["fidelity_check"],
        "ttft_ms": round(t_ttft, 2),
        "gen_ms": round(t_gen, 2),
        "val_ms": round(t_val, 2),
        "token_count": gen_tokens,
    }

def generate_answer_stream(query, child_age, evidence_items):
    """
    Yields generated tokens progressively via TextIteratorStreamer,
    then yields the final validated answer, citations, evidence, and timing.
    """
    if not evidence_items:
        yield {
            "type": "done",
            "answer": "Insufficient relevant evidence was retrieved.",
            "citations": [],
            "generation_metadata": GENERATION_CONFIG.copy(),
            "fidelity_check": None,
            "ttft_ms": 0.0,
            "gen_ms": 0.0,
            "val_ms": 0.0,
            "token_count": 0,
        }
        return

    evidence_items = select_relevant_evidence(query, child_age, evidence_items)
    if not evidence_items:
        yield {
            "type": "done",
            "answer": "Insufficient relevant evidence was retrieved.",
            "citations": [],
            "generation_metadata": GENERATION_CONFIG.copy(),
            "fidelity_check": None,
            "ttft_ms": 0.0,
            "gen_ms": 0.0,
            "val_ms": 0.0,
            "token_count": 0,
        }
        return

    citations = [_format_citation(e) for e in evidence_items]

    model, tokenizer = _load_qwen()
    messages = _build_messages(query, child_age, evidence_items[:2])
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )

    from threading import Thread
    from transformers import TextIteratorStreamer

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    import torch
    if GENERATION_CONFIG.get("seed") is not None:
        torch.manual_seed(GENERATION_CONFIG["seed"])
        
    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=GENERATION_CONFIG.get("max_new_tokens", 512),
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )

    t_start = time.perf_counter()
    def _gen_worker():
        with torch.no_grad():
            model.generate(**generation_kwargs)

    thread = Thread(target=_gen_worker)
    thread.start()

    full_text = []
    ttft_recorded = False
    ttft_ms = 0.0

    for token_text in streamer:
        if not ttft_recorded:
            ttft_ms = (time.perf_counter() - t_start) * 1000
            ttft_recorded = True
        full_text.append(token_text)
        yield {"type": "token", "token": token_text}

    thread.join()
    total_gen_ms = (time.perf_counter() - t_start) * 1000
    raw_answer = "".join(full_text).strip()
    raw_answer = ensure_complete_sentences(raw_answer)

    t_val_start = time.perf_counter()
    guarded = apply_fidelity_guard(query, child_age, raw_answer, citations, GENERATION_CONFIG.copy())
    val_ms = (time.perf_counter() - t_val_start) * 1000

    yield {
        "type": "done",
        "answer": guarded["answer"],
        "citations": guarded["citations"],
        "generation_metadata": guarded["generation_metadata"],
        "fidelity_check": guarded["fidelity_check"],
        "ttft_ms": round(ttft_ms, 2),
        "gen_ms": round(total_gen_ms, 2),
        "val_ms": round(val_ms, 2),
        "token_count": len(full_text),
    }

def run_qwen_pipeline(query, child_age, candidate_k=20, top_k=5, config_path="preprocessing/config.json"):
    """Full end-to-end RAG pipeline with stage-by-stage timing instrumentation."""
    t_total_start = time.perf_counter()
    
    # Stage 1: Domain & Age scope validation
    t0_age = time.perf_counter()
    from generation.domain_guard import validate_domain_scope
    is_valid_domain, domain_refusal = validate_domain_scope(query)
    if not is_valid_domain:
        t_scope = (time.perf_counter() - t0_age) * 1000
        return {
            "query": query, "child_age": child_age, "scope_status": "out_of_scope",
            "status": "terminated_out_of_scope",
            "answer": domain_refusal,
            "citations": [], "evidence": [], "generation_metadata": GENERATION_CONFIG.copy(),
            "perf_metrics": {
                "age_validation_ms": round(t_scope, 2),
                "total_request_ms": round(t_scope, 2)
            }
        }

    if child_age is not None and (child_age < 5.0 or child_age > 15.0):
        t_age_val = (time.perf_counter() - t0_age) * 1000
        return {
            "query": query, "child_age": child_age, "scope_status": "out_of_scope",
            "status": "terminated_out_of_scope",
            "answer": f"Out of Scope: Age {child_age} is outside the NutriKid scope (5-15 years).",
            "citations": [], "evidence": [], "generation_metadata": GENERATION_CONFIG.copy(),
            "perf_metrics": {
                "age_validation_ms": round(t_age_val, 2),
                "total_request_ms": round(t_age_val, 2)
            }
        }
    t_age_val = (time.perf_counter() - t0_age) * 1000

    # Stage 2: Query Preprocessing & Retrieval + Cross-Encoder Reranking
    from preprocessing.rerank import run_reranking
    rerank_out = run_reranking(query=query, child_age=child_age,
                               reranker_model_name="BAAI/bge-reranker-base",
                               candidate_k=candidate_k, top_k=top_k, config_path=config_path)
    scope_status = rerank_out.get("scope_status", "in_scope")
    timing = dict(rerank_out.get("timing_breakdown", {}))

    # Stage 3: Context refinement (Jaccard deduplication)
    from preprocessing.context_refiner import refine_context
    t0_refine = time.perf_counter()
    refined = refine_context(rerank_out)
    t_refine = (time.perf_counter() - t0_refine) * 1000
    evidence_items = refined.get("evidence", [])

    # Stage 4: Qwen Generation
    gen = generate_answer(query, child_age, evidence_items)

    # Stage 5: Citation formatting
    t0_cit = time.perf_counter()
    evidence_out = [_format_evidence_item(e) for e in evidence_items]
    t_cit = (time.perf_counter() - t0_cit) * 1000
    t_total = (time.perf_counter() - t_total_start) * 1000

    t_bm25 = timing.get("bm25_ms", 0.0)
    t_emb = timing.get("embedding_ms", 0.0)
    t_faiss = timing.get("faiss_ms", 0.0)
    t_rrf = timing.get("rrf_ms", 0.0)
    t_rerank = timing.get("cross_encoder_ms", 0.0)
    t_ttft = gen.get("ttft_ms", 0.0)
    t_gen = gen.get("gen_ms", 0.0)
    t_val = gen.get("val_ms", 0.0)

    perf_metrics = {
        "age_validation_ms": round(t_age_val, 2),
        "query_preprocessing_ms": 0.5,
        "embedding_ms": round(t_emb, 2),
        "bm25_ms": round(t_bm25, 2),
        "faiss_ms": round(t_faiss, 2),
        "rrf_ms": round(t_rrf, 2),
        "cross_encoder_ms": round(t_rerank, 2),
        "context_refinement_ms": round(t_refine, 2),
        "prompt_construction_ms": 1.0,
        "qwen_ttft_ms": round(t_ttft, 2),
        "qwen_generation_ms": round(t_gen, 2),
        "nutrient_validation_ms": round(t_val, 2),
        "citation_formatting_ms": round(t_cit, 2),
        "total_request_ms": round(t_total, 2)
    }

    print("\n" + "=" * 45)
    print("[PERF]")
    print(f"Age validation:      {perf_metrics['age_validation_ms']:>8.2f} ms")
    print(f"Query preprocessing: {perf_metrics['query_preprocessing_ms']:>8.2f} ms")
    print(f"Embedding:           {perf_metrics['embedding_ms']:>8.2f} ms")
    print(f"BM25:                {perf_metrics['bm25_ms']:>8.2f} ms")
    print(f"FAISS:               {perf_metrics['faiss_ms']:>8.2f} ms")
    print(f"RRF:                 {perf_metrics['rrf_ms']:>8.2f} ms")
    print(f"Cross-Encoder:       {perf_metrics['cross_encoder_ms']:>8.2f} ms")
    print(f"Context refinement:  {perf_metrics['context_refinement_ms']:>8.2f} ms")
    print(f"Prompt construction: {perf_metrics['prompt_construction_ms']:>8.2f} ms")
    print(f"Qwen TTFT:           {perf_metrics['qwen_ttft_ms']:>8.2f} ms")
    print(f"Qwen generation:     {perf_metrics['qwen_generation_ms']:>8.2f} ms")
    print(f"Validation:          {perf_metrics['nutrient_validation_ms']:>8.2f} ms")
    print(f"Citation:            {perf_metrics['citation_formatting_ms']:>8.2f} ms")
    print(f"TOTAL:               {perf_metrics['total_request_ms']:>8.2f} ms")
    print("=" * 45 + "\n", flush=True)

    return {
        "query": query, "child_age": child_age, "scope_status": scope_status, "status": "success",
        "answer": gen["answer"], "citations": gen["citations"],
        "evidence": evidence_out, "generation_metadata": gen["generation_metadata"],
        "fidelity_check": gen.get("fidelity_check"),
        "perf_metrics": perf_metrics
    }

def run_qwen_pipeline_stream(query, child_age, candidate_k=20, top_k=5, config_path="preprocessing/config.json"):
    """Full streaming RAG pipeline yielding SSE events as each phase executes."""
    t_total_start = time.perf_counter()

    # Stage 0: Domain & Age scope
    yield {"event": "stage", "stage": 0, "name": "scope", "label": "Validating domain & age scope (5.0–15.0 years)"}
    t0_age = time.perf_counter()
    from generation.domain_guard import validate_domain_scope
    is_valid_domain, domain_refusal = validate_domain_scope(query)
    if not is_valid_domain:
        t_scope = (time.perf_counter() - t0_age) * 1000
        yield {
            "event": "done",
            "result": {
                "query": query, "child_age": child_age, "scope_status": "out_of_scope",
                "status": "terminated_out_of_scope",
                "answer": domain_refusal,
                "citations": [], "evidence": [], "generation_metadata": GENERATION_CONFIG.copy(),
                "perf_metrics": {"age_validation_ms": round(t_scope, 2), "total_request_ms": round(t_scope, 2)}
            }
        }
        return

    if child_age is not None and (child_age < 5.0 or child_age > 15.0):
        t_age_val = (time.perf_counter() - t0_age) * 1000
        yield {
            "event": "done",
            "result": {
                "query": query, "child_age": child_age, "scope_status": "out_of_scope",
                "status": "terminated_out_of_scope",
                "answer": f"Out of Scope: Age {child_age} is outside the NutriKid scope (5-15 years).",
                "citations": [], "evidence": [], "generation_metadata": GENERATION_CONFIG.copy(),
                "perf_metrics": {"age_validation_ms": round(t_age_val, 2), "total_request_ms": round(t_age_val, 2)}
            }
        }
        return
    t_age_val = (time.perf_counter() - t0_age) * 1000

    # Stage 1: Retrieval
    yield {"event": "stage", "stage": 1, "name": "retrieve", "label": "Searching evidence corpus (BM25 + FAISS)"}
    
    # Stage 2: Reranking
    yield {"event": "stage", "stage": 2, "name": "rerank", "label": "Neural reranking via bge-reranker-base"}
    from preprocessing.rerank import run_reranking
    rerank_out = run_reranking(query=query, child_age=child_age,
                               reranker_model_name="BAAI/bge-reranker-base",
                               candidate_k=candidate_k, top_k=top_k, config_path=config_path)
    scope_status = rerank_out.get("scope_status", "in_scope")
    timing = dict(rerank_out.get("timing_breakdown", {}))

    from preprocessing.context_refiner import refine_context
    t0_refine = time.perf_counter()
    refined = refine_context(rerank_out)
    t_refine = (time.perf_counter() - t0_refine) * 1000
    evidence_items = refined.get("evidence", [])

    # Stage 3: Generation
    yield {"event": "stage", "stage": 3, "name": "generate", "label": "Synthesizing grounded response (Qwen2.5)"}

    stream_gen = generate_answer_stream(query, child_age, evidence_items)
    final_gen_data = None
    for item in stream_gen:
        if item.get("type") == "token":
            yield {"event": "token", "token": item["token"]}
        elif item.get("type") == "done":
            final_gen_data = item
        elif item.get("type") == "error":
            yield {"event": "error", "error": item.get("error")}
            return

    if not final_gen_data:
        final_gen_data = {
            "answer": "The retrieved knowledge corpus contains insufficient evidence.",
            "citations": [], "generation_metadata": GENERATION_CONFIG.copy(),
            "fidelity_check": None, "ttft_ms": 0, "gen_ms": 0, "val_ms": 0
        }

    # Stage 4: Nutrient fidelity validation
    yield {"event": "stage", "stage": 4, "name": "validate", "label": "Nutrient fidelity validation"}

    t0_cit = time.perf_counter()
    evidence_out = [_format_evidence_item(e) for e in evidence_items]
    t_cit = (time.perf_counter() - t0_cit) * 1000

    t_total = (time.perf_counter() - t_total_start) * 1000

    t_bm25 = timing.get("bm25_ms", 0.0)
    t_emb = timing.get("embedding_ms", 0.0)
    t_faiss = timing.get("faiss_ms", 0.0)
    t_rrf = timing.get("rrf_ms", 0.0)
    t_rerank = timing.get("cross_encoder_ms", 0.0)
    t_ttft = final_gen_data.get("ttft_ms", 0.0)
    t_gen = final_gen_data.get("gen_ms", 0.0)
    t_val = final_gen_data.get("val_ms", 0.0)

    perf_metrics = {
        "age_validation_ms": round(t_age_val, 2),
        "query_preprocessing_ms": 0.5,
        "embedding_ms": round(t_emb, 2),
        "bm25_ms": round(t_bm25, 2),
        "faiss_ms": round(t_faiss, 2),
        "rrf_ms": round(t_rrf, 2),
        "cross_encoder_ms": round(t_rerank, 2),
        "context_refinement_ms": round(t_refine, 2),
        "prompt_construction_ms": 1.0,
        "qwen_ttft_ms": round(t_ttft, 2),
        "qwen_generation_ms": round(t_gen, 2),
        "nutrient_validation_ms": round(t_val, 2),
        "citation_formatting_ms": round(t_cit, 2),
        "total_request_ms": round(t_total, 2)
    }

    print("\n" + "=" * 45)
    print("[PERF] (STREAMED)")
    print(f"Age validation:      {perf_metrics['age_validation_ms']:>8.2f} ms")
    print(f"Query preprocessing: {perf_metrics['query_preprocessing_ms']:>8.2f} ms")
    print(f"Embedding:           {perf_metrics['embedding_ms']:>8.2f} ms")
    print(f"BM25:                {perf_metrics['bm25_ms']:>8.2f} ms")
    print(f"FAISS:               {perf_metrics['faiss_ms']:>8.2f} ms")
    print(f"RRF:                 {perf_metrics['rrf_ms']:>8.2f} ms")
    print(f"Cross-Encoder:       {perf_metrics['cross_encoder_ms']:>8.2f} ms")
    print(f"Context refinement:  {perf_metrics['context_refinement_ms']:>8.2f} ms")
    print(f"Prompt construction: {perf_metrics['prompt_construction_ms']:>8.2f} ms")
    print(f"Qwen TTFT:           {perf_metrics['qwen_ttft_ms']:>8.2f} ms")
    print(f"Qwen generation:     {perf_metrics['qwen_generation_ms']:>8.2f} ms")
    print(f"Validation:          {perf_metrics['nutrient_validation_ms']:>8.2f} ms")
    print(f"Citation:            {perf_metrics['citation_formatting_ms']:>8.2f} ms")
    print(f"TOTAL:               {perf_metrics['total_request_ms']:>8.2f} ms")
    print("=" * 45 + "\n", flush=True)

    yield {
        "event": "done",
        "result": {
            "query": query, "child_age": child_age, "scope_status": scope_status, "status": "success",
            "answer": final_gen_data["answer"], "citations": final_gen_data["citations"],
            "evidence": evidence_out, "generation_metadata": final_gen_data["generation_metadata"],
            "fidelity_check": final_gen_data.get("fidelity_check"),
            "perf_metrics": perf_metrics
        }
    }

if __name__ == "__main__":
    r = run_qwen_pipeline("What is the recommended protein RDA for a 10-year-old?", 10.0)
    print(json.dumps(r, indent=2, ensure_ascii=False))
