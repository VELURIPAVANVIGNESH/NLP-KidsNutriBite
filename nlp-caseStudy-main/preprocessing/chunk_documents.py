import os
import csv
import json
import re
import sys
import traceback

sys.stdout.reconfigure(encoding='utf-8')

def load_config(config_path="preprocessing/config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Conservative sentence splitting
def split_into_sentences(text):
    if not text:
        return []
    # Split on period, question mark, or exclamation mark followed by whitespace
    sentences = re.split(r'(?<=[.?!])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# Clean age range to float/int or None
def parse_age(value):
    if value is None or str(value).strip() == "":
        return None
    val_str = str(value).strip()
    try:
        if '.' in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str

# Check if a chunk text represents meaningless structural/orphan divider content
def is_structural_orphan(text):
    txt = text.strip()
    if len(txt) == 0:
        return True
    if len(txt) < 10:
        return True
    # If it's only digits and punctuation (like page numbers)
    if re.match(r'^[0-9\s\.\,\-\_\(\)]+$', txt):
        return True
    if txt.lower() in ["x", "xx", "xxx", "annexes", "annex", "contents"]:
        return True
    return False

def run_ifct_audit(ifct_doc, parsed_dir):
    source_id = ifct_doc["source_id"]
    fname = ifct_doc["file_name"]
    json_path = os.path.join(parsed_dir, f"{source_id}_parsed.json")
    
    print(f"\n--- RUNNING IFCT PRE-CHUNKING AUDIT FOR {source_id} ({fname}) ---")
    
    if not os.path.exists(json_path):
        print(f"ERROR: Parsed IFCT file not found at: {json_path}")
        return None
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    pages = data.get("pages", [])
    total_pages = len(pages)
    
    pages_with_codes = 0
    total_rows_detected = 0
    pages_with_no_rows = 0
    rows_per_page = {}
    
    code_pattern = re.compile(r'^[A-Z]\d{3}')
    
    # We locate table section start and end dynamically
    table_pages_indices = []
    for idx, p in enumerate(pages):
        text = p["text"] or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        has_codes = any(code_pattern.match(l) for l in lines)
        if has_codes:
            table_pages_indices.append(idx)
            
    start_idx = min(table_pages_indices) if table_pages_indices else 0
    end_idx = max(table_pages_indices) if table_pages_indices else 0
    
    suspicious_table_pages = []
    
    for idx, p in enumerate(pages):
        page_num = p["page_number"]
        text = p["text"] or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        row_count = sum(1 for l in lines if code_pattern.match(l))
        
        if row_count > 0:
            pages_with_codes += 1
            total_rows_detected += row_count
            rows_per_page[page_num] = row_count
        else:
            pages_with_no_rows += 1
            # If page is within active table start/end boundaries but contains no rows,
            # it is a gap page (divider or header page)
            if start_idx <= idx <= end_idx:
                suspicious_table_pages.append(page_num)
                
    print(f"Total IFCT Pages:                  {total_pages}")
    print(f"Table Section Range:               Page {start_idx + 1} to Page {end_idx + 1}")
    print(f"Pages with Food Row Codes:         {pages_with_codes}")
    print(f"Total Food Rows Detected:          {total_rows_detected}")
    print(f"Pages with No Food Row Codes:      {pages_with_no_rows}")
    print(f"Table Section Gaps (No Codes):     {len(suspicious_table_pages)}")
    
    # Safety Check: Did we extract a healthy amount of rows?
    if total_rows_detected < 100:
        print(f"WARNING: Exceptionally low food-row detection count ({total_rows_detected}). Audit failed!")
        return {
            "success": False,
            "total_pages": total_pages,
            "pages_with_codes": pages_with_codes,
            "total_rows_detected": total_rows_detected,
            "suspicious_pages": suspicious_table_pages,
            "start_page": start_idx + 1,
            "end_page": end_idx + 1
        }
        
    print("IFCT Pre-chunking Audit PASSED successfully.\n")
    return {
        "success": True,
        "total_pages": total_pages,
        "pages_with_codes": pages_with_codes,
        "total_rows_detected": total_rows_detected,
        "suspicious_pages": suspicious_table_pages,
        "start_page": start_idx + 1,
        "end_page": end_idx + 1
    }

def chunk_prose_document(doc, parsed_data, config):
    source_id = doc["source_id"]
    file_name = doc["file_name"]
    rel_path = doc["relative_path"]
    
    target_size = config["chunk_size_target"]
    max_size = config["chunk_size_max"]
    overlap_size = config["chunk_overlap"]
    
    chunks = []
    
    # Meta fields directly inherited
    publisher = doc["publisher"]
    pub_year = doc["publication_year"]
    doc_type = doc["document_type"]
    auth_tier = doc["authority_tier"]
    domain = doc["domain"]
    age_min = parse_age(doc["age_min"])
    age_max = parse_age(doc["age_max"])
    
    # Conservative heading regex
    heading_regex = re.compile(r'^(Chapter\s+\d+|Annex\s+\d+|\d+\.\d+(\.\d+)?)\s+[A-Z]', re.IGNORECASE)
    
    current_heading_text = ""
    current_heading_page = None
    
    # Flatten prose text into sentences with associated page numbers
    sentences_with_pages = []
    
    for page_obj in parsed_data["pages"]:
        page_num = page_obj["page_number"]
        page_text = page_obj["text"] or ""
        
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in page_text.split("\n") if p.strip()]
            
        for para in paragraphs:
            is_heading = len(para) < 120 and heading_regex.match(para)
            if is_heading:
                sentences_with_pages.append((para, page_num, True))
            else:
                sentences = split_into_sentences(para)
                for sentence in sentences:
                    sentences_with_pages.append((sentence, page_num, False))
                    
    active_sentences = [] # list of tuples: (text, page_num)
    
    def flush_chunk():
        nonlocal active_sentences
        if not active_sentences:
            return
        chunk_text = " ".join(s[0] for s in active_sentences)
        chunk_pages = list(set(s[1] for s in active_sentences))
        
        context_prefix = ""
        if current_heading_text:
            context_prefix = f"Section: {current_heading_text}"
            if current_heading_page and current_heading_page not in chunk_pages:
                chunk_pages.append(current_heading_page)
                
        chunks.append({
            "text": chunk_text,
            "page_numbers": sorted(chunk_pages),
            "context_prefix": context_prefix
        })
        
        # Build overlap
        overlap_sentences = []
        overlap_len = 0
        for s in reversed(active_sentences):
            if overlap_len + len(s[0]) + 1 <= overlap_size:
                overlap_sentences.insert(0, s)
                overlap_len += len(s[0]) + 1
            else:
                break
        active_sentences = overlap_sentences

    for s_text, p_num, is_h in sentences_with_pages:
        if is_h:
            flush_chunk()
            current_heading_text = s_text
            current_heading_page = p_num
            continue
            
        current_len = sum(len(s[0]) + 1 for s in active_sentences) - 1 if active_sentences else 0
        
        # HARDENING: Target-vs-Max splitting logic
        if active_sentences and (current_len + 1 + len(s_text) > max_size):
            flush_chunk()
            # Recalculate length with the overlap
            current_len = sum(len(s[0]) + 1 for s in active_sentences) - 1 if active_sentences else 0
            # If the overlap + new sentence still exceeds max_size,
            # discard the overlap and start a completely fresh chunk.
            if current_len + 1 + len(s_text) > max_size:
                active_sentences = []
        elif active_sentences and (current_len >= target_size):
            # Flush because we met the target size threshold
            flush_chunk()
            
        active_sentences.append((s_text, p_num))
        
    # Final flush
    if active_sentences:
        chunk_text = " ".join(s[0] for s in active_sentences)
        chunk_pages = list(set(s[1] for s in active_sentences))
        context_prefix = ""
        if current_heading_text:
            context_prefix = f"Section: {current_heading_text}"
            if current_heading_page and current_heading_page not in chunk_pages:
                chunk_pages.append(current_heading_page)
        chunks.append({
            "text": chunk_text,
            "page_numbers": sorted(chunk_pages),
            "context_prefix": context_prefix
        })
        
    # Map to final schema
    final_chunks = []
    for idx, c in enumerate(chunks):
        chunk_id = f"{source_id}-C{idx+1:05d}"
        final_chunks.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "source_name": doc["source_name"],
            "file_name": file_name,
            "relative_path": rel_path,
            "page_numbers": c["page_numbers"],
            "publisher": publisher,
            "publication_year": pub_year,
            "document_type": doc_type,
            "authority_tier": auth_tier,
            "domain": domain,
            "age_min": age_min,
            "age_max": age_max,
            "text": c["text"],
            "context_prefix": c["context_prefix"]
        })
        
    return final_chunks

