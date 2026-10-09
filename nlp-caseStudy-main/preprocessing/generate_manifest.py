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
        return f"Error: {e}"

def generate_manifest():
    root_dir = "knowledge_corpus"
    output_csv = "data/metadata/corpus_manifest.csv"
    
    # Base folder configurations
    folder_tiers = {
        "01_PRIMARY_KNOWLEDGE": "Tier 1",
        "02_SUPPORTING_KNOWLEDGE": "Tier 2",
        "03_EVALUATION_CONTEXT": "Tier 3",
        "04_OUT_OF_SCOPE_INFANT": "Tier 4",
        "05_REFERENCE_ONLY": "Tier 5"
    }
    
    folder_retrieval = {
        "01_PRIMARY_KNOWLEDGE": "true",
        "02_SUPPORTING_KNOWLEDGE": "true",
        "03_EVALUATION_CONTEXT": "false",
        "04_OUT_OF_SCOPE_INFANT": "false",
        "05_REFERENCE_ONLY": "false"
    }

    # Explicit verified metadata mapping for the 32 documents
    # Keyed by filename to avoid path issues
    metadata_map = {
        "07-043497.pdf": {
            "source_name": "Development of a WHO growth reference for school-aged children and adolescents",
            "publisher": "WHO",
            "publication_year": "2007",
            "document_type": "Journal Article",
            "domain": "Growth Standards",
            "age_min": "5",
            "age_max": "19",
            "retrieval_enabled_override": None
        },
        "9789240073593-engCarbohydrate intake for adults and childrenWHO guideline.pdf": {
            "source_name": "Carbohydrate intake for adults and children: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Guideline",
            "domain": "Macronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "9789240073616-engUse of non-sugar sweetenersWHO guideline.pdf": {
            "source_name": "Use of non-sugar sweeteners: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Guideline",
            "domain": "Nutritional Recommendations",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "9789240101876-eng.What are healthy diets.pdf": {
            "source_name": "What are healthy diets? Joint statement by FAO and WHO",
            "publisher": "FAO/WHO",
            "publication_year": "2024",
            "document_type": "Joint Statement",
            "domain": "General Nutrition",
            "age_min": "2",
            "age_max": "19",
            "retrieval_enabled_override": None
        },
        "9789241504829_engGuidelinepotassium intake for adults and children.pdf": {
            "source_name": "Potassium intake for adults and children: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2012",
            "document_type": "Guideline",
            "domain": "Micronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "9789241504836_engGuidelinesodium intake for adults and children.pdf": {
            "source_name": "Sodium intake for adults and children: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2012",
            "document_type": "Guideline",
            "domain": "Micronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "9789241549028_engGuidelinesugars intake for adults and children.pdf": {
            "source_name": "Sugars intake for adults and children: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2015",
            "document_type": "Guideline",
            "domain": "Macronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "brief_note.pdf": {
            "source_name": "A Brief Note on Nutrient Requirements for Indians, Recommended Dietary Allowances (RDA) and Estimated Average Requirements (EAR)",
            "publisher": "ICMR-NIN",
            "publication_year": "2020",
            "document_type": "Reference Document",
            "domain": "Recommended Dietary Allowances",
            "age_min": "0",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "DGI_07th_May_2024_fin.pdf": {
            "source_name": "Dietary Guidelines for Indians",
            "publisher": "ICMR-NIN",
            "publication_year": "2024",
            "document_type": "Guideline",
            "domain": "Dietary Guidelines",
            "age_min": "0",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "Food_Safety_School_Childrens.pdf": {
            "source_name": "Food Safety for Children",
            "publisher": "FSSAI",
            "publication_year": "2014",
            "document_type": "Brochure",
            "domain": "Food Safety",
            "age_min": "5",
            "age_max": "18",
            "retrieval_enabled_override": None
        },
        "IFCT_BOOK.pdf": {
            "source_name": "Indian Food Composition Tables 2017",
            "publisher": "ICMR-NIN",
            "publication_year": "2017",
            "document_type": "Reference Book",
            "domain": "Food Composition",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "Implementing effective-adolscent.pdf": {
            "source_name": "Implementing effective actions for improving adolescent nutrition: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2018",
            "document_type": "Guideline",
            "domain": "Adolescent Nutrition",
            "age_min": "10",
            "age_max": "19",
            "retrieval_enabled_override": None
        },
        "PoliciesandinterventionstocreatehealthyschoolfoodenvironmentsWHOguideline.pdf": {
            "source_name": "Policies and interventions to create healthy school food environments: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2025",
            "document_type": "Guideline",
            "domain": "School Food Environments",
            "age_min": "5",
            "age_max": "19",
            "retrieval_enabled_override": None
        },
        "ref-1-txt-book.pdf": {
            "source_name": "Dietary Guidelines for Indians (Alternative Print Version)",
            "publisher": "ICMR-NIN",
            "publication_year": "2024",
            "document_type": "Guideline",
            "domain": "Dietary Guidelines",
            "age_min": "0",
            "age_max": "99",
            "retrieval_enabled_override": "false"  # Explicitly disabled as duplicate content of DGI_07th_May_2024_fin.pdf
        },
        "Totalfatintakefortheadults.pdf": {
            "source_name": "Total fat intake for the prevention of unhealthy weight gain in adults and children: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Guideline",
            "domain": "Macronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "WHO.pdf": {
            "source_name": "WHO Child Growth Standards (0-5 years) methods and development",
            "publisher": "WHO",
            "publication_year": "2006",
            "document_type": "Reference Standard",
            "domain": "Growth Standards",
            "age_min": "0",
            "age_max": "5",
            "retrieval_enabled_override": "false"  # Under-5 years is OUT OF SCOPE for RAG retrieval
        },
        
        # Folder 02: SUPPORTING KNOWLEDGE
        "9789240074828-engRed and processed meat in the context of h.pdf": {
            "source_name": "Red and processed meat in the context of health and the environment: information brief",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Information Brief",
            "domain": "Nutritional Recommendations",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "9789240105591-engUse of lower-sodium salt substitutesWHO guideline ﻿.pdf": {
            "source_name": "Use of lower-sodium salt substitutes: WHO guideline",
            "publisher": "WHO",
            "publication_year": "2025",
            "document_type": "Guideline",
            "domain": "Macronutrient Intake",
            "age_min": "2",
            "age_max": "99",
            "retrieval_enabled_override": None
        },
        "Dietary protein quality.pdf": {
            "source_name": "Dietary protein quality evaluation in human nutrition: Report of an FAO Expert Consultation",
            "publisher": "FAO",
            "publication_year": "2013",
            "document_type": "Report",
            "domain": "Macronutrient Intake",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "Global Accelerated Action for the Health of Adolescents (AA-HA!) - Second edition.pdf": {
            "source_name": "Global Accelerated Action for the Health of Adolescents (AA-HA!): Guidance to Support Country Implementation",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Guideline",
            "domain": "Adolescent Health",
            "age_min": "10",
            "age_max": "19",
            "retrieval_enabled_override": None
        },
        "Human Vitamin .pdf": {
            "source_name": "Human Vitamin and Mineral Requirements: Report of a joint FAO/WHO expert consultation",
            "publisher": "FAO/WHO",
            "publication_year": "2004",
            "document_type": "Report",
            "domain": "Nutritional Recommendations",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "ref-2-txt-book-1.pdf": {
            "source_name": "Report of the Expert Group on Consumption of Fat, Sugar and Salt and its health impacts on Indian population",
            "publisher": "FSSAI",
            "publication_year": "2017",
            "document_type": "Expert Group Report",
            "domain": "Nutrition Policy",
            "age_min": "5",
            "age_max": "17",
            "retrieval_enabled_override": None
        },
        "WHO-NMH-NHD-18.4-engREPLACE trans fa an action package to eliminate industrially produced trans-fatty acids.pdf": {
            "source_name": "REPLACE trans fat: an action package to eliminate industrially produced trans-fatty acids",
            "publisher": "WHO",
            "publication_year": "2018",
            "document_type": "Report",
            "domain": "Food Safety",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "WHO_TRS_916Diet, nutrition and the prevention of chronic diseases.pdf": {
            "source_name": "Diet, nutrition and the prevention of chronic diseases: Report of a Joint WHO/FAO Expert Consultation",
            "publisher": "WHO",
            "publication_year": "2003",
            "document_type": "Report",
            "domain": "General Nutrition",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        
        # Folder 03: EVALUATION CONTEXT
        "FR375.pdf": {
            "source_name": "National Family Health Survey (NFHS-5), 2019-21: India Report",
            "publisher": "IIPS",
            "publication_year": "2022",
            "document_type": "Survey Report",
            "domain": "Dietary Assessment",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        "NFHS-5_Phase-II_0.pdf": {
            "source_name": "National Family Health Survey (NFHS-5), 2019-21: Compendium of Fact Sheets India and 14 States/UTs (Phase-II)",
            "publisher": "IIPS",
            "publication_year": "2021",
            "document_type": "Survey Report",
            "domain": "Dietary Assessment",
            "age_min": "",
            "age_max": "",
            "retrieval_enabled_override": None
        },
        
        # Folder 04: OUT OF SCOPE INFANT
        "6-23months.pdf": {
            "source_name": "WHO Guideline for complementary feeding of infants and young children 6–23 months of age",
            "publisher": "WHO",
            "publication_year": "2023",
            "document_type": "Guideline",
            "domain": "Pediatric Nutrition",
            "age_min": "0.5",
            "age_max": "1.92",
            "retrieval_enabled_override": None
        },
        "9789240018389-eng.pdf": {
            "source_name": "Indicators for assessing infant and young child feeding practices: definitions and measurement methods",
            "publisher": "WHO/UNICEF",
            "publication_year": "2021",
            "document_type": "Reference Standard",
            "domain": "Pediatric Nutrition",
            "age_min": "0",
            "age_max": "2",
            "retrieval_enabled_override": None
        },
        "acta-paediatrica-supplement-on-the-who-child-growth-standards.pdf": {
            "source_name": "WHO Child Growth Standards: Supplement to Acta Paediatrica",
            "publisher": "WHO",
            "publication_year": "2006",
            "document_type": "Journal Supplement",
            "domain": "Growth Standards",
            "age_min": "0",
            "age_max": "5",
            "retrieval_enabled_override": None
        },
        "Flip_Chart_English.pdf": {
            "source_name": "Counselling Guide: Towards Complete Development of a Child - Infant and Young Child Feeding",
            "publisher": "NHM",
            "publication_year": "2016",
            "document_type": "Counselling Guide",
            "domain": "Pediatric Nutrition",
            "age_min": "0",
            "age_max": "2",
            "retrieval_enabled_override": None
        },
        "Infant and young child feeding.pdf": {
            "source_name": "Infant and young child feeding: Model Chapter for textbooks for medical students and allied health professionals",
            "publisher": "WHO",
            "publication_year": "2009",
            "document_type": "Reference Book",
            "domain": "Pediatric Nutrition",
            "age_min": "0",
            "age_max": "2",
            "retrieval_enabled_override": None
        },
        "nutrition-and-child-development-4nbsped-9788181913111-8181913116_compress (1).pdf": {
            "source_name": "Nutrition and Child Development (4th Edition)",
            "publisher": "Paras Medical Publisher",
            "publication_year": "2014",
            "document_type": "Reference Book",
            "domain": "Pediatric Nutrition",
            "age_min": "0",
            "age_max": "18",
            "retrieval_enabled_override": None
        }
    }

    # Discover files physically on disk
    discovered_files = []
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith('.pdf'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ".").replace('\\', '/')
                folder = os.path.basename(root)
                discovered_files.append((f, rel_path, folder, full_path))
                
    # Sort files to ensure deterministic source ID generation
    discovered_files.sort(key=lambda x: (x[2], x[0]))

    # Ensure output folder exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    print(f"Discovered {len(discovered_files)} PDF files on disk.")

    # Write manifest CSV
    headers = [
        "source_id", "source_name", "file_name", "relative_path", "folder", 
        "publisher", "publication_year", "document_type", "authority_tier", 
        "domain", "age_min", "age_max", "retrieval_enabled"
    ]
    
    rows = []
    id_counter = 1
    
    for fname, rel_path, folder, full_path in discovered_files:
        source_id = f"NK-{id_counter:03d}"
        id_counter += 1
        
        # Lookup metadata map
        meta = metadata_map.get(fname, {})
        
        source_name = meta.get("source_name", "")
        publisher = meta.get("publisher", "")
        publication_year = meta.get("publication_year", "")
        document_type = meta.get("document_type", "")
        domain = meta.get("domain", "")
        age_min = meta.get("age_min", "")
        age_max = meta.get("age_max", "")
        
        authority_tier = folder_tiers.get(folder, "Tier 5")
        
        # Default retrieval setting based on folder
        ret_val = folder_retrieval.get(folder, "false")
        # Check override
        override = meta.get("retrieval_enabled_override", None)
        if override is not None:
            ret_val = override
            
        row = {
            "source_id": source_id,
            "source_name": source_name,
            "file_name": fname,
            "relative_path": rel_path,
            "folder": folder,
            "publisher": publisher,
            "publication_year": publication_year,
            "document_type": document_type,
            "authority_tier": authority_tier,
            "domain": domain,
            "age_min": age_min,
            "age_max": age_max,
            "retrieval_enabled": ret_val
        }
        rows.append(row)
        
    with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
            
    print(f"Successfully generated corpus_manifest.csv with {len(rows)} entries.")

if __name__ == '__main__':
    generate_manifest()
