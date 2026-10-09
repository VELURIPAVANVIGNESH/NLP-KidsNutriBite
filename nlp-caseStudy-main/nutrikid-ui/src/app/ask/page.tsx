'use client';

import { useState, useRef } from 'react';
import Navbar from '@/components/Navbar';
import { api, APIError } from '@/lib/api';
import type { AskResult, Citation, Evidence } from '@/lib/types';
import { CORPUS_STATS } from '@/lib/corpus';

const PRESET_QUERIES = [
  { label: 'Protein intake for 10y (ICMR-NIN)', age: 10, query: 'Recommended protein intake for 10-year-old child (ICMR-NIN RDA)' },
  { label: 'Calcium RDA for 12y girl', age: 12, query: 'Calcium RDA for 12-year-old girl and rich dietary sources' },
  { label: 'Iron requirements for 7y', age: 7, query: 'Iron requirements and bioavailability factors for 7-year-old child' },
  { label: 'Vitamin A UL vs RDA for 14y boy', age: 14, query: 'Vitamin A safe upper limit vs RDA for 14-year-old boy' },
  { label: 'Added sugar guidelines for 9y', age: 9, query: 'WHO guidelines on added sugar intake for school-age children 9 years' },
  { label: '[Test Refusal] 2y toddler', age: 2, query: 'Protein requirements for 2-year-old toddler', isEdge: true },
];

const LOADING_STAGES = [
  { key: 'scope', label: 'Validating age scope (5.0–15.0 years)' },
  { key: 'retrieve', label: 'Searching evidence corpus (BM25 + FAISS)' },
  { key: 'rerank', label: 'Neural reranking via bge-reranker-base' },
  { key: 'generate', label: 'Synthesizing grounded response (Qwen2.5)' },
  { key: 'validate', label: 'Nutrient fidelity validation' },
];

function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className="citation-card-item"
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: expanded ? 8 : 0 }}>
        <span className="badge badge-citation">[{citation.chunk_id || `REF-${index + 1}`}]</span>
        {citation.source && (
          <span className="font-mono text-label-code" style={{ fontSize: 11, color: 'var(--surgical-blue)', fontWeight: 600 }}>{citation.source}</span>
        )}
        {citation.page_numbers && citation.page_numbers.length > 0 && (
          <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
            pp. {citation.page_numbers.join(', ')}
          </span>
        )}
        <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--on-surface-variant)', marginLeft: 'auto' }}>
          {expanded ? 'expand_less' : 'expand_more'}
        </span>
      </div>
      {expanded && citation.title && (
        <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', marginTop: 4 }}>
          {citation.title}
        </p>
      )}
    </div>
  );
}