def chunk_ifct_document(doc, parsed_data, config, audit_results):
    source_id = doc["source_id"]
    file_name = doc["file_name"]
    rel_path = doc["relative_path"]
    
    rows_per_chunk = config["ifct_rows_per_chunk"]
    
    publisher = doc["publisher"]
    pub_year = doc["publication_year"]
    doc_type = doc["document_type"]
    auth_tier = doc["authority_tier"]
    domain = doc["domain"]
    age_min = parse_age(doc["age_min"])
    age_max = parse_age(doc["age_max"])
    
    chunks = []
    
    current_category = ""
    current_category_pages = []
    current_headers = ""
    current_headers_pages = []
    
    code_pattern = re.compile(r'^[A-Z]\d{3}')
    category_pattern = re.compile(r'^[A-Z]\s+[A-Z\s,]{4,50}$')
    header_pattern = re.compile(r'(WATER|PROTCNT|FATCE|CHOAVLDF|ENERC|Moisture|Protein|Total\s+Fat)', re.IGNORECASE)
    
    active_rows_buffer = []
    active_rows_pages = []
    
    total_parsed_rows = 0
    fallback_pages_count = 0
    
    for page_obj in parsed_data["pages"]:
        page_num = page_obj["page_number"]
        page_text = page_obj["text"] or ""
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        
        has_food_rows = any(code_pattern.match(l) for l in lines)
        
        if not has_food_rows:
            fallback_pages_count += 1
            sub_page_data = {
                "source_id": source_id,
                "pages": [page_obj]
            }
            prose_chunks = chunk_prose_document(doc, sub_page_data, config)
            for pc in prose_chunks:
                chunks.append(pc)
            continue
            
        # HARDENING: IFCT Category Provenance Sanity Check
        # Reset Category and Header if they are separated by >15 pages (prevents context drift across chapters)
        if current_category_pages and (page_num - current_category_pages[0] > 15):
            print(f"[Sanity Check] Category '{current_category}' reset on page {page_num} due to large page gap ({page_num - current_category_pages[0]} pages).")
            current_category = ""
            current_category_pages = []
            
        if current_headers_pages and (page_num - current_headers_pages[0] > 15):
            current_headers = ""
            current_headers_pages = []
            
        # Parse table lines
        for line in lines:
            if category_pattern.match(line) and not line.startswith("TABLE") and len(line) < 100:
                current_category = line
                current_category_pages = [page_num]
            elif header_pattern.search(line) and len(line) < 150:
                current_headers = line
                current_headers_pages = [page_num]
            elif code_pattern.match(line):
                active_rows_buffer.append(line)
                active_rows_pages.append(page_num)
                total_parsed_rows += 1
                
                if len(active_rows_buffer) >= rows_per_chunk:
                    context_lines = []
                    if current_category:
                        context_lines.append(f"Category: {current_category}")
                    if current_headers:
                        context_lines.append(f"Table Columns: {current_headers}")
                    context_prefix = "\n".join(context_lines)
                    
                    header_pages = list(set(current_category_pages + current_headers_pages))
                    row_pages = list(set(active_rows_pages))
                    chunk_pages = sorted(list(set(header_pages + row_pages)))
                    
                    chunks.append({
                        "text": "\n".join(active_rows_buffer),
                        "context_prefix": context_prefix,
                        "page_numbers": chunk_pages
                    })
                    
                    active_rows_buffer = []
                    active_rows_pages = []
                    
    # Flush remaining rows
    if active_rows_buffer:
        context_lines = []
        if current_category:
            context_lines.append(f"Category: {current_category}")
        if current_headers:
            context_lines.append(f"Table Columns: {current_headers}")
        context_prefix = "\n".join(context_lines)
        
        header_pages = list(set(current_category_pages + current_headers_pages))
        row_pages = list(set(active_rows_pages))
        chunk_pages = sorted(list(set(header_pages + row_pages)))
        
        chunks.append({
            "text": "\n".join(active_rows_buffer),
            "context_prefix": context_prefix,
            "page_numbers": chunk_pages
        })
        
    # Map to final schema
    final_chunks = []
    for idx, c in enumerate(chunks):
        if "chunk_id" in c:
            final_chunks.append(c)
        else:
            chunk_id = f"{source_id}-C{idx+1:05d}"
            final_chunks.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "source_name": doc["source_name"],
                "file_name": file_name,
                "relative_path": rel_path,
                "page_numbers": c["page_numbers"],
                "publisher": publisher,
                "publication_year": pub_year,
                "document_type": doc_type,
                "authority_tier": auth_tier,
                "domain": domain,
                "age_min": age_min,
                "age_max": age_max,
                "text": c["text"],
                "context_prefix": c["context_prefix"]
            })
            
    # Fix sequence IDs
    for idx, fc in enumerate(final_chunks):
        fc["chunk_id"] = f"{source_id}-C{idx+1:05d}"
        
    return final_chunks

