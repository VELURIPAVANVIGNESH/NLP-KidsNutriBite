import os
import csv
import hashlib

def calculate_md5(filepath):
    """Calculate MD5 hash of a file to check for exact byte duplicates."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        return None

def validate_manifest():
    root_dir = "knowledge_corpus"
    manifest_csv = "data/metadata/corpus_manifest.csv"
    validation_txt = "data/metadata/manifest_validation.txt"
    
    errors = []
    warnings = []
    
    # 1. Discover physical PDFs
    discovered_pdfs = {}
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith('.pdf'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ".").replace('\\', '/')
                folder = os.path.basename(root)
                discovered_pdfs[rel_path] = {
                    "file_name": f,
                    "folder": folder,
                    "full_path": full_path,
                    "md5": calculate_md5(full_path)
                }
                
    total_pdfs = len(discovered_pdfs)
    
    # 2. Read Manifest
    if not os.path.exists(manifest_csv):
        errors.append(f"Manifest file {manifest_csv} does not exist.")
        write_report(total_pdfs, 0, {}, [], [], errors, warnings, validation_txt)
        return
        
    manifest_entries = []
    source_ids = set()
    relative_paths_in_manifest = set()
    
    folder_counts = {
        "01_PRIMARY_KNOWLEDGE": 0,
        "02_SUPPORTING_KNOWLEDGE": 0,
        "03_EVALUATION_CONTEXT": 0,
        "04_OUT_OF_SCOPE_INFANT": 0,
        "05_REFERENCE_ONLY": 0
    }
    
    with open(manifest_csv, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            manifest_entries.append(row)
            source_ids.add(row["source_id"])
            relative_paths_in_manifest.add(row["relative_path"])
            
            fld = row["folder"]
            if fld in folder_counts:
                folder_counts[fld] += 1
            else:
                folder_counts[fld] = 1
                
    total_manifest = len(manifest_entries)
    
    # 3. Perform Validations
    
    # Check: every discovered PDF has exactly one manifest entry
    for pdf_path in discovered_pdfs:
        if pdf_path not in relative_paths_in_manifest:
            errors.append(f"Discovered PDF '{pdf_path}' is not present in the manifest.")
            
    # Check: every manifest entry points to an existing PDF
    for entry in manifest_entries:
        p = entry["relative_path"]
        if p not in discovered_pdfs:
            errors.append(f"Manifest entry '{entry['source_id']}' points to non-existent path '{p}'.")
            
    # Check: no duplicate relative paths in manifest
    manifest_paths = [entry["relative_path"] for entry in manifest_entries]
    if len(manifest_paths) != len(set(manifest_paths)):
        errors.append("Duplicate relative paths exist in the manifest.")
        
    # Check: every source_id is unique
    if len(source_ids) != len(manifest_entries):
        errors.append("Duplicate source_ids exist in the manifest.")
        
    # Check: valid folder classifications
    valid_folders = {"01_PRIMARY_KNOWLEDGE", "02_SUPPORTING_KNOWLEDGE", "03_EVALUATION_CONTEXT", "04_OUT_OF_SCOPE_INFANT", "05_REFERENCE_ONLY"}
    for entry in manifest_entries:
        fld = entry["folder"]
        if fld not in valid_folders:
            errors.append(f"Manifest entry '{entry['source_id']}' has invalid folder '{fld}'.")
            
    # Check: retrieval policy consistency & out-of-scope constraints
    for entry in manifest_entries:
        sid = entry["source_id"]
        fname = entry["file_name"]
        fld = entry["folder"]
        re_str = entry["retrieval_enabled"].lower()
        retrieval_enabled = (re_str == "true")
        
        # Enforce folder retrieval rules
        if fld == "03_EVALUATION_CONTEXT" and retrieval_enabled:
            errors.append(f"Evaluation document '{sid}' ({fname}) has retrieval_enabled=true, which is forbidden.")
        elif fld == "04_OUT_OF_SCOPE_INFANT" and retrieval_enabled:
            errors.append(f"Out-of-scope infant document '{sid}' ({fname}) has retrieval_enabled=true, which is forbidden.")
        elif fld == "05_REFERENCE_ONLY" and retrieval_enabled:
            errors.append(f"Reference-only document '{sid}' ({fname}) has retrieval_enabled=true, which is forbidden.")
            
        # Specific document overrides validation
        if fname == "WHO.pdf" and retrieval_enabled:
            errors.append(f"WHO.pdf ({sid}) covers 0-5 years and must have retrieval_enabled=false.")
            
        # Check if age range indicates out-of-scope but retrieval_enabled is true
        age_max_str = entry["age_max"]
        if age_max_str:
            try:
                age_max = float(age_max_str)
                if age_max < 5.0 and retrieval_enabled:
                    errors.append(f"Document '{sid}' ({fname}) has age_max={age_max} (under 5 years) but has retrieval_enabled=true.")
            except ValueError:
                pass
                
    # 4. Duplicate / Alternative Detection
    duplicates_detected = []
    
    # 4a. Exact MD5 duplicates
    md5_to_paths = {}
    for path, info in discovered_pdfs.items():
        h = info["md5"]
        if h:
            if h in md5_to_paths:
                md5_to_paths[h].append(path)
            else:
                md5_to_paths[h] = [path]
                
    for h, paths in md5_to_paths.items():
        if len(paths) > 1:
            warnings.append(f"Exact byte duplicate files detected (same MD5): {paths}")
            duplicates_detected.append({
                "type": "exact_md5",
                "files": paths
            })

    # 4b. Specific duplicate pair check (ref-1-txt-book.pdf and DGI_07th_May_2024_fin.pdf)
    dgi_file = "knowledge_corpus/01_PRIMARY_KNOWLEDGE/DGI_07th_May_2024_fin.pdf"
    ref1_file = "knowledge_corpus/01_PRIMARY_KNOWLEDGE/ref-1-txt-book.pdf"
    if dgi_file in discovered_pdfs and ref1_file in discovered_pdfs:
        warnings.append(f"Alternative/duplicate document version detected: '{ref1_file}' is an alternative version of '{dgi_file}' (Dietary Guidelines for Indians).")
        duplicates_detected.append({
            "type": "alternative_version",
            "primary": dgi_file,
            "alternative": ref1_file
        })
        
    # 5. Metadata fields requiring verification (missing/empty fields)
    missing_fields = []
    required_fields = ["publisher", "publication_year", "document_type", "domain"]
    for entry in manifest_entries:
        sid = entry["source_id"]
        fname = entry["file_name"]
        empty_reqs = [field for field in required_fields if not entry[field].strip()]
        
        # If age min/max are also blank
        age_blank = not entry["age_min"].strip() and not entry["age_max"].strip()
        
        if empty_reqs or age_blank:
            fields_list = empty_reqs.copy()
            if age_blank:
                fields_list.append("age_range")
            missing_fields.append({
                "source_id": sid,
                "file_name": fname,
                "fields": fields_list
            })
            
    # 6. Write Validation Report
    write_report(
        total_pdfs=total_pdfs,
        total_manifest=total_manifest,
        folder_counts=folder_counts,
        duplicates=duplicates_detected,
        missing_fields=missing_fields,
        errors=errors,
        warnings=warnings,
        output_path=validation_txt
    )

def write_report(total_pdfs, total_manifest, folder_counts, duplicates, missing_fields, errors, warnings, output_path):
    report_lines = []
    report_lines.append("============================================================")
    report_lines.append("NUTRIKID CORPUS MANIFEST VALIDATION REPORT")
    report_lines.append("============================================================")
    report_lines.append(f"Total PDFs Discovered on Disk: {total_pdfs}")
    report_lines.append(f"Total Manifest Records:        {total_manifest}")
    report_lines.append("")
    report_lines.append("Folder Counts:")
    report_lines.append(f"  01_PRIMARY_KNOWLEDGE:   {folder_counts.get('01_PRIMARY_KNOWLEDGE', 0)}")
    report_lines.append(f"  02_SUPPORTING_KNOWLEDGE: {folder_counts.get('02_SUPPORTING_KNOWLEDGE', 0)}")
    report_lines.append(f"  03_EVALUATION_CONTEXT:   {folder_counts.get('03_EVALUATION_CONTEXT', 0)}")
    report_lines.append(f"  04_OUT_OF_SCOPE_INFANT:  {folder_counts.get('04_OUT_OF_SCOPE_INFANT', 0)}")
    report_lines.append(f"  05_REFERENCE_ONLY:       {folder_counts.get('05_REFERENCE_ONLY', 0)}")
    report_lines.append("")
    
    report_lines.append("============================================================")
    report_lines.append(f"VALIDATION ERRORS ({len(errors)})")
    report_lines.append("============================================================")
    if errors:
        for err in errors:
            report_lines.append(f"[-] ERROR: {err}")
    else:
        report_lines.append("[+] No validation errors found.")
    report_lines.append("")
    
    report_lines.append("============================================================")
    report_lines.append(f"VALIDATION WARNINGS ({len(warnings)})")
    report_lines.append("============================================================")
    if warnings:
        for warn in warnings:
            report_lines.append(f"[!] WARNING: {warn}")
    else:
        report_lines.append("[+] No validation warnings found.")
    report_lines.append("")
    
    report_lines.append("============================================================")
    report_lines.append(f"DUPLICATE / ALTERNATIVE VERSIONS DETECTED ({len(duplicates)})")
    report_lines.append("============================================================")
    if duplicates:
        for d in duplicates:
            if d["type"] == "exact_md5":
                report_lines.append(f"[!] Byte duplicate files (same MD5): {', '.join(d['files'])}")
            elif d["type"] == "alternative_version":
                report_lines.append(f"[!] Alternative version: '{d['alternative']}' is a duplicate/alternative of '{d['primary']}'")
    else:
        report_lines.append("[+] No duplicates detected.")
    report_lines.append("")
    
    report_lines.append("============================================================")
    report_lines.append(f"METADATA FIELDS REQUIRING VERIFICATION ({len(missing_fields)})")
    report_lines.append("============================================================")
    if missing_fields:
        report_lines.append("The following files have empty or unverified fields:")
        for mf in missing_fields:
            report_lines.append(f"  - {mf['source_id']} ({mf['file_name']}): missing {', '.join(mf['fields'])}")
    else:
        report_lines.append("[+] All metadata fields verified.")
    report_lines.append("")
    
    # Save to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, mode='w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
        
    # Output to stdout
    print('\n'.join(report_lines))

if __name__ == '__main__':
    validate_manifest()
