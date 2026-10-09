// Shared TypeScript types for NutriKid

export interface Evidence {
  chunk_id: string;
  score: number;
  text: string;
  source: string;
  page_numbers?: number[];
}

export interface Citation {
  chunk_id: string;
  source: string;
  title: string;
  page_numbers?: number[];
}

export interface FidelityCheck {
  passed: boolean;
  triggered_rules?: string[];
  explanation?: string;
}

export interface GenerationMetadata {
  model?: string;
  active_model?: string;
  temperature?: number;
  max_new_tokens?: number;
  do_sample?: boolean;
  [key: string]: unknown;
}

export interface AskResult {
  query: string;
  child_age: number;
  scope_status: string;
  status: string;
  answer: string;
  citations: Citation[];
  evidence: Evidence[];
  generation_metadata?: GenerationMetadata;
  fidelity_check?: FidelityCheck;
}

export interface SearchResultMetadata {
  source: string;
  source_name: string;
  page: string | number;
  title?: string;
  chunk_index?: number;
  [key: string]: unknown;
}

export interface SearchResult {
  chunk_id: string;
  score: number;
  text: string;
  metadata: SearchResultMetadata;
}

export interface SearchResponse {
  backend: string;
  query: string;
  k: number;
  results: SearchResult[];
}

export interface HealthResponse {
  status: string;
  message: string;
}

// Corpus source type (from manifest)
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
  retrieval_enabled: string;
}