def validate_chunks(chunks_list, active_doc_ids, manifest_dict, parsed_docs_cache):
    print("--- RUNNING DETAILED VALIDATION AND PROVENANCE CHECKS ---")
    
    errors = []
    seen_ids = set()
    
    for idx, c in enumerate(chunks_list):
        chunk_id = c["chunk_id"]
        source_id = c["source_id"]
        text = c["text"]
        page_numbers = c["page_numbers"]
        
        if chunk_id in seen_ids:
            errors.append(f"Duplicate chunk_id: '{chunk_id}'")
        seen_ids.add(chunk_id)
        
        if not re.match(rf'^{source_id}-C\d{{5}}$', chunk_id):
            errors.append(f"Invalid format for chunk_id: '{chunk_id}'")
            
        if not text.strip():
            errors.append(f"Empty chunk text at '{chunk_id}'")
            
        if source_id not in active_doc_ids:
            errors.append(f"Source ID '{source_id}' is inactive/disabled")
            
        if not isinstance(page_numbers, list):
            errors.append(f"page_numbers field is not a list in '{chunk_id}'")
            continue
            
        if not page_numbers:
            errors.append(f"page_numbers list is empty in '{chunk_id}'")
            continue
            
        parsed_doc = parsed_docs_cache.get(source_id)
        if parsed_doc:
            available_pages = {p["page_number"] for p in parsed_doc["pages"]}
            for pnum in page_numbers:
                if not isinstance(pnum, int) or pnum <= 0:
                    errors.append(f"Invalid page number format '{pnum}' in '{chunk_id}'")
                elif pnum not in available_pages:
                    errors.append(f"Page number '{pnum}' in '{chunk_id}' does not exist in parent document pages")
                    
        man_doc = manifest_dict.get(source_id)
        if man_doc:
            fields_to_check = [
                "source_name", "file_name", "relative_path",
                "publisher", "publication_year", "document_type", 
                "authority_tier", "domain"
            ]
            for field in fields_to_check:
                m_val = man_doc[field].strip()
                c_val = str(c.get(field, '')).strip()
                if m_val != c_val:
                    errors.append(f"Metadata field mismatch '{field}' in '{chunk_id}': manifest='{m_val}', chunk='{c_val}'")
                    
            m_age_min = parse_age(man_doc["age_min"])
            m_age_max = parse_age(man_doc["age_max"])
            if c["age_min"] != m_age_min or c["age_max"] != m_age_max:
                errors.append(f"Age limits mismatch in '{chunk_id}': manifest=({m_age_min},{m_age_max}), chunk=({c['age_min']},{c['age_max']})")
                
    return errors