function EvidenceCard({ ev, index }: { ev: Evidence; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const PREVIEW_LENGTH = 300;
  const isLong = ev.text.length > PREVIEW_LENGTH;

  return (
    <div className="evidence-card animate-slide-up" style={{ animationDelay: `${index * 60}ms` }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <span className="badge badge-primary" style={{ fontSize: 10 }}>#{index + 1}</span>
        <span className="font-mono text-label-code" style={{ fontSize: 11, fontWeight: 700, color: 'var(--citation-text)' }}>{ev.chunk_id}</span>
        {ev.source && (
          <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>· {ev.source}</span>
        )}
        {ev.page_numbers && ev.page_numbers.length > 0 && (
          <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            pp. {ev.page_numbers.join(', ')}
          </span>
        )}
        {ev.score > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}>
            <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
              Score: {ev.score.toFixed(4)}
            </span>
            <div className="progress-track" style={{ width: 56, height: 4 }}>
              <div className="progress-fill primary" style={{ width: `${Math.min(ev.score * 100, 100)}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Evidence text */}
      <p className="text-body-sm" style={{ color: 'var(--on-surface)', lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
        {expanded || !isLong ? ev.text : `${ev.text.slice(0, PREVIEW_LENGTH)}…`}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ marginTop: 8, background: 'none', border: 'none', color: 'var(--secondary)', fontSize: 12, cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>{expanded ? 'expand_less' : 'expand_more'}</span>
          {expanded ? 'Show less' : 'Show full passage'}
        </button>
      )}
    </div>
  );
}

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [age, setAge] = useState('10');
  const [result, setResult] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [streamingText, setStreamingText] = useState('');
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'answer' | 'citations' | 'evidence'>('answer');
  const resultRef = useRef<HTMLDivElement>(null);

  const ageNum = parseFloat(age);
  const ageValid = !isNaN(ageNum);
  const ageInScope = ageValid && ageNum >= 5.0 && ageNum <= 15.0;

  const handleAsk = async () => {
    if (!question.trim()) { setError('Please enter a clinical nutrition question.'); return; }
    if (!ageValid) { setError('Please enter a valid child age (numeric value).'); return; }

    setLoading(true);
    setError('');
    setResult(null);
    setStreamingText('');
    setLoadingStage(0);

    try {
      const res = await api.askStream(question, ageNum, {
        onStage: (stageIndex) => {
          setLoadingStage(stageIndex);
        },
        onToken: (token) => {
          setStreamingText((prev) => prev + token);
          setLoadingStage(3); // Synthesizing stage
        },
        onDone: (finalRes) => {
          setResult(finalRes);
          setStreamingText('');
          setActiveTab('answer');
          setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
        },
        onError: (err) => {
          setError(err);
        },
      });
      setResult(res);
      setStreamingText('');
      setActiveTab('answer');
    } catch (e) {
      // Fallback to non-streaming endpoint
      try {
        const fallbackRes = await api.ask(question, ageNum);
        setResult(fallbackRes);
        setActiveTab('answer');
      } catch {
        if (e instanceof APIError) {
          if (e.status === 0 || e.message.includes('fetch')) {
            setError('Backend unavailable. Please ensure the NutriKid API server is running on port 8000.');
          } else {
            setError(e.message);
          }
        } else {
          setError('Request failed. Is the API server running?');
        }
      }
    } finally {
      setLoading(false);
      setStreamingText('');
    }
  };

  const loadPreset = (p: typeof PRESET_QUERIES[0]) => {
    setQuestion(p.query);
    setAge(String(p.age));
    setResult(null);
    setError('');
  };

  const scopeTag = ageValid
    ? ageInScope
      ? { label: `VALID COHORT: ${ageNum.toFixed(1)} YRS`, color: 'var(--confidence-high)', icon: 'check_circle' }
      : { label: `OUT OF SCOPE: ${ageNum.toFixed(1)} YRS — Must be 5.0–15.0`, color: 'var(--confidence-low)', icon: 'error' }
    : { label: 'Enter age to validate', color: 'var(--on-surface-variant)', icon: 'help' };

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>
        <div style={{ maxWidth: 1800, margin: '0 auto', padding: '20px 24px' }}>

          {/* Top HUD */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 20, padding: '10px 16px', backgroundColor: 'var(--surface-container)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--primary-container)', animation: 'ping 1.5s cubic-bezier(0,0,0.2,1) infinite' }} />
              <span className="font-mono text-label-provenance" style={{ color: 'var(--primary-container)', fontSize: 11 }}>WORKSPACE READY</span>
              <span style={{ color: 'var(--outline)' }}>/</span>
              <span className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)' }}>Ask NutriKid — Clinical RAG Query Engine</span>
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                Model: <strong style={{ color: 'var(--on-surface)' }}>{CORPUS_STATS.generation_model.split('/').pop()}</strong>
              </span>
              <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                Index: <strong style={{ color: 'var(--on-surface)' }}>FAISS + BM25</strong>
              </span>
              <span className="badge badge-high" style={{ fontSize: 10 }}>Vector Sync: OK</span>
            </div>
          </div>

          {/* Main dual-panel grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>

            {/* ─── LEFT PANEL — Query Input ─────────────────────────── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="nk-card" style={{ padding: 24, position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', right: -40, top: -40, width: 160, height: 160, background: 'radial-gradient(circle, rgba(0,229,201,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />

                {/* Card header */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--primary-container)' }}>tune</span>
                      <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--primary-container)' }}>PEDIATRIC PARAMETERS & QUERY VECTOR</span>
                    </div>
                    <h2 className="text-headline-md" style={{ color: 'var(--on-surface)' }}>Clinical Retrieval Engine</h2>
                  </div>
                  <span className="badge badge-citation" style={{ fontSize: 10 }}>Dual-Grounded</span>
                </div>

                <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', marginBottom: 20 }}>
                  Corpus: <span style={{ color: 'var(--on-surface)', fontWeight: 500 }}>ICMR-NIN 2020 & IFCT 2017</span> Active ·
                  Engine: <span style={{ color: 'var(--on-surface)', fontWeight: 500 }}>{CORPUS_STATS.generation_model.split('/').pop()}</span>
                </p>

                {/* Age input */}
                <div style={{ backgroundColor: 'var(--surface-container-low)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <label className="font-geist" style={{ fontSize: 14, fontWeight: 500, color: 'var(--on-surface)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--secondary)' }}>child_care</span>
                      Child Chronological Age
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input
                        id="age-number-input"
                        type="number"
                        min={1} max={20} step={0.5}
                        value={age}
                        onChange={(e) => setAge(e.target.value)}
                        style={{ width: 64, height: 28, textAlign: 'center', backgroundColor: 'var(--surface-base)', color: 'var(--primary-container)', fontFamily: 'JetBrains Mono, monospace', fontSize: 13, borderRadius: 6, border: '1px solid var(--border-subtle)', outline: 'none', padding: '0 4px' }}
                      />
                      <span className="font-mono text-label-code" style={{ fontSize: 12, color: 'var(--on-surface-variant)' }}>YRS</span>
                    </div>
                  </div>

                  <input
                    type="range"
                    id="child-age-range"
                    min={5} max={15} step={0.5}
                    value={Math.min(Math.max(ageNum || 10, 5), 15)}
                    onChange={(e) => setAge(e.target.value)}
                    style={{ width: '100%', marginBottom: 6 }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'var(--on-surface-variant)' }}>
                    <span>5.0 Y (Lower Limit)</span>
                    <span style={{ color: 'var(--primary-container)', fontWeight: 600 }}>{ageNum ? `${ageNum.toFixed(1)} Y (Selected)` : '— Y (Enter age)'}</span>
                    <span>15.0 Y (Upper Limit)</span>
                  </div>

                  {/* Scope tag */}
                  <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '7px 10px', borderRadius: 6, backgroundColor: 'var(--surface-container)', border: `1px solid ${ageInScope ? 'rgba(16,185,129,0.2)' : ageValid ? 'rgba(239,68,68,0.2)' : 'var(--border-subtle)'}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: scopeTag.color }}>{scopeTag.icon}</span>
                      <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: scopeTag.color }}>{scopeTag.label}</span>
                    </div>
                    <span className="font-mono text-label-code" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                      {ageInScope ? 'PEDIATRIC TIER-2' : ageValid ? 'REFUSAL ZONE' : 'UNVALIDATED'}
                    </span>
                  </div>
                </div>

                {/* Question input */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <label className="font-geist" style={{ fontSize: 14, fontWeight: 500, color: 'var(--on-surface)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--primary-container)' }}>clinical_notes</span>
                      Clinical Question & Constraints
                    </label>
                    <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>NATURAL CLINICAL TEXT</span>
                  </div>
                  <div style={{ borderRadius: 8, overflow: 'hidden', backgroundColor: 'var(--surface-base)', border: '1px solid var(--border-subtle)' }}>
                    <textarea
                      id="question-input"
                      className="nk-textarea"
                      placeholder="Enter clinical nutritional query for deterministic guideline synthesis..."
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      rows={5}
                      style={{ border: 'none', borderRadius: '8px 8px 0 0' }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); handleAsk(); }
                      }}
                    />
                    <div style={{ backgroundColor: 'var(--surface-container-low)', padding: '8px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: question.trim() ? 'var(--confidence-high)' : 'var(--on-surface-variant)', display: 'block' }} />
                        <span className="font-mono text-label-code" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                          Target: ICMR-NIN 2020 RDA Standard
                        </span>
                      </div>
                      <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                        {question.length} chars · Ctrl+Enter to submit
                      </span>
                    </div>
                  </div>
                </div>

                {/* Preset chips */}
                <div style={{ marginBottom: 20 }}>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.06em' }}>
                    PRESET BENCHMARK QUERIES & EDGE SCENARIOS
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {PRESET_QUERIES.map((p) => (
                      <button
                        key={p.label}
                        onClick={() => loadPreset(p)}
                        style={{
                          padding: '5px 10px',
                          borderRadius: 6,
                          backgroundColor: p.isEdge ? 'rgba(239,68,68,0.1)' : 'var(--surface-container)',
                          border: `1px solid ${p.isEdge ? 'rgba(239,68,68,0.25)' : 'var(--border-subtle)'}`,
                          color: p.isEdge ? 'var(--confidence-low)' : 'var(--on-surface-variant)',
                          fontSize: 12,
                          fontFamily: 'Inter, sans-serif',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        {p.isEdge && <span className="material-symbols-outlined" style={{ fontSize: 12 }}>warning</span>}
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Retrieval info */}
                <div style={{ backgroundColor: 'var(--surface-container-low)', borderRadius: 8, padding: 12, marginBottom: 20, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  {[
                    { label: 'Retrieval Mode', value: 'BM25 + FAISS', color: 'var(--primary-container)' },
                    { label: 'Neural Reranker', value: 'bge-reranker-base', color: 'var(--secondary)' },
                    { label: 'Corpus Chunks', value: CORPUS_STATS.canonical_chunks.toLocaleString(), color: 'var(--chart-accent)' },
                  ].map((item) => (
                    <div key={item.label} style={{ backgroundColor: 'var(--surface-base)', padding: '8px 10px', borderRadius: 6 }}>
                      <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 4 }}>{item.label}</span>
                      <span className="font-mono text-label-code" style={{ fontSize: 11, fontWeight: 600, color: item.color }}>{item.value}</span>
                    </div>
                  ))}
                </div>

                {/* Submit button */}
                <button
                  id="ask-button"
                  className="btn-primary"
                  onClick={handleAsk}
                  disabled={loading}
                  style={{ width: '100%', justifyContent: 'center', padding: '12px 24px', fontSize: 15 }}
                >
                  {loading ? (
                    <>
                      <div className="spinner" />
                      Processing clinical query…
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined" style={{ fontSize: 20 }}>auto_awesome</span>
                      Retrieve Evidence & Generate Answer
                    </>
                  )}
                </button>

                {/* Error */}
                {error && (
                  <div style={{ marginTop: 14, padding: '12px 16px', borderRadius: 8, backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--confidence-low)', flexShrink: 0 }}>error</span>
                    <p className="text-body-sm" style={{ color: 'var(--confidence-low)', lineHeight: 1.5 }}>{error}</p>
                  </div>
                )}
              </div>
            </div>

            {/* ─── RIGHT PANEL — Results ────────────────────────────── */}
            <div ref={resultRef} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* Loading state & live progressive token stream */}
              {loading && (
                <div className="nk-card animate-fade-in" style={{ padding: 24 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                    <div className="spinner" />
                    <span className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)' }}>
                      {streamingText ? 'Synthesizing Grounded Response (Live Streaming)…' : 'Running RAG Pipeline…'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: streamingText ? 16 : 0 }}>
                    {LOADING_STAGES.map((stage, i) => (
                      <div
                        key={stage.key}
                        className={`pipeline-step ${i < loadingStage ? 'done' : i === loadingStage ? 'active' : 'waiting'}`}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                          {i < loadingStage ? 'check_circle' : i === loadingStage ? 'radio_button_checked' : 'radio_button_unchecked'}
                        </span>
                        {stage.label}
                      </div>
                    ))}
                  </div>

                  {streamingText && (
                    <div style={{ marginTop: 14, backgroundColor: 'var(--surface-container-low)', borderRadius: 8, padding: 16, borderLeft: '3px solid var(--primary-container)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--primary-container)' }}>psychology</span>
                        <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--primary-container)' }}>STREAMING ANSWER IN REAL TIME</span>
                      </div>
                      <p className="text-body-md" style={{ color: 'var(--on-surface)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                        {streamingText}
                        <span style={{ display: 'inline-block', width: 6, height: 14, backgroundColor: 'var(--primary-container)', marginLeft: 3, verticalAlign: 'middle', animation: 'ping 1s infinite' }} />
                      </p>
                    </div>
                  )}

                  {!streamingText && (
                    <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', marginTop: 16 }}>
                      Active: Concurrent BM25 + FAISS retrieval with Cross-Encoder neural reranking.
                    </p>
                  )}
                </div>
              )}

              {/* Empty state */}
              {!loading && !result && !error && (
                <div className="nk-card" style={{ padding: 40, textAlign: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 48, color: 'var(--border-highlight)', display: 'block', marginBottom: 16 }}>clinical_notes</span>
                  <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 8 }}>
                    Clinical Query Engine Ready
                  </h3>
                  <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>
                    Enter a pediatric nutrition question on the left and click "Retrieve Evidence" to get a grounded answer with citations.
                  </p>
                </div>
              )}

              {/* Out-of-scope result */}
              {!loading && result && result.scope_status === 'out_of_scope' && (
                <div className="nk-card animate-slide-up" style={{ padding: 24, borderColor: 'rgba(245,158,11,0.3)', backgroundColor: 'rgba(245,158,11,0.04)' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 16 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--confidence-medium)', flexShrink: 0 }}>shield</span>
                    <div>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                        <span className="badge badge-medium">Outside NutriKid Scope</span>
                        <span className="badge badge-neutral" style={{ fontSize: 10 }}>Age: {result.child_age}y</span>
                      </div>
                      <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)' }}>
                        Protected Age Boundary
                      </h3>
                    </div>
                  </div>
                  <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.7, marginBottom: 16 }}>
                    {result.answer}
                  </p>
                  <div style={{ padding: '12px 16px', backgroundColor: 'var(--surface-container-low)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                    <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                      NUTRIKID CURRENTLY SUPPORTS: 5.0 – 15.0 YEARS · THIS IS A PROTECTIVE SYSTEM BOUNDARY, NOT A TECHNICAL ERROR
                    </p>
                  </div>
                </div>
              )}

              {/* In-scope result */}
              {!loading && result && result.scope_status !== 'out_of_scope' && (
                <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

                  {/* Result meta header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: '10px 14px', backgroundColor: 'var(--surface-container-low)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                    <span className="badge badge-high">In Scope</span>
                    <span className="badge badge-neutral" style={{ fontSize: 10 }}>Age: {result.child_age}y</span>
                    {result.generation_metadata?.model && (
                      <span className="badge badge-secondary" style={{ fontSize: 10 }}>
                        {String(result.generation_metadata.model).split('/').pop()}
                      </span>
                    )}
                    {result.fidelity_check && (
                      <span className={`badge ${result.fidelity_check.passed ? 'badge-high' : 'badge-low'}`} style={{ fontSize: 10 }}>
                        Fidelity: {result.fidelity_check.passed ? 'PASS' : 'OVERRIDE'}
                      </span>
                    )}
                    <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)', marginLeft: 'auto' }}>
                      {result.evidence?.length || 0} evidence passages · {result.citations?.length || 0} citations
                    </span>
                  </div>

                  {/* Tabs */}
                  <div style={{ display: 'flex', gap: 4, padding: '4px', backgroundColor: 'var(--surface-container-low)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                    {[
                      { key: 'answer', label: 'Grounded Answer', icon: 'psychology' },
                      { key: 'citations', label: `Sources (${result.citations?.length || 0})`, icon: 'bookmark' },
                      { key: 'evidence', label: `Evidence (${result.evidence?.length || 0})`, icon: 'science' },
                    ].map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as typeof activeTab)}
                        style={{
                          flex: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6,
                          padding: '8px 12px',
                          borderRadius: 6,
                          border: 'none',
                          cursor: 'pointer',
                          fontSize: 13,
                          fontFamily: 'Inter, sans-serif',
                          fontWeight: activeTab === tab.key ? 600 : 400,
                          backgroundColor: activeTab === tab.key ? 'var(--surface-container-high)' : 'transparent',
                          color: activeTab === tab.key ? 'var(--primary-container)' : 'var(--on-surface-variant)',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: 15 }}>{tab.icon}</span>
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Answer tab */}
                  {activeTab === 'answer' && (
                    <div className="nk-card" style={{ padding: 24 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--primary-container)' }}>psychology</span>
                        <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)' }}>
                          Evidence-Grounded Answer
                        </h3>
                      </div>
                      <div style={{ backgroundColor: 'var(--surface-container-low)', borderRadius: 8, padding: 16, borderLeft: '3px solid var(--primary-container)' }}>
                        <p className="text-body-md" style={{ color: 'var(--on-surface)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                          {result.answer}
                        </p>
                      </div>
                      {result.fidelity_check && !result.fidelity_check.passed && (
                        <div style={{ marginTop: 14, padding: '12px 16px', borderRadius: 8, backgroundColor: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }}>
                          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--confidence-medium)', marginBottom: 4 }}>NUTRIENT FIDELITY GUARD TRIGGERED</p>
                          <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{result.fidelity_check.explanation}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Citations tab */}
                  {activeTab === 'citations' && (
                    <div className="nk-card" style={{ padding: 24 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--secondary)' }}>bookmark</span>
                        <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)' }}>
                          Source Citations ({result.citations?.length || 0})
                        </h3>
                      </div>
                      {result.citations && result.citations.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {result.citations.map((c, i) => (
                            <CitationCard key={i} citation={c} index={i} />
                          ))}
                        </div>
                      ) : (
                        <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>No citations returned by this query.</p>
                      )}
                    </div>
                  )}

                  {/* Evidence tab */}
                  {activeTab === 'evidence' && (
                    <div className="nk-card" style={{ padding: 24 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--chart-accent)' }}>science</span>
                        <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)' }}>
                          Retrieved Evidence Passages ({result.evidence?.length || 0})
                        </h3>
                      </div>
                      {result.evidence && result.evidence.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          {result.evidence.map((ev, i) => (
                            <EvidenceCard key={i} ev={ev} index={i} />
                          ))}
                        </div>
                      ) : (
                        <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>No evidence passages returned.</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '16px 24px', textAlign: 'center', marginTop: 40 }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            NUTRIKID CLINICAL RAG ENGINE · NOT FOR MEDICAL DIAGNOSIS · SCOPE: 5.0–15.0 YEARS
          </p>
        </footer>

        <style jsx>{`
          @media (max-width: 1024px) {
            div[style*="grid-template-columns: 1fr 1fr"] {
              grid-template-columns: 1fr !important;
            }
          }
        `}</style>
      </main>
    </>
  );
}
