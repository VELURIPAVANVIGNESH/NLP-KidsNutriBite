import csv
import os

def verify_metadata():
    manifest_csv = "data/metadata/corpus_manifest.csv"
    report_csv = "data/metadata/metadata_verification_report.csv"
    
    if not os.path.exists(manifest_csv):
        print(f"Error: Manifest file '{manifest_csv}' not found.")
        return

    # Read manifest
    rows = []
    with open(manifest_csv, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)
            
    # Track previous values for report
    previous_age_min = ""
    previous_age_max = ""
    
    # 1. Update NK-004 (What are healthy diets) to age_min=2, age_max=19 based on evidence
    for row in rows:
        if row["source_id"] == "NK-004":
            previous_age_min = row["age_min"]
            previous_age_max = row["age_max"]
            row["age_min"] = "2"
            row["age_max"] = "19"
            print(f"Updated NK-004: set age_min='2', age_max='19'.")
            
    # Write back manifest
    with open(manifest_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print("Manifest updated successfully.")

    # 2. Generate Verification Report
    report_headers = [
        "source_id", "file_name", "field", "previous_value", 
        "verified_value", "verification_status", "evidence", "notes"
    ]
    
    report_entries = [
        # NK-004
        {
            "source_id": "NK-004",
            "file_name": "9789240101876-eng.What are healthy diets.pdf",
            "field": "age_min",
            "previous_value": previous_age_min,
            "verified_value": "2",
            "verification_status": "verified",
            "evidence": "Page 11 line 14 explicitly mentions '(2-19 years of age)'",
            "notes": "Updated in manifest"
        },
        {
            "source_id": "NK-004",
            "file_name": "9789240101876-eng.What are healthy diets.pdf",
            "field": "age_max",
            "previous_value": previous_age_max,
            "verified_value": "19",
            "verification_status": "verified",
            "evidence": "Page 11 line 14 explicitly mentions '(2-19 years of age)'",
            "notes": "Updated in manifest"
        },
        # NK-010
        {
            "source_id": "NK-010",
            "file_name": "IFCT_BOOK.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "General food database listing nutrients in Indian foods (Page 27)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-010",
            "file_name": "IFCT_BOOK.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "General food database listing nutrients in Indian foods (Page 27)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-017
        {
            "source_id": "NK-017",
            "file_name": "9789240074828-engRed and processed meat in the context of h.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Broad informational brief addressing red/processed meat consumption for all age groups (Page 14)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-017",
            "file_name": "9789240074828-engRed and processed meat in the context of h.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Broad informational brief addressing red/processed meat consumption for all age groups (Page 14)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-019
        {
            "source_id": "NK-019",
            "file_name": "Dietary protein quality.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Proposes protein scoring patterns for all age groups (infants, children, adults) (Page 21, 24)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-019",
            "file_name": "Dietary protein quality.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Proposes protein scoring patterns for all age groups (infants, children, adults) (Page 21, 24)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-021
        {
            "source_id": "NK-021",
            "file_name": "Human Vitamin .pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Details nutrient recommendations for all age groups of the human population (Page 27)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-021",
            "file_name": "Human Vitamin .pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Details nutrient recommendations for all age groups of the human population (Page 27)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-022
        {
            "source_id": "NK-022",
            "file_name": "WHO-NMH-NHD-18.4-engREPLACE trans fa an action package to eliminate industrially produced trans-fatty acids.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Global policy action package targeting elimination of trans-fatty acids for all consumers (Page 6)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-022",
            "file_name": "WHO-NMH-NHD-18.4-engREPLACE trans fa an action package to eliminate industrially produced trans-fatty acids.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Global policy action package targeting elimination of trans-fatty acids for all consumers (Page 6)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-023
        {
            "source_id": "NK-023",
            "file_name": "WHO_TRS_916Diet, nutrition and the prevention of chronic diseases.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Broad guidelines for population-level diet and chronic disease prevention (Page 17)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        {
            "source_id": "NK-023",
            "file_name": "WHO_TRS_916Diet, nutrition and the prevention of chronic diseases.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Broad guidelines for population-level diet and chronic disease prevention (Page 17)",
            "notes": "Population-wide reference, age-range is not applicable"
        },
        # NK-025
        {
            "source_id": "NK-025",
            "file_name": "FR375.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Demographic national survey containing indicators for all household members (Page 8)",
            "notes": "Population-wide evaluation survey data, age-range is not applicable"
        },
        {
            "source_id": "NK-025",
            "file_name": "FR375.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Demographic national survey containing indicators for all household members (Page 8)",
            "notes": "Population-wide evaluation survey data, age-range is not applicable"
        },
        # NK-026
        {
            "source_id": "NK-026",
            "file_name": "NFHS-5_Phase-II_0.pdf",
            "field": "age_min",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Compendium of demographic survey fact sheets covering all household indicators (Page 5, 22)",
            "notes": "Population-wide evaluation survey data, age-range is not applicable"
        },
        {
            "source_id": "NK-026",
            "file_name": "NFHS-5_Phase-II_0.pdf",
            "field": "age_max",
            "previous_value": "",
            "verified_value": "",
            "verification_status": "not_found",
            "evidence": "Compendium of demographic survey fact sheets covering all household indicators (Page 5, 22)",
            "notes": "Population-wide evaluation survey data, age-range is not applicable"
        }
    ]
    
    os.makedirs(os.path.dirname(report_csv), exist_ok=True)
    with open(report_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=report_entries[0].keys())
        writer.writeheader()
        writer.writerows(report_entries)
    print(f"Verification report generated successfully at: {report_csv}")

if __name__ == '__main__':
    verify_metadata()