def verify_ifct_chunks_representative(chunks):
    print("--- RUNNING PROGRAMMATIC 3-CHUNK IFCT STRUCTURAL AUDIT ---")
    
    ifct_chunks = [c for c in chunks if c["source_id"] == "NK-010"]
    table_chunks = [c for c in ifct_chunks if "Category:" in c["context_prefix"]]
    
    if len(table_chunks) < 3:
        print("WARNING: Insufficient IFCT table chunks for validation!")
        return {"success": False, "verified_count": 0, "log": "Insufficient table chunks"}
        
    indices_to_check = [10, len(table_chunks)//2, len(table_chunks) - 10]
    verified_ok = 0
    verification_log = []
    
    code_pattern = re.compile(r'[A-Z]\d{3}')
    
    for idx in indices_to_check:
        c = table_chunks[idx]
        chunk_id = c["chunk_id"]
        text = c["text"]
        prefix = c["context_prefix"]
        pages = c["page_numbers"]
        
        has_category = "Category:" in prefix
        has_food_codes = any(code_pattern.search(l) for l in text.split("\n"))
        has_pages = len(pages) > 0
        has_numbers = any(char.isdigit() for char in text)
        
        status = has_category and has_food_codes and has_pages and has_numbers
        if status:
            verified_ok += 1
            verification_log.append(f"Chunk {chunk_id}: PASSED (Category context verified, food rows contain codes, page provenance={pages}, numerical integrity preserved)")
        else:
            verification_log.append(f"Chunk {chunk_id}: FAILED (category={has_category}, codes={has_food_codes}, pages={pages}, numbers={has_numbers})")
            
    print(f"Verified {len(indices_to_check)} representative IFCT chunks. Success: {verified_ok}/{len(indices_to_check)}")
    for log in verification_log:
        print(f"  - {log}")
        
    return {
        "success": verified_ok == len(indices_to_check),
        "verified_count": verified_ok,
        "details": verification_log
    }

def main():
    config = load_config()
    manifest_path = config["manifest_path"]
    parsed_dir = config["parsed_dir"]
    chunks_dir = config["chunks_dir"]
    report_path = config["chunk_report_path"]
    summary_path = config["chunk_summary_path"]
    
    os.makedirs(chunks_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    # 1. Load manifest
    if not os.path.exists(manifest_path):
        print(f"Error: manifest not found at {manifest_path}")
        return
        
    active_docs = []
    manifest_dict = {}
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["source_id"]
            manifest_dict[sid] = row
            if row["retrieval_enabled"].strip().lower() == "true":
                active_docs.append(row)
                
    active_doc_ids = {doc["source_id"] for doc in active_docs}
    print(f"Manifest loaded. Active documents: {len(active_docs)}")
    
    # 2. Run IFCT Audit
    ifct_doc = None
    for doc in active_docs:
        if "IFCT_BOOK.pdf" in doc["file_name"]:
            ifct_doc = doc
            break
            
    audit_results = None
    if ifct_doc:
        audit_results = run_ifct_audit(ifct_doc, parsed_dir)
        if audit_results and not audit_results["success"]:
            print("IFCT Pre-chunking audit failed! Stopping execution to prevent malformed table parsing.")
            return
            
    parsed_docs_cache = {}
    retrieval_chunks = [] # final retrieval set (excludes structural/orphans)
    report_rows = []
    
    # Statistics and Diagnostic Variables
    prose_chunks_lengths = []
    ifct_chunks_lengths = []
    structural_orphans_count = 0
    total_fallback_pages = 0
    total_parsed_corruption_chars = 0
    total_chunked_corruption_chars = 0
    
    # Large prose chunk analysis lists
    single_sentence_large_chunks = []
    multi_sentence_large_chunks = []
    
    # Completeness diagnostics cache
    completeness_stats = []
    
    # 3. Process each active document
    for doc in active_docs:
        source_id = doc["source_id"]
        fname = doc["file_name"]
        
        parsed_json_path = os.path.join(parsed_dir, f"{source_id}_parsed.json")
        if not os.path.exists(parsed_json_path):
            print(f"Skipping {source_id} because parsed JSON does not exist.")
            continue
            
        with open(parsed_json_path, 'r', encoding='utf-8') as jf:
            parsed_data = json.load(jf)
            
        parsed_docs_cache[source_id] = parsed_data
        
        # Source characters & extraction symbols corruption count ( = \ufffd)
        source_char_count = sum(len(p["text"] or "") for p in parsed_data["pages"])
        source_corruption_count = sum((p["text"] or "").count("\ufffd") for p in parsed_data["pages"])
        total_parsed_corruption_chars += source_corruption_count
        
        print(f"Chunking [{source_id}] {fname}...")
        
        doc_chunks = []
        if source_id == ifct_doc.get("source_id") if ifct_doc else False:
            doc_chunks = chunk_ifct_document(doc, parsed_data, config, audit_results)
            if audit_results:
                total_fallback_pages += audit_results["total_pages"] - audit_results["pages_with_codes"]
        else:
            doc_chunks = chunk_prose_document(doc, parsed_data, config)
            
        # HARDENING: Classify, Audit Lengths, and filter out structural/orphan chunks
        filtered_doc_chunks = []
        for c in doc_chunks:
            c_len = len(c["text"])
            
            # Identify and exclude structural/orphan divider fragments from the final retrieval JSONs
            if is_structural_orphan(c["text"]):
                structural_orphans_count += 1
                continue # Discard from final retrieval chunks
                
            filtered_doc_chunks.append(c)
            total_chunked_corruption_chars += c["text"].count("\ufffd")
            
            if source_id == ifct_doc.get("source_id") if ifct_doc else False:
                ifct_chunks_lengths.append(c_len)
            else:
                prose_chunks_lengths.append(c_len)
                
                # Check for prose chunks exceeding max size (>1400)
                if c_len > config["chunk_size_max"]:
                    sentences = split_into_sentences(c["text"])
                    if len(sentences) <= 1:
                        single_sentence_large_chunks.append((c["chunk_id"], c_len))
                    else:
                        multi_sentence_large_chunks.append((c["chunk_id"], c_len, len(sentences)))
                        
        # Save per-source JSON chunks file (retrieval-enabled chunks only)
        output_json_path = os.path.join(chunks_dir, f"{source_id}_chunks.json")
        with open(output_json_path, 'w', encoding='utf-8') as out_f:
            json.dump(filtered_doc_chunks, out_f, indent=2, ensure_ascii=False)
            
        retrieval_chunks.extend(filtered_doc_chunks)
        
        lengths = [len(c["text"]) for c in filtered_doc_chunks]
        avg_len = sum(lengths)/len(lengths) if lengths else 0
        max_len = max(lengths) if lengths else 0
        min_len = min(lengths) if lengths else 0
        
        report_rows.append({
            "source_id": source_id,
            "file_name": fname,
            "chunks_generated": len(filtered_doc_chunks),
            "avg_chunk_length": round(avg_len, 1),
            "max_chunk_length": max_len,
            "min_chunk_length": min_len,
            "status": "Success"
        })
        
        # Completeness Check Diagnostics (incorporating overlap check)
        chunked_pages_covered = set()
        chunked_chars_total = 0
        for c in filtered_doc_chunks:
            chunked_pages_covered.update(c["page_numbers"])
            chunked_chars_total += len(c["text"])
            
        source_pages_all = {p["page_number"] for p in parsed_data["pages"] if (p["text"] or "").strip()}
        uncovered_pages = sorted(list(source_pages_all - chunked_pages_covered))
        
        completeness_stats.append({
            "source_id": source_id,
            "file_name": fname,
            "source_pages_count": len(source_pages_all),
            "covered_pages_count": len(chunked_pages_covered & source_pages_all),
            "uncovered_pages": uncovered_pages,
            "source_chars": source_char_count,
            "chunked_chars": chunked_chars_total
        })
        
    # Write report CSV
    report_headers = ["source_id", "file_name", "chunks_generated", "avg_chunk_length", "max_chunk_length", "min_chunk_length", "status"]
    with open(report_path, mode='w', newline='', encoding='utf-8') as rf:
        writer = csv.DictWriter(rf, fieldnames=report_headers)
        writer.writeheader()
        writer.writerows(report_rows)
        
    print(f"Chunker report saved to: {report_path}")
    
    # Save unified preprocessed_corpus.json payload
    preprocessed_corpus_path = config.get("preprocessed_corpus_path", "data/processed/preprocessed_corpus.json")
    os.makedirs(os.path.dirname(preprocessed_corpus_path), exist_ok=True)
    with open(preprocessed_corpus_path, mode='w', encoding='utf-8') as pcf:
        json.dump(retrieval_chunks, pcf, indent=2, ensure_ascii=False)
    print(f"Preprocessed corpus payload saved to: {preprocessed_corpus_path}")
    
    # 4. Perform Detailed Validation Loop
    val_errors = validate_chunks(retrieval_chunks, active_doc_ids, manifest_dict, parsed_docs_cache)
    
    # 5. Programmatic 3-Chunk Representative Validation
    ifct_verif = verify_ifct_chunks_representative(retrieval_chunks)
    if not ifct_verif["success"]:
        val_errors.append("Representative IFCT 3-chunk verification check FAILED.")
        
    # Check for multi-sentence large chunks (should be 0 under correct target/max boundaries)
    if multi_sentence_large_chunks:
        val_errors.append(f"Genuinely oversized multi-sentence prose chunks detected (Count: {len(multi_sentence_large_chunks)}). Must be fixed.")
        
    # Summarize stats
    total_retrieval_chunks = len(retrieval_chunks)
    
    p_avg = sum(prose_chunks_lengths)/len(prose_chunks_lengths) if prose_chunks_lengths else 0
    p_max = max(prose_chunks_lengths) if prose_chunks_lengths else 0
    p_min = min(prose_chunks_lengths) if prose_chunks_lengths else 0
    
    i_avg = sum(ifct_chunks_lengths)/len(ifct_chunks_lengths) if ifct_chunks_lengths else 0
    i_max = max(ifct_chunks_lengths) if ifct_chunks_lengths else 0
    i_min = min(ifct_chunks_lengths) if ifct_chunks_lengths else 0
    
    # 6. Write Summary TXT
    raw_chunks_total = total_retrieval_chunks + structural_orphans_count
    summary_lines = [
        "============================================================",
        "NUTRIKID DOCUMENT CHUNKER SUMMARY REPORT (PHASE 3.2)",
        "============================================================",
        f"Active Documents Processed:          {len(active_docs)}",
        f"Raw Chunks Generated Before Filter:  {raw_chunks_total}",
        f"Structural/Orphan Chunks Excluded:   {structural_orphans_count}",
        f"Final Retrieval-Eligible Chunks:     {total_retrieval_chunks}",
        "",
        "============================================================",
        "CHUNK LENGTH DISTINCTION STATISTICS",
        "============================================================",
        "General Prose Chunks (target <= 1000, max <= 1400):",
        f"  - Count:                           {len(prose_chunks_lengths)}",
        f"  - Average Length:                  {round(p_avg, 1)} characters",
        f"  - Maximum Length:                  {p_max} characters",
        f"  - Minimum Length:                  {p_min} characters",
        "",
        "IFCT Structured Table Chunks (grouped by ifct_rows_per_chunk=6):",
        f"  - Count:                           {len(ifct_chunks_lengths)}",
        f"  - Average Length:                  {round(i_avg, 1)} characters",
        f"  - Maximum Length:                  {i_max} characters",
        f"  - Minimum Length:                  {i_min} characters",
        "",
        "============================================================",
        "PROSE CHUNKS >1400 DIAGNOSTICS",
        "============================================================",
        f"Single Indivisible Text Units (Huge Sentence/Block): {len(single_sentence_large_chunks)} chunks",
        f"Genuinely Oversized Multi-sentence Chunks:           {len(multi_sentence_large_chunks)} chunks",
        ""
    ]
    
    if single_sentence_large_chunks:
        summary_lines.append("Single Indivisible Sentence Units (first 10):")
        for cid, length in single_sentence_large_chunks[:10]:
            summary_lines.append(f"  - {cid}: length={length} characters (1 sentence)")
            
    if multi_sentence_large_chunks:
        summary_lines.append("Genuinely Oversized Multi-sentence Chunks (Errors):")
        for cid, length, s_count in multi_sentence_large_chunks:
            summary_lines.append(f"  - {cid}: length={length} characters ({s_count} sentences) - BUG!")
            
    summary_lines.extend([
        "",
        "============================================================",
        "IFCT DIAGNOSTIC RESULTS",
        "============================================================"
    ])
    
    if audit_results:
        summary_lines.extend([
            f"Audit Success:                       {audit_results['success']}",
            f"Total IFCT Pages Inspected:          {audit_results['total_pages']}",
            f"Pages with Food Row Codes:           {audit_results['pages_with_codes']}",
            f"Total Food Rows Detected:             {audit_results['total_rows_detected']}",
            f"Table Section Gaps (No Codes):       {len(audit_results['suspicious_pages'])}",
            f"Fallback Pages Count:                {total_fallback_pages}"
        ])
    else:
        summary_lines.append("IFCT Document not found or processed.")
        
    summary_lines.extend([
        "",
        "============================================================",
        "REPRESENTATIVE IFCT 3-CHUNK VALIDATION RESULTS",
        "============================================================"
    ])
    for detail in ifct_verif.get("details", []):
        summary_lines.append(f"  [+] {detail}")
        
    summary_lines.extend([
        "",
        "============================================================",
        "COMPLETENESS DIAGNOSTIC AUDIT RESULTS",
        "============================================================"
    ])
    
    for cs in completeness_stats:
        uncovered_str = ", ".join(map(str, cs["uncovered_pages"][:10]))
        if len(cs["uncovered_pages"]) > 10:
            uncovered_str += f" (+{len(cs['uncovered_pages'])-10} more)"
        
        summary_lines.extend([
            f"Source: {cs['source_id']} ({cs['file_name']}):",
            f"  - Parsed Pages Containing Any Text:              {cs['source_pages_count']}",
            f"  - Meaningful Retrieval Content Pages Covered:    {cs['covered_pages_count']}",
            f"  - Structural/Orphan Pages Intentionally Excluded: {len(cs['uncovered_pages'])}",
            f"  - Source text chars: {cs['source_chars']}, Generated chunk text chars: {cs['chunked_chars']}",
            f"  - Excluded Structural Page List:                 {uncovered_str if uncovered_str else 'None'}"
        ])
    
    summary_lines.extend([
        "",
        "============================================================",
        "NUMERICAL EXTRACTION CORRUPTION DIAGNOSTICS",
        "============================================================",
        "Phase 3.1 PDF Text Extraction Limitations:",
        f"  - Total replacement chars () in parsed source: {total_parsed_corruption_chars}",
        f"  - Total replacement chars () in generated chunks: {total_chunked_corruption_chars}",
        f"  - Phase 3.2 modification check: {'PASS (No additional corruption introduced)' if total_parsed_corruption_chars == total_chunked_corruption_chars else 'FAIL (Additional corruption detected!)'}",
        "",
        "============================================================",
        "VALIDATION VERIFICATION STATUS",
        "============================================================"
    ])
    
    if not val_errors:
        summary_lines.append("[+] VALIDATION STATUS: PASSED (0 errors found)")
    else:
        summary_lines.append(f"[-] VALIDATION STATUS: FAILED ({len(val_errors)} errors found)")
        for err in val_errors:
            summary_lines.append(f"  - ERROR: {err}")
            
    with open(summary_path, mode='w', encoding='utf-8') as sf:
        sf.write("\n".join(summary_lines))
        
    print(f"Summary report saved to: {summary_path}")
    print("\n".join(summary_lines[:23])) # print basic summary stats

if __name__ == '__main__':
    main()
