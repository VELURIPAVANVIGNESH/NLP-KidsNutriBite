import os
import csv
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def load_config(config_path="preprocessing/config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_quality_check():
    config = load_config()
    manifest_path = config["manifest_path"]
    parsed_dir = config["parsed_dir"]
    
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file '{manifest_path}' not found.")
        return

    # Load manifest rows
    manifest_rows = []
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            manifest_rows.append(row)
            
    # Select representative documents based on publisher and domain
    representatives = {}
    
    for row in manifest_rows:
        if row["retrieval_enabled"].strip().lower() != "true":
            continue
            
        fname = row["file_name"]
        publisher = row["publisher"]
        domain = row["domain"]
        source_id = row["source_id"]
        
        # 1. IFCT (Indian Food Composition Tables)
        if "IFCT" in fname and "IFCT" not in representatives:
            representatives["IFCT"] = row
        # 2. DGI (Dietary Guidelines for Indians)
        elif "DGI" in fname and "DGI" not in representatives:
            representatives["DGI"] = row
        # 3. WHO
        elif publisher == "WHO" and "WHO" not in representatives and "school" in fname.lower():
            representatives["WHO"] = row
        # 4. ICMR
        elif publisher == "ICMR-NIN" and domain == "Recommended Dietary Allowances" and "ICMR" not in representatives:
            representatives["ICMR"] = row
        # 5. FSSAI
        elif publisher == "FSSAI" and "FSSAI" not in representatives:
            representatives["FSSAI"] = row
        # 6. FAO
        elif (publisher == "FAO" or publisher == "FAO/WHO") and "FAO" not in representatives:
            representatives["FAO"] = row

    print("============================================================")
    print("NUTRIKID DOCUMENT PARSER QUALITY CHECK")
    print("============================================================")
    print(f"Selected representative documents for quality check:")
    for key, doc in representatives.items():
        print(f"  - {key}: {doc['source_id']} ({doc['file_name']})")
    print("------------------------------------------------------------\n")
    
    for key, doc in representatives.items():
        source_id = doc["source_id"]
        fname = doc["file_name"]
        parsed_json_path = os.path.join(parsed_dir, f"{source_id}_parsed.json")
        
        print(f"=== CHECKING REPRESENTATIVE: {key} ({source_id} - {fname}) ===")
        
        if not os.path.exists(parsed_json_path):
            print(f"[-] ERROR: Parsed file '{parsed_json_path}' does not exist on disk!")
            print("="*60 + "\n")
            continue
            
        try:
            with open(parsed_json_path, "r", encoding="utf-8") as jf:
                parsed_data = json.load(jf)
                
            # Check source ID
            if parsed_data["source_id"] != source_id:
                print(f"[-] ERROR: JSON source_id '{parsed_data['source_id']}' does not match manifest '{source_id}'!")
            else:
                print(f"[+] Verified: source_id matches ('{source_id}')")
                
            # Check metadata fields
            meta = parsed_data["metadata"]
            print(f"[+] Verified: metadata exists (pages={meta['total_pages']}, publisher='{meta['publisher']}', tier='{meta['authority_tier']}')")
            
            # Check pages array
            pages = parsed_data["pages"]
            if not pages:
                print("[-] ERROR: Pages list is empty!")
                print("="*60 + "\n")
                continue
                
            print(f"[+] Verified: extracted pages count = {len(pages)}")
            
            # Check page numbers sequential
            sequential = True
            for i, p in enumerate(pages):
                if p["page_number"] != i + 1:
                    sequential = False
                    break
            if sequential:
                print("[+] Verified: page numbers are sequential (1-indexed)")
            else:
                print("[-] ERROR: page numbers are not sequential!")
                
            # Check text presence and quality
            non_empty_pages_count = sum(1 for p in pages if (p["text"] or "").strip())
            print(f"[+] Verified: {non_empty_pages_count} of {len(pages)} pages contain text content")
            
            # Show a sample of page 2 if it exists
            if len(pages) >= 2:
                sample_text = (pages[1]["text"] or "").strip()
                sample_snippet = sample_text[:120].replace('\n', ' ')
                print(f"[+] Sample Text (Page 2): {sample_snippet}...")
            else:
                sample_text = (pages[0]["text"] or "").strip()
                sample_snippet = sample_text[:120].replace('\n', ' ')
                print(f"[+] Sample Text (Page 1): {sample_snippet}...")
                
            # Highlight suspicious pages in this file
            suspicious_pages = []
            for p in pages:
                p_text = (p["text"] or "").strip()
                if len(p_text) > 0 and len(p_text) < 15:
                    suspicious_pages.append(f"Page {p['page_number']} (chars={len(p_text)})")
            if suspicious_pages:
                print(f"[!] WARNING: suspicious low text on pages: {', '.join(suspicious_pages[:5])}")
            else:
                print("[+] Verified: no suspiciously short text pages found (<15 chars)")
                
        except Exception as e:
            print(f"[-] ERROR checking file: {e}")
            traceback.print_exc()
            
        print("="*60 + "\n")

if __name__ == '__main__':
    run_quality_check()
