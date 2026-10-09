'use client';

import { useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { CORPUS_STATS } from '@/lib/corpus';

const PIPELINE_STAGES = [
  {
    id: 'S01',
    stage: '01',
    label: 'Source Corpus Ingestion',
    icon: 'folder_open',
    color: 'var(--on-surface-variant)',
    purpose: 'Loads 22 active PDF documents from institutional sources (WHO, ICMR-NIN, FAO, FSSAI) into the preprocessing pipeline.',
    model: 'PDF text extraction (pdfminer)',
    algorithm: 'Structural parsing with empty-page detection',
    module: 'preprocessing/parse_documents.py',
    inputs: ['Raw PDF files', 'corpus_manifest.csv'],
    outputs: ['Parsed text per page', 'parser_summary.txt'],
    stats: `${CORPUS_STATS.active_documents} active docs · ${CORPUS_STATS.total_pages.toLocaleString()} pages · 6,014,229 chars extracted`,
  },
  {
    id: 'S02',
    stage: '02',
    label: 'Domain-Aware Chunking',
    icon: 'content_cut',
    color: 'var(--chart-accent)',
    purpose: 'Applies domain-specific chunking strategies: 1,000-char target, 200-char overlap for prose; 6-row per chunk for IFCT food composition tables.',
    model: 'Rule-based chunker with IFCT table specialization',
    algorithm: 'Sliding window (1000/200) + structured table chunker',
    module: 'preprocessing/chunk_documents.py',
    inputs: ['Parsed page text', 'config.json (chunk params)'],
    outputs: ['6,422 canonical chunks', 'chunker_report.csv'],
    stats: 'Chunk target: 1000 chars · Max: 1400 · Overlap: 200 · IFCT rows: 6/chunk',
  },
  {
    id: 'S03',
    stage: '03',
    label: 'Sparse BM25 Indexing',
    icon: 'sort',
    color: 'var(--secondary)',
    purpose: 'Builds a BM25 Okapi index over all 6,422 chunks for exact-term retrieval, particularly effective on RDA numeric tables and structured nutritional data.',
    model: 'BM25 Okapi (rank_bm25)',
    algorithm: 'BM25 (k1=1.5, b=0.75)',
    module: 'preprocessing/preprocess_knowledge.py',
    inputs: ['6,422 canonical chunks'],
    outputs: ['bm25_index.json', '33,038-term vocabulary'],
    stats: 'k1=1.5 · b=0.75 · Vocabulary: 33,038 terms',
  },
  {
    id: 'S04',
    stage: '04',
    label: 'Dense FAISS Embedding',
    icon: 'device_hub',
    color: 'var(--primary-container)',
    purpose: 'Embeds all 6,422 chunks using BAAI/bge-small-en-v1.5 (384-dim) and stores in a FAISS IndexFlatIP index for cosine similarity retrieval.',
    model: 'BAAI/bge-small-en-v1.5 (384d)',
    algorithm: 'FAISS IndexFlatIP (Exact Inner Product = Cosine on normalized vectors)',
    module: 'preprocessing/preprocess_knowledge.py → rebuild_dense_index.py',
    inputs: ['6,422 canonical chunks'],
    outputs: ['dense_index.faiss (9.8 MB)', 'dense_index_map.json'],
    stats: '384-dim embeddings · 6,422 vectors · 0 NaN/Inf detected',
  },
  {
    id: 'S05',
    stage: '05',
    label: 'Hybrid RRF Retrieval',
    icon: 'merge',
    color: 'var(--surgical-blue)',
    purpose: 'At inference time, runs both BM25 and FAISS retrieval independently and fuses rankings with Reciprocal Rank Fusion (k=60) to produce a unified candidate pool.',
    model: 'Reciprocal Rank Fusion',
    algorithm: 'RRF score = Σ 1/(k + rank_i) where k=60',
    module: 'preprocessing/retrieve.py',
    inputs: ['User query', 'BM25 index', 'FAISS index'],
    outputs: ['Top-50 hybrid-ranked candidates with RRF scores'],
    stats: 'RRF k=60 · Candidate pool: 50 · Hybrid MRR: 0.1423',
  },
  {
    id: 'S06',
    stage: '06',
    label: 'Cross-Encoder Reranking',
    icon: 'model_training',
    color: 'var(--primary-container)',
    purpose: 'Applies BAAI/bge-reranker-base cross-encoder to re-score the top-50 RRF candidates and select the top-5 most relevant passages for context construction.',
    model: 'BAAI/bge-reranker-base (cross-encoder)',
    algorithm: 'Full query-document attention scoring via BERT-style cross-encoder',
    module: 'preprocessing/rerank.py',
    inputs: ['Query', 'Top-50 RRF candidates'],
    outputs: ['Top-5 reranked passages with cross-encoder scores'],
    stats: 'MRR: 0.2751 (+93.29% vs Hybrid RRF) · Recall@5: 0.25',
  },
  {
    id: 'S07',
    stage: '07',
    label: 'Evidence-Grounded Generation',
    icon: 'memory',
    color: 'var(--ice-glow)',
    purpose: 'Constructs a structured prompt with the top-5 evidence passages and feeds it to Qwen2.5-1.5B-Instruct running locally on CPU. Strict system instructions prevent hallucination.',
    model: 'Qwen/Qwen2.5-1.5B-Instruct (local, CPU)',
    algorithm: 'Constrained causal LM generation (temp=0.1, max_new_tokens=512)',
    module: 'generation/qwen_generator.py',
    inputs: ['System prompt', 'Top-5 evidence passages', 'Child age', 'Query'],
    outputs: ['Raw generated answer with inline source references'],
    stats: 'Temp: 0.1 · Top-p: 0.9 · Top-k: 50 · Max new tokens: 512',
  },
  {
    id: 'S08',
    stage: '08',
    label: 'Nutrient Fidelity Validation',
    icon: 'verified',
    color: 'var(--confidence-high)',
    purpose: 'Applies deterministic post-generation validation to detect and block nutrient unit cross-contamination (e.g., preventing µg/day iodine values from being presented as protein RDA in grams).',
    model: 'Rule-based NutrientFidelityGuard',
    algorithm: 'Regex-based unit detection + nutrient-specific cross-contamination rules',
    module: 'generation/nutrient_fidelity_guard.py',
    inputs: ['Raw generated answer', 'Original query', 'Child age'],
    outputs: ['Validated answer or override message', 'fidelity_check metadata'],
    stats: 'Guards: protein/iron/calcium/vitamin cross-contamination · GEN001 fix applied',
  },
];

export default function PipelinePage() {
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (id: string) => setExpanded(prev => prev === id ? null : id);

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '40px 24px' }}>

          {/* Page header */}
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <span className="badge badge-primary" style={{ marginBottom: 12 }}>RAG Architecture</span>
            <h1 className="text-headline-xl" style={{ color: 'var(--on-surface)', marginBottom: 16, marginTop: 8 }}>
              NutriKid 8-Stage Clinical RAG Pipeline
            </h1>
            <p className="text-body-lg" style={{ color: 'var(--on-surface-variant)', maxWidth: 700, margin: '0 auto', lineHeight: 1.7 }}>
              A deterministic, evidence-grounded retrieval-augmented generation pipeline purpose-built for pediatric nutrition.
              Click any stage to inspect its configuration, models, and real implementation modules.
            </p>
          </div>

          {/* Pipeline summary strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 40, padding: '20px 24px', backgroundColor: 'var(--surface-raised)', borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
            {[
              { label: 'Canonical Chunks', value: CORPUS_STATS.canonical_chunks.toLocaleString(), color: 'var(--primary-container)' },
              { label: 'BM25 Vocabulary', value: '33,038', color: 'var(--secondary)' },
              { label: 'Embedding Dim', value: '384', color: 'var(--chart-accent)' },
              { label: 'RRF k', value: '60', color: 'var(--surgical-blue)' },
              { label: 'Reranked MRR', value: '0.2751', color: 'var(--confidence-high)' },
              { label: 'ROUGE-1 (Avg)', value: '0.4011', color: 'var(--primary-container)' },
            ].map((s) => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div className="metric-value" style={{ fontSize: 20, color: s.color }}>{s.value}</div>
                <div className="metric-label" style={{ fontSize: 10, marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Pipeline stages — full-width expandable cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {PIPELINE_STAGES.map((stage, i) => {
              const isOpen = expanded === stage.id;
              return (
                <div
                  key={stage.id}
                  style={{
                    backgroundColor: 'var(--surface-raised)',
                    borderTop: `1px solid ${isOpen ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    borderRight: `1px solid ${isOpen ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    borderBottom: `1px solid ${isOpen ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    borderLeft: `3px solid ${stage.color}`,
                    borderRadius: 10,
                    overflow: 'hidden',
                    transition: 'border-color 0.2s ease',
                  }}
                >
                  {/* Stage header — always visible */}
                  <button
                    onClick={() => toggle(stage.id)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 16,
                      padding: '16px 20px',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    {/* Stage number */}
                    <span className="font-mono" style={{ fontSize: 11, fontWeight: 700, color: 'var(--on-surface-variant)', minWidth: 60, letterSpacing: '0.04em' }}>
                      STAGE {stage.stage}
                    </span>

                    {/* Icon */}
                    <div style={{ width: 36, height: 36, borderRadius: 8, backgroundColor: 'var(--surface-container)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: stage.color }}>{stage.icon}</span>
                    </div>

                    {/* Label */}
                    <div style={{ flex: 1 }}>
                      <span className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)', display: 'block' }}>{stage.label}</span>
                      <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{stage.stats}</span>
                    </div>

                    {/* Module badge */}
                    <span className="badge badge-citation" style={{ fontSize: 9, display: 'block' }}>
                      {stage.module.split('/').pop()}
                    </span>

                    {/* Expand icon */}
                    <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--on-surface-variant)', transition: 'transform 0.2s ease', transform: isOpen ? 'rotate(180deg)' : 'rotate(0)' }}>
                      expand_more
                    </span>
                  </button>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border-subtle)', marginTop: 0, paddingTop: 20 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>

                        {/* Purpose */}
                        <div>
                          <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.06em' }}>PURPOSE</span>
                          <p className="text-body-sm" style={{ color: 'var(--on-surface)', lineHeight: 1.65 }}>{stage.purpose}</p>
                        </div>

                        {/* Model + Algorithm */}
                        <div>
                          <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.06em' }}>MODEL / ALGORITHM</span>
                          <span className="font-mono text-label-code" style={{ fontSize: 12, color: stage.color, display: 'block', marginBottom: 4 }}>{stage.model}</span>
                          <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{stage.algorithm}</span>
                        </div>

                        {/* Implementation module */}
                        <div>
                          <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.06em' }}>IMPLEMENTATION MODULE</span>
                          <span className="badge badge-citation" style={{ fontSize: 11 }}>{stage.module}</span>
                        </div>

                        {/* I/O */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                          <div>
                            <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 6, letterSpacing: '0.06em' }}>INPUTS</span>
                            {stage.inputs.map((inp) => (
                              <div key={inp} style={{ display: 'flex', alignItems: 'flex-start', gap: 5, marginBottom: 3 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--secondary)', marginTop: 1 }}>arrow_right</span>
                                <span className="text-body-sm" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>{inp}</span>
                              </div>
                            ))}
                          </div>
                          <div>
                            <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 6, letterSpacing: '0.06em' }}>OUTPUTS</span>
                            {stage.outputs.map((out) => (
                              <div key={out} style={{ display: 'flex', alignItems: 'flex-start', gap: 5, marginBottom: 3 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 12, color: stage.color, marginTop: 1 }}>arrow_right</span>
                                <span className="text-body-sm" style={{ fontSize: 11, color: 'var(--on-surface)' }}>{out}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Architecture diagram note */}
          <div style={{ marginTop: 40, padding: '24px 28px', backgroundColor: 'var(--surface-raised)', borderRadius: 12, border: '1px solid var(--border-subtle)', display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 24, color: 'var(--secondary)', flexShrink: 0 }}>info</span>
            <div>
              <h3 className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 8 }}>Pipeline Integrity</h3>
              <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.7, marginBottom: 10 }}>
                The retrieval pipeline is frozen and deterministic. Two consecutive evaluations on the same 30-query benchmark produce 100% identical rankings (verified via MD5 checksums on all 77 frozen baseline assets). The pipeline uses CPU-only execution for reproducibility across hardware.
              </p>
              <Link href="/evaluation" className="btn-ghost" style={{ padding: '6px 0', fontSize: 12 }}>
                View full benchmark evaluation
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>arrow_forward</span>
              </Link>
            </div>
          </div>
        </div>

        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '16px 24px', textAlign: 'center', marginTop: 40 }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            NUTRIKID 8-STAGE RAG PIPELINE · BM25 + FAISS + RRF + BGE RERANKER + QWEN2.5 + NUTRIENT FIDELITY GUARD
          </p>
        </footer>
      </main>
    </>
  );
}
