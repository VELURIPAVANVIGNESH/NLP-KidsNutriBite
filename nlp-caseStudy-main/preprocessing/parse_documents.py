import os
import csv
import json
import traceback
import pypdf
import sys

sys.stdout.reconfigure(encoding='utf-8')

def load_config(config_path="preprocessing/config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_documents():
    config = load_config()
    
    manifest_path = config.get("manifest_path", "data/metadata/corpus_manifest.csv")
    corpus_dir = config.get("corpus_dir", "knowledge_corpus")
    output_dir = config.get("parsed_dir", config.get("output_dir", "data/processed/parsed"))
    report_path = config.get("report_path", "data/processed/parser_report.csv")
    summary_path = config.get("summary_path", "data/processed/parser_summary.txt")
    min_char_threshold = config["min_character_threshold"]
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    # 1. Load manifest
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file '{manifest_path}' not found.")
        return
        
    active_docs = []
    total_docs_in_manifest = 0
    
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_docs_in_manifest += 1
            if row["retrieval_enabled"].strip().lower() == "true":
                active_docs.append(row)
                
    print(f"Loaded manifest. Total documents: {total_docs_in_manifest}. Active documents to parse: {len(active_docs)}.")
    
    report_rows = []
    
    total_pages_all = 0
    total_text_pages_all = 0
    total_empty_pages_all = 0
    total_low_text_pages_all = 0
    total_characters_all = 0
    total_words_all = 0
    total_warnings_all = 0
    total_errors_all = 0
    
    successfully_parsed_count = 0
    failed_count = 0
    manual_inspection_pages = [] # list of dicts with details of suspect pages
    
    for doc in active_docs:
        source_id = doc["source_id"]
        fname = doc["file_name"]
        rel_path = doc["relative_path"]
        
        # Verify physical path
        # In manifest, relative_path is 'knowledge_corpus/01_PRIMARY_KNOWLEDGE/...'
        # Check if the file exists directly or relative to workspace root
        pdf_path = rel_path
        if not os.path.exists(pdf_path):
            # Try joining with corpus_dir if relative_path does not contain it, but it does.
            # Let's check
            print(f"File not found: {pdf_path}. Skipping.")
            report_rows.append({
                "source_id": source_id,
                "file_name": fname,
                "pages_processed": 0,
                "pages_with_text": 0,
                "empty_pages": 0,
                "low_text_pages": 0,
                "extraction_warnings": 1,
                "extraction_errors": 1,
                "character_count": 0,
                "word_count": 0,
                "status": "Failed: File not found"
            })
            failed_count += 1
            total_warnings_all += 1
            total_errors_all += 1
            continue
            
        print(f"Parsing [{source_id}] {fname}...")
        
        pages_processed = 0
        pages_with_text = 0
        empty_pages = 0
        low_text_pages = 0
        doc_warnings = 0
        doc_errors = 0
        doc_char_count = 0
        doc_word_count = 0
        doc_pages_data = []
        
        status = "Success"
        
        try:
            reader = pypdf.PdfReader(pdf_path)
            pages_processed = len(reader.pages)
            
            for idx in range(pages_processed):
                page_number = idx + 1
                page_text = ""
                page_warnings = 0
                page_errors = 0
                
                try:
                    page_text = reader.pages[idx].extract_text() or ""
                except Exception as e:
                    page_errors += 1
                    doc_errors += 1
                    page_text = ""
                    
                char_count = len(page_text)
                word_count = len(page_text.split())
                
                doc_char_count += char_count
                doc_word_count += word_count
                
                # Check empty vs low text
                if char_count == 0:
                    empty_pages += 1
                    page_status = "empty"
                elif char_count < min_char_threshold:
                    low_text_pages += 1
                    page_status = "low_text"
                    page_warnings += 1
                    doc_warnings += 1
                else:
                    pages_with_text += 1
                    page_status = "ok"
                    
                doc_pages_data.append({
                    "page_number": page_number,
                    "text": page_text
                })
                
                # If page is suspicious (low text or error)
                if page_status in ("empty", "low_text") or page_errors > 0:
                    manual_inspection_pages.append({
                        "source_id": source_id,
                        "file_name": fname,
                        "page_number": page_number,
                        "char_count": char_count,
                        "status": page_status,
                        "errors": page_errors
                    })
                    
            # Output single JSON per source document
            output_json_path = os.path.join(output_dir, f"{source_id}_parsed.json")
            parsed_doc = {
                "source_id": source_id,
                "source_name": doc["source_name"],
                "file_name": fname,
                "relative_path": rel_path,
                "metadata": {
                    "publisher": doc["publisher"],
                    "publication_year": doc["publication_year"],
                    "document_type": doc["document_type"],
                    "authority_tier": doc["authority_tier"],
                    "domain": doc["domain"],
                    "age_min": doc["age_min"],
                    "age_max": doc["age_max"],
                    "retrieval_enabled": doc["retrieval_enabled"],
                    "total_pages": pages_processed
                },
                "pages": doc_pages_data
            }
            
            with open(output_json_path, mode='w', encoding='utf-8') as json_out:
                json.dump(parsed_doc, json_out, indent=2, ensure_ascii=False)
                
            successfully_parsed_count += 1
            
        except Exception as e:
            status = f"Failed: {type(e).__name__}"
            print(f"Error parsing document {source_id}: {e}")
            doc_errors += 1
            failed_count += 1
            
        # Accumulate stats
        total_pages_all += pages_processed
        total_text_pages_all += pages_with_text
        total_empty_pages_all += empty_pages
        total_low_text_pages_all += low_text_pages
        total_characters_all += doc_char_count
        total_words_all += doc_word_count
        total_warnings_all += doc_warnings
        total_errors_all += doc_errors
        
        report_rows.append({
            "source_id": source_id,
            "file_name": fname,
            "pages_processed": pages_processed,
            "pages_with_text": pages_with_text,
            "empty_pages": empty_pages,
            "low_text_pages": low_text_pages,
            "extraction_warnings": doc_warnings,
            "extraction_errors": doc_errors,
            "character_count": doc_char_count,
            "word_count": doc_word_count,
            "status": status
        })

    # Write report CSV
    report_headers = [
        "source_id", "file_name", "pages_processed", "pages_with_text", 
        "empty_pages", "low_text_pages", "extraction_warnings", 
        "extraction_errors", "character_count", "word_count", "status"
    ]
    with open(report_path, mode='w', newline='', encoding='utf-8') as rf:
        writer = csv.DictWriter(rf, fieldnames=report_headers)
        writer.writeheader()
        writer.writerows(report_rows)
        
    print(f"Verification report saved to: {report_path}")
    
    # 2. Write Summary TXT
    summary_lines = [
        "============================================================",
        "NUTRIKID DOCUMENT PARSER SUMMARY REPORT (PHASE 3.1)",
        "============================================================",
        f"Active Documents Discovered (in Manifest):   {len(active_docs)}",
        f"Active Documents Successfully Parsed:        {successfully_parsed_count}",
        f"Active Documents Failed to Parse:            {failed_count}",
        f"Total Pages Processed:                       {total_pages_all}",
        f"Total Pages with Extracted Text (>=10 char): {total_text_pages_all}",
        f"Total Empty Pages (0 char):                  {total_empty_pages_all}",
        f"Total Low-Text Pages (<10 char):             {total_low_text_pages_all}",
        f"Total Characters Extracted:                  {total_characters_all}",
        f"Total Words Extracted:                       {total_words_all}",
        f"Total Extraction Warnings:                   {total_warnings_all}",
        f"Total Extraction Errors:                     {total_errors_all}",
        "",
        "============================================================",
        "DOCUMENTS REQUIRING MANUAL INSPECTION",
        "============================================================"
    ]
    
    if manual_inspection_pages:
        summary_lines.append("The following pages are empty or contain very low text content:")
        # Group by document to keep summary clean
        doc_groups = {}
        for p in manual_inspection_pages:
            sid = p["source_id"]
            if sid not in doc_groups:
                doc_groups[sid] = {
                    "file_name": p["file_name"],
                    "pages": []
                }
            doc_groups[sid]["pages"].append(f"Page {p['page_number']} ({p['status']}, chars={p['char_count']})")
            
        for sid, info in doc_groups.items():
            summary_lines.append(f"  - {sid} ({info['file_name']}):")
            # chunk pages into groups for readability
            pages_str = ", ".join(info["pages"][:12])
            if len(info["pages"]) > 12:
                pages_str += f", ... (+{len(info['pages']) - 12} more pages)"
            summary_lines.append(f"    Suspect pages: {pages_str}")
    else:
        summary_lines.append("[+] No documents require manual inspection.")
        
    with open(summary_path, mode='w', encoding='utf-8') as sf:
        sf.write("\n".join(summary_lines))
        
    print(f"Summary report saved to: {summary_path}")
    print("\n".join(summary_lines[:15])) # print basic summary stats

if __name__ == '__main__':
    parse_documents()
