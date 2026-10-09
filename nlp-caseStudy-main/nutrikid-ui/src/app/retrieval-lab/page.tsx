'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import { api, APIError } from '@/lib/api';
import type { SearchResponse, SearchResult } from '@/lib/types';
import { CORPUS_STATS } from '@/lib/corpus';

type Backend = 'faiss' | 'chroma';

const TOP_K_OPTIONS = [3, 5, 10, 15, 20];

const SAMPLE_QUERIES = [
  'protein requirements for school-age children',
  'calcium RDA for adolescents',
  'iron deficiency anemia prevention',
  'vitamin D requirements for children',
  'sodium intake recommendations for 10 year old',
  'dietary fiber guidelines for children',
];

function ResultRow({ result, index, backend }: { result: SearchResult; index: number; backend: Backend }) {
  const [expanded, setExpanded] = useState(false);
  const PREVIEW = 250;
  const isLong = result.text.length > PREVIEW;

  return (
    <tr>
      <td style={{ textAlign: 'center', padding: '10px 12px', whiteSpace: 'nowrap' }}>
        <span className="font-mono" style={{ fontSize: 11, color: backend === 'faiss' ? 'var(--primary-container)' : 'var(--secondary)', fontWeight: 700 }}>
          #{index + 1}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span className="badge badge-citation" style={{ fontSize: 10 }}>{result.chunk_id}</span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span className="font-mono" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
          {result.metadata?.source || result.metadata?.source_name || '—'}
        </span>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
        <span className="font-mono" style={{ fontSize: 12, fontWeight: 600, color: result.score > 0.5 ? 'var(--confidence-high)' : result.score > 0.3 ? 'var(--confidence-medium)' : 'var(--on-surface-variant)', fontVariantNumeric: 'tabular-nums' }}>
          {result.score.toFixed(4)}
        </span>
      </td>
      <td style={{ padding: '10px 12px' }}>
        <span className="font-mono" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
          {result.metadata?.page ? `p.${result.metadata.page}` : '—'}
        </span>
      </td>
      <td style={{ padding: '10px 12px', maxWidth: 400 }}>
        <div>
          <p className="text-body-sm" style={{ color: 'var(--on-surface)', lineHeight: 1.6, wordBreak: 'break-word' }}>
            {expanded || !isLong ? result.text : `${result.text.slice(0, PREVIEW)}…`}
          </p>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              style={{ marginTop: 4, background: 'none', border: 'none', color: 'var(--secondary)', fontSize: 11, cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', display: 'flex', alignItems: 'center', gap: 3 }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>{expanded ? 'expand_less' : 'expand_more'}</span>
              {expanded ? 'Collapse' : 'Expand passage'}
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function RetrievalLabPage() {
  const [query, setQuery] = useState('');
  const [backend, setBackend] = useState<Backend>('faiss');
  const [topK, setTopK] = useState(5);
  const [compareMode, setCompareMode] = useState(false);

  const [results, setResults] = useState<SearchResponse | null>(null);
  const [resultsB, setResultsB] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) { setError('Please enter a search query.'); return; }
    setLoading(true);
    setError('');
    setResults(null);
    setResultsB(null);

    try {
      if (compareMode) {
        const [faissRes, chromaRes] = await Promise.allSettled([
          api.searchFaiss(query, topK),
          api.searchChroma(query, topK),
        ]);
        if (faissRes.status === 'fulfilled') setResults(faissRes.value);
        else setError(`FAISS: ${faissRes.reason instanceof APIError ? faissRes.reason.message : 'Search failed'}`);

        if (chromaRes.status === 'fulfilled') setResultsB(chromaRes.value);
        else {
          // Chroma may not be available — show graceful message
          setResultsB({ backend: 'chromadb', query, k: topK, results: [] });
          if (!error) setError(`ChromaDB: ${chromaRes.reason instanceof APIError ? chromaRes.reason.message : 'ChromaDB unavailable'}`);
        }
      } else {
        const res = backend === 'faiss'
          ? await api.searchFaiss(query, topK)
          : await api.searchChroma(query, topK);
        setResults(res);
      }
    } catch (e) {
      if (e instanceof APIError) {
        setError(e.message.includes('fetch') || e.status === 0
          ? 'Backend unavailable. Please ensure the NutriKid API server is running.'
          : e.message);
      } else {
        setError('Search failed. Is the API server running?');
      }
    } finally {
      setLoading(false);
    }
  };

  const backendColor = (b: string) => b === 'faiss' ? 'var(--primary-container)' : 'var(--secondary)';
  const backendLabel = (b: string) => b === 'faiss' ? '⚡ FAISS' : '◉ ChromaDB';
  const scoreNote = (b: string) => b === 'faiss'
    ? 'Inner-product similarity (higher = more similar)'
    : 'Cosine similarity (higher = more similar) — not directly comparable to FAISS scores';

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>
        <div style={{ maxWidth: 1800, margin: '0 auto', padding: '24px 24px' }}>

          {/* Page header */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span className="badge badge-primary">Vector Search Lab</span>
              <span className="badge badge-neutral" style={{ fontSize: 10 }}>Phase 2 Dual Backend</span>
            </div>
            <h1 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginBottom: 8 }}>
              NutriKid Retrieval Lab — Vector Search
            </h1>
            <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', maxWidth: 700 }}>
              Inspect raw vector similarity results from FAISS (production backend) and ChromaDB (Phase 2 alternative).
              The main RAG pipeline always uses FAISS with BM25+RRF hybrid retrieval.
            </p>
          </div>

          {/* Two-column layout: controls + results */}
          <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20, alignItems: 'start' }}>

            {/* ─── LEFT — Search Controls ─────────────────────────────── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="nk-card" style={{ padding: 22 }}>
                <h2 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--primary-container)' }}>manage_search</span>
                  Search Parameters
                </h2>

                {/* Query input */}
                <div style={{ marginBottom: 16 }}>
                  <label className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.05em' }}>
                    SEARCH QUERY
                  </label>
                  <input
                    id="search-input"
                    className="nk-input"
                    placeholder="e.g. protein requirements for children"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  />
                </div>

                {/* Sample queries */}
                <div style={{ marginBottom: 16 }}>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 6, letterSpacing: '0.05em' }}>
                    SAMPLE QUERIES
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                    {SAMPLE_QUERIES.map((q) => (
                      <button
                        key={q}
                        onClick={() => { setQuery(q); setError(''); }}
                        style={{ padding: '3px 8px', borderRadius: 5, backgroundColor: 'var(--surface-container)', border: '1px solid var(--border-subtle)', color: 'var(--on-surface-variant)', fontSize: 11, fontFamily: 'Inter, sans-serif', cursor: 'pointer' }}
                      >
                        {q.length > 30 ? q.slice(0, 28) + '…' : q}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Backend selector */}
                <div style={{ marginBottom: 16 }}>
                  <label className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.05em' }}>
                    VECTOR ENGINE
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {(['faiss', 'chroma'] as Backend[]).map((b) => (
                      <button
                        key={b}
                        id={`backend-${b}`}
                        onClick={() => { setBackend(b); setCompareMode(false); }}
                        disabled={compareMode}
                        style={{
                          flex: 1,
                          padding: '8px 10px',
                          borderRadius: 8,
                          border: `1px solid ${backend === b && !compareMode ? backendColor(b) : 'var(--border-subtle)'}`,
                          backgroundColor: backend === b && !compareMode ? `rgba(${b === 'faiss' ? '0,229,201' : '123,208,255'},0.08)` : 'var(--surface-container)',
                          color: backend === b && !compareMode ? backendColor(b) : 'var(--on-surface-variant)',
                          fontSize: 12,
                          fontFamily: 'JetBrains Mono, monospace',
                          fontWeight: 600,
                          cursor: compareMode ? 'not-allowed' : 'pointer',
                          opacity: compareMode ? 0.5 : 1,
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {b === 'faiss' ? '⚡ FAISS (Production)' : '◉ ChromaDB (Phase 2)'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Compare mode toggle */}
                <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', backgroundColor: 'var(--surface-container-low)', borderRadius: 8 }}>
                  <button
                    id="compare-toggle"
                    onClick={() => setCompareMode(!compareMode)}
                    style={{ width: 36, height: 20, borderRadius: 10, backgroundColor: compareMode ? 'var(--primary-container)' : 'var(--surface-container-high)', border: 'none', cursor: 'pointer', position: 'relative', transition: 'background-color 0.2s ease', flexShrink: 0 }}
                  >
                    <span style={{ position: 'absolute', top: 2, left: compareMode ? 18 : 2, width: 16, height: 16, borderRadius: '50%', backgroundColor: compareMode ? 'var(--on-primary-fixed)' : 'var(--on-surface-variant)', transition: 'left 0.2s ease', display: 'block' }} />
                  </button>
                  <div>
                    <span className="font-mono text-label-code" style={{ fontSize: 11, color: 'var(--on-surface)', display: 'block' }}>
                      Compare FAISS vs ChromaDB
                    </span>
                    <span className="text-body-sm" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                      Run both backends simultaneously
                    </span>
                  </div>
                </div>

                {/* Top-K selector */}
                <div style={{ marginBottom: 20 }}>
                  <label className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 8, letterSpacing: '0.05em' }}>
                    TOP-K RESULTS: <span style={{ color: 'var(--primary-container)' }}>{topK}</span>
                  </label>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {TOP_K_OPTIONS.map((k) => (
                      <button
                        key={k}
                        onClick={() => setTopK(k)}
                        style={{
                          flex: 1,
                          padding: '6px 0',
                          borderRadius: 6,
                          border: `1px solid ${topK === k ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                          backgroundColor: topK === k ? 'rgba(0,229,201,0.1)' : 'var(--surface-container)',
                          color: topK === k ? 'var(--primary-container)' : 'var(--on-surface-variant)',
                          fontSize: 12,
                          fontFamily: 'JetBrains Mono, monospace',
                          fontWeight: topK === k ? 700 : 400,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {k}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Search button */}
                <button
                  id="search-button"
                  className="btn-primary"
                  onClick={handleSearch}
                  disabled={loading}
                  style={{ width: '100%', justifyContent: 'center', padding: '11px 20px' }}
                >
                  {loading ? (
                    <><div className="spinner" />Searching vectors…</>
                  ) : (
                    <><span className="material-symbols-outlined" style={{ fontSize: 19 }}>manage_search</span>
                    {compareMode ? 'Compare Both Backends' : `Search ${backend.toUpperCase()}`}</>
                  )}
                </button>

                {error && (
                  <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
                    <p className="text-body-sm" style={{ color: 'var(--confidence-low)' }}>{error}</p>
                  </div>
                )}
              </div>

              {/* Index info card */}
              <div className="nk-card" style={{ padding: 18 }}>
                <h3 className="font-geist" style={{ fontSize: 13, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--secondary)' }}>database</span>
                  Index Metadata
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    { label: 'FAISS Vectors', value: CORPUS_STATS.canonical_chunks.toLocaleString(), color: 'var(--primary-container)' },
                    { label: 'Embedding Model', value: CORPUS_STATS.embedding_model.split('/').pop() || CORPUS_STATS.embedding_model },
                    { label: 'FAISS Index Type', value: 'IndexFlatIP (Cosine)' },
                    { label: 'ChromaDB Status', value: 'Phase 2 Alternative' },
                    { label: 'BM25 Vocabulary', value: '33,038 terms' },
                  ].map((item) => (
                    <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: 'var(--surface-container-low)', borderRadius: 5 }}>
                      <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>{item.label}</span>
                      <span className="font-mono text-label-code" style={{ fontSize: 10, fontWeight: 600, color: item.color || 'var(--on-surface)' }}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ─── RIGHT — Results ─────────────────────────────────────── */}
            <div>
              {/* Empty state */}
              {!loading && !results && !resultsB && (
                <div className="nk-card" style={{ padding: 48, textAlign: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 52, color: 'var(--border-highlight)', display: 'block', marginBottom: 16 }}>manage_search</span>
                  <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 8 }}>
                    Vector Search Ready
                  </h3>
                  <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', maxWidth: 400, margin: '0 auto' }}>
                    Enter a query and select a backend. FAISS uses normalized inner-product (cosine) similarity.
                    ChromaDB uses cosine similarity — scores are not directly comparable between backends.
                  </p>
                </div>
              )}

              {/* Loading */}
              {loading && (
                <div className="nk-card animate-fade-in" style={{ padding: 40, textAlign: 'center' }}>
                  <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px', borderWidth: 3 }} />
                  <p className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 6 }}>
                    Searching vector index…
                  </p>
                  <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>
                    {compareMode ? 'Running FAISS and ChromaDB in parallel' : `Querying ${backend.toUpperCase()} with k=${topK}`}
                  </p>
                </div>
              )}

              {/* Single backend results */}
              {!loading && results && !compareMode && (
                <div className="animate-slide-up">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
                    <span className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)' }}>
                      {backendLabel(results.backend)}
                    </span>
                    <span className="badge" style={{ backgroundColor: `rgba(${results.backend === 'faiss' ? '0,229,201' : '123,208,255'},0.1)`, color: backendColor(results.backend), border: `1px solid ${backendColor(results.backend)}40`, fontSize: 10 }}>
                      {results.results.length} results
                    </span>
                    <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                      · {scoreNote(results.backend)}
                    </span>
                  </div>

                  <div className="nk-card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ overflowX: 'auto' }}>
                      <table className="nk-table">
                        <thead>
                          <tr>
                            <th style={{ width: 40 }}>Rank</th>
                            <th>Chunk ID</th>
                            <th>Source</th>
                            <th style={{ textAlign: 'right' }}>Score</th>
                            <th>Page</th>
                            <th>Evidence Text</th>
                          </tr>
                        </thead>
                        <tbody>
                          {results.results.map((r, i) => (
                            <ResultRow key={i} result={r} index={i} backend={results.backend as Backend} />
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Compare mode results */}
              {!loading && compareMode && (results || resultsB) && (
                <div className="animate-slide-up" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  {[results, resultsB].map((res, panel) => {
                    const bkd = panel === 0 ? 'faiss' : 'chroma';
                    return (
                      <div key={bkd}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                          <span className="font-geist" style={{ fontSize: 14, fontWeight: 600, color: backendColor(bkd) }}>
                            {backendLabel(bkd)}
                          </span>
                          {res && <span className="badge badge-neutral" style={{ fontSize: 10 }}>{res.results.length} results</span>}
                        </div>
                        <div className="nk-card" style={{ padding: 0, overflow: 'hidden' }}>
                          {res && res.results.length > 0 ? (
                            <div style={{ overflowX: 'auto' }}>
                              <table className="nk-table">
                                <thead>
                                  <tr>
                                    <th>#</th>
                                    <th>Chunk</th>
                                    <th>Source</th>
                                    <th style={{ textAlign: 'right' }}>Score</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {res.results.map((r, i) => (
                                    <tr key={i}>
                                      <td style={{ textAlign: 'center', padding: '8px 10px' }}>
                                        <span className="font-mono" style={{ fontSize: 11, color: backendColor(bkd), fontWeight: 700 }}>#{i + 1}</span>
                                      </td>
                                      <td style={{ padding: '8px 10px' }}>
                                        <span className="badge badge-citation" style={{ fontSize: 9 }}>{r.chunk_id}</span>
                                      </td>
                                      <td style={{ padding: '8px 10px' }}>
                                        <span className="font-mono" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                                          {r.metadata?.source || r.metadata?.source_name || '—'}
                                        </span>
                                      </td>
                                      <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                                        <span className="font-mono" style={{ fontSize: 11, fontWeight: 600, color: backendColor(bkd), fontVariantNumeric: 'tabular-nums' }}>
                                          {r.score.toFixed(4)}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div style={{ padding: 24, textAlign: 'center' }}>
                              <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>
                                {bkd === 'chroma' ? 'ChromaDB is currently unavailable.' : 'No results returned.'}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '16px 24px', textAlign: 'center', marginTop: 40 }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            NUTRIKID RETRIEVAL LAB · FAISS IndexFlatIP · ChromaDB Cosine · {CORPUS_STATS.canonical_chunks.toLocaleString()} INDEXED CHUNKS
          </p>
        </footer>

        <style jsx>{`
          @media (max-width: 1100px) {
            div[style*="grid-template-columns: 380px 1fr"] {
              grid-template-columns: 1fr !important;
            }
          }
          @media (max-width: 800px) {
            div[style*="grid-template-columns: 1fr 1fr"] {
              grid-template-columns: 1fr !important;
            }
          }
        `}</style>
      </main>
    </>
  );
}
