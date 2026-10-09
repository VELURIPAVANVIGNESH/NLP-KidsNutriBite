// NutriKid — Real corpus data from data/metadata/corpus_manifest.csv
// Active sources only (retrieval_enabled: true)
// 22 active documents, 2403 total pages, 6422 canonical chunks

export interface CorpusSource {
  source_id: string;
  source_name: string;
  file_name: string;
  folder: string;
  publisher: string;
  publication_year: string;
  document_type: string;
  authority_tier: string;
  domain: string;
  age_min?: string;
  age_max?: string;
  retrieval_enabled: boolean;
}

export const CORPUS_SOURCES: CorpusSource[] = [
  { source_id: 'NK-001', source_name: 'Development of a WHO growth reference for school-aged children and adolescents', file_name: '07-043497.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2007', document_type: 'Journal Article', authority_tier: 'Tier 1', domain: 'Growth Standards', age_min: '5', age_max: '19', retrieval_enabled: true },
  { source_id: 'NK-002', source_name: 'Carbohydrate intake for adults and children: WHO guideline', file_name: '9789240073593-eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2023', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Macronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-003', source_name: 'Use of non-sugar sweeteners: WHO guideline', file_name: '9789240073616-eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2023', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Nutritional Recommendations', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-004', source_name: 'What are healthy diets? Joint statement by FAO and WHO', file_name: '9789240101876-eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'FAO/WHO', publication_year: '2024', document_type: 'Joint Statement', authority_tier: 'Tier 1', domain: 'General Nutrition', age_min: '2', age_max: '19', retrieval_enabled: true },
  { source_id: 'NK-005', source_name: 'Potassium intake for adults and children: WHO guideline', file_name: '9789241504829_eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2012', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Micronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-006', source_name: 'Sodium intake for adults and children: WHO guideline', file_name: '9789241504836_eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2012', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Micronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-007', source_name: 'Sugars intake for adults and children: WHO guideline', file_name: '9789241549028_eng.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2015', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Macronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-008', source_name: 'Dietary Guidelines for Indians (ICMR-NIN 2024)', file_name: 'DGI_07th_May_2024_fin.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'ICMR-NIN', publication_year: '2024', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Dietary Guidelines', age_min: '0', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-009', source_name: 'Food Safety for Children', file_name: 'Food_Safety_School_Childrens.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'FSSAI', publication_year: '2014', document_type: 'Brochure', authority_tier: 'Tier 1', domain: 'Food Safety', age_min: '5', age_max: '18', retrieval_enabled: true },
  { source_id: 'NK-010', source_name: 'Indian Food Composition Tables 2017 (IFCT)', file_name: 'IFCT_BOOK.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'ICMR-NIN', publication_year: '2017', document_type: 'Reference Book', authority_tier: 'Tier 1', domain: 'Food Composition', retrieval_enabled: true },
  { source_id: 'NK-011', source_name: 'Implementing effective actions for improving adolescent nutrition: WHO guideline', file_name: 'Implementing effective-adolscent.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2018', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Adolescent Nutrition', age_min: '10', age_max: '19', retrieval_enabled: true },
  { source_id: 'NK-012', source_name: 'Policies and interventions to create healthy school food environments: WHO guideline', file_name: 'PoliciesandinterventionsWHOguideline.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2025', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'School Food Environments', age_min: '5', age_max: '19', retrieval_enabled: true },
  { source_id: 'NK-013', source_name: 'Total fat intake for prevention of unhealthy weight gain: WHO guideline', file_name: 'Totalfatintakefortheadults.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'WHO', publication_year: '2023', document_type: 'Guideline', authority_tier: 'Tier 1', domain: 'Macronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-015', source_name: 'A Brief Note on Nutrient Requirements for Indians — RDA and EAR (ICMR-NIN 2020)', file_name: 'brief_note.pdf', folder: '01_PRIMARY_KNOWLEDGE', publisher: 'ICMR-NIN', publication_year: '2020', document_type: 'Reference Document', authority_tier: 'Tier 1', domain: 'Recommended Dietary Allowances', age_min: '0', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-017', source_name: 'Red and processed meat in the context of health and the environment: information brief', file_name: '9789240074828-eng.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'WHO', publication_year: '2023', document_type: 'Information Brief', authority_tier: 'Tier 2', domain: 'Nutritional Recommendations', retrieval_enabled: true },
  { source_id: 'NK-018', source_name: 'Use of lower-sodium salt substitutes: WHO guideline', file_name: '9789240105591-eng.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'WHO', publication_year: '2025', document_type: 'Guideline', authority_tier: 'Tier 2', domain: 'Macronutrient Intake', age_min: '2', age_max: '99', retrieval_enabled: true },
  { source_id: 'NK-019', source_name: 'Dietary protein quality evaluation in human nutrition: FAO Expert Consultation', file_name: 'Dietary protein quality.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'FAO', publication_year: '2013', document_type: 'Report', authority_tier: 'Tier 2', domain: 'Macronutrient Intake', retrieval_enabled: true },
  { source_id: 'NK-020', source_name: 'Global Accelerated Action for the Health of Adolescents (AA-HA!) — 2nd Edition', file_name: 'AA-HA! - Second edition.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'WHO', publication_year: '2023', document_type: 'Guideline', authority_tier: 'Tier 2', domain: 'Adolescent Health', age_min: '10', age_max: '19', retrieval_enabled: true },
  { source_id: 'NK-021', source_name: 'Human Vitamin and Mineral Requirements: FAO/WHO Expert Consultation Report', file_name: 'Human Vitamin.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'FAO/WHO', publication_year: '2004', document_type: 'Report', authority_tier: 'Tier 2', domain: 'Nutritional Recommendations', retrieval_enabled: true },
  { source_id: 'NK-022', source_name: 'REPLACE trans fat: Action package to eliminate industrially produced trans-fatty acids', file_name: 'WHO-NMH-NHD-18.4-eng.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'WHO', publication_year: '2018', document_type: 'Report', authority_tier: 'Tier 2', domain: 'Food Safety', retrieval_enabled: true },
  { source_id: 'NK-023', source_name: 'Diet, nutrition and prevention of chronic diseases: WHO/FAO Expert Consultation', file_name: 'WHO_TRS_916.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'WHO', publication_year: '2003', document_type: 'Report', authority_tier: 'Tier 2', domain: 'General Nutrition', retrieval_enabled: true },
  { source_id: 'NK-024', source_name: 'Report of the Expert Group on Fat, Sugar and Salt and health impacts on Indian population', file_name: 'ref-2-txt-book-1.pdf', folder: '02_SUPPORTING_KNOWLEDGE', publisher: 'FSSAI', publication_year: '2017', document_type: 'Expert Group Report', authority_tier: 'Tier 2', domain: 'Nutrition Policy', age_min: '5', age_max: '17', retrieval_enabled: true },
];

// Verified corpus statistics from preprocessor_summary.txt and parser_summary.txt
export const CORPUS_STATS = {
  active_documents: 22,
  total_pages: 2403,
  canonical_chunks: 6422,
  embedding_model: 'BAAI/bge-small-en-v1.5',
  reranker_model: 'BAAI/bge-reranker-base',
  generation_model: 'Qwen/Qwen2.5-1.5B-Instruct',
  bm25_vocabulary: 33038,
  age_scope_min: 5.0,
  age_scope_max: 15.0,
  retrieval_mode: 'BM25 + FAISS Dense + RRF (k=60)',
  faiss_index_type: 'IndexFlatIP (Cosine Similarity)',
  rrf_k: 60,
};

// Real retrieval benchmark metrics from retrieval_benchmark_summary.txt + reranking_summary.md
export const RETRIEVAL_METRICS = {
  benchmark_queries: 30,
  bm25: { mrr: 0.0958, map: 0.0629, ndcg5: 0.0839, recall5: 0.1167 },
  dense: { mrr: 0.1884, map: 0.1123, ndcg5: 0.1310, recall5: 0.1500 },
  hybrid_rrf: { mrr: 0.1423, map: 0.0987, ndcg5: 0.1378, recall5: 0.2167 },
  reranked_bge: { mrr: 0.2751, map: 0.1644, ndcg5: 0.2289, recall5: 0.2500 },
  mrr_improvement_vs_hybrid: 93.29,
};

// Real generation ROUGE metrics from rouge_evaluation_results.json (5 queries)
export const GENERATION_METRICS = {
  n_queries: 5,
  avg_rouge1: 0.4011,
  avg_rouge2: 0.1424,
  avg_rougeL: 0.2583,
};
