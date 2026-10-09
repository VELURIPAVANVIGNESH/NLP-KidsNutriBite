'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import { CORPUS_SOURCES, CORPUS_STATS, type CorpusSource } from '@/lib/corpus';

const PUBLISHERS = ['All', 'WHO', 'ICMR-NIN', 'FAO', 'FAO/WHO', 'FSSAI'];
const TIERS = ['All', 'Tier 1', 'Tier 2'];

const TIER_COLOR: Record<string, string> = {
  'Tier 1': 'var(--primary-container)',
  'Tier 2': 'var(--secondary)',
  'Tier 3': 'var(--chart-accent)',
};
const PUBLISHER_COLOR: Record<string, string> = {
  WHO: 'var(--surgical-blue)',
  'ICMR-NIN': 'var(--primary-container)',
  FAO: 'var(--chart-accent)',
  'FAO/WHO': 'var(--confidence-medium)',
  FSSAI: 'var(--confidence-high)',
};

function SourceRow({ source }: { source: CorpusSource }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        <td style={{ padding: '10px 14px' }}>
          <span className="font-mono text-label-code" style={{ fontSize: 11, fontWeight: 700, color: 'var(--citation-text)' }}>
            {source.source_id}
          </span>
        </td>
        <td style={{ padding: '10px 14px', maxWidth: 340 }}>
          <span className="text-body-sm" style={{ color: 'var(--on-surface)', lineHeight: 1.5 }}>
            {source.source_name}
          </span>
        </td>
        <td style={{ padding: '10px 14px' }}>
          <span className="font-mono text-label-code" style={{ fontSize: 11, fontWeight: 600, color: PUBLISHER_COLOR[source.publisher] || 'var(--on-surface-variant)' }}>
            {source.publisher}
          </span>
        </td>
        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
          <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
            {source.publication_year}
          </span>
        </td>
        <td style={{ padding: '10px 14px' }}>
          <span className="badge badge-neutral" style={{ fontSize: 9 }}>
            {source.document_type}
          </span>
        </td>
        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
          <span className="badge" style={{ fontSize: 9, color: TIER_COLOR[source.authority_tier] || 'var(--on-surface-variant)', backgroundColor: 'transparent', border: `1px solid ${TIER_COLOR[source.authority_tier] || 'var(--border-subtle)'}40` }}>
            {source.authority_tier}
          </span>
        </td>
        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
          {source.age_min && source.age_max ? (
            <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
              {source.age_min}–{source.age_max}y
            </span>
          ) : (
            <span style={{ color: 'var(--on-surface-variant)', fontSize: 10 }}>—</span>
          )}
        </td>
        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              color: source.retrieval_enabled ? 'var(--confidence-high)' : 'var(--on-surface-variant)',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 13 }}>
              {source.retrieval_enabled ? 'check_circle' : 'cancel'}
            </span>
            {source.retrieval_enabled ? 'ACTIVE' : 'DISABLED'}
          </span>
        </td>
        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--on-surface-variant)' }}>
            {expanded ? 'expand_less' : 'expand_more'}
          </span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} style={{ padding: '0 14px 16px' }}>
            <div style={{ backgroundColor: 'var(--surface-container-low)', borderRadius: 8, padding: '12px 16px', borderLeft: '3px solid var(--border-highlight)' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                <div>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 3 }}>DOMAIN</span>
                  <span className="text-body-sm" style={{ color: 'var(--on-surface)' }}>{source.domain}</span>
                </div>
                <div>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 3 }}>FOLDER</span>
                  <span className="text-body-sm" style={{ color: 'var(--on-surface)' }}>{source.folder}</span>
                </div>
                <div>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 3 }}>FILE</span>
                  <span className="font-mono text-label-code" style={{ fontSize: 10, color: 'var(--citation-text)' }}>{source.file_name}</span>
                </div>
                <div>
                  <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 3 }}>RETRIEVAL STATUS</span>
                  <span className="font-mono text-label-code" style={{ fontSize: 10, color: source.retrieval_enabled ? 'var(--confidence-high)' : 'var(--on-surface-variant)' }}>
                    {source.retrieval_enabled ? 'Included in active corpus — indexed in FAISS + BM25' : 'Excluded from retrieval (out-of-scope folder)'}
                  </span>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function SourcesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPublisher, setFilterPublisher] = useState('All');
  const [filterTier, setFilterTier] = useState('All');
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'disabled'>('active');

  const filtered = CORPUS_SOURCES.filter((s) => {
    const matchSearch =
      !searchTerm ||
      s.source_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.source_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.publisher.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.domain.toLowerCase().includes(searchTerm.toLowerCase());
    const matchPublisher = filterPublisher === 'All' || s.publisher.startsWith(filterPublisher);
    const matchTier = filterTier === 'All' || s.authority_tier === filterTier;
    const matchActive =
      filterActive === 'all' ||
      (filterActive === 'active' && s.retrieval_enabled) ||
      (filterActive === 'disabled' && !s.retrieval_enabled);
    return matchSearch && matchPublisher && matchTier && matchActive;
  });

  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>
        <div style={{ maxWidth: 1800, margin: '0 auto', padding: '32px 24px' }}>

          {/* Page header */}
          <div style={{ marginBottom: 32 }}>
            <span className="badge badge-primary" style={{ marginBottom: 12 }}>Knowledge Corpus</span>
            <h1 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginBottom: 12, marginTop: 8 }}>
              NutriKid Institutional Sources
            </h1>
            <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', maxWidth: 700, lineHeight: 1.7 }}>
              NutriKid retrieves evidence exclusively from peer-reviewed publications and official guidelines issued by globally recognized health and nutrition authorities.
            </p>
            <div style={{ marginTop: 14, padding: '10px 16px', backgroundColor: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 8, maxWidth: 700 }}>
              <p className="text-body-sm" style={{ color: 'var(--confidence-medium)' }}>
                <strong>Disclaimer:</strong> These institutions are sources of the underlying evidence corpus. Their inclusion does not imply endorsement, certification, or affiliation with NutriKid.
              </p>
            </div>
          </div>

          {/* Stats strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 28 }}>
            {[
              { value: String(CORPUS_STATS.active_documents), label: 'Active Documents', color: 'var(--primary-container)' },
              { value: CORPUS_STATS.total_pages.toLocaleString(), label: 'Total Pages Parsed' },
              { value: CORPUS_STATS.canonical_chunks.toLocaleString(), label: 'Canonical Chunks' },
              { value: '8,351', label: 'IFCT Food Rows' },
              { value: `${CORPUS_SOURCES.filter(s => s.publisher.startsWith('WHO')).length}`, label: 'WHO Publications' },
              { value: `${CORPUS_SOURCES.filter(s => s.publisher.includes('ICMR')).length}`, label: 'ICMR-NIN Publications' },
            ].map((stat) => (
              <div key={stat.label} className="metric-card">
                <span className="metric-value" style={{ fontSize: 22, color: stat.color || 'var(--primary-container)' }}>{stat.value}</span>
                <span className="metric-label" style={{ fontSize: 10 }}>{stat.label}</span>
              </div>
            ))}
          </div>

          {/* Filter bar */}
          <div className="nk-card" style={{ padding: '16px 20px', marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
            {/* Search */}
            <div style={{ flex: '1 1 220px', minWidth: 200 }}>
              <input
                className="nk-input"
                placeholder="Search sources, IDs, publishers…"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ height: 36 }}
              />
            </div>

            {/* Publisher filter */}
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {PUBLISHERS.map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPublisher(p)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 5,
                    border: `1px solid ${filterPublisher === p ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    backgroundColor: filterPublisher === p ? 'rgba(0,229,201,0.1)' : 'var(--surface-container)',
                    color: filterPublisher === p ? 'var(--primary-container)' : 'var(--on-surface-variant)',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono, monospace',
                    cursor: 'pointer',
                  }}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Tier filter */}
            <div style={{ display: 'flex', gap: 5 }}>
              {TIERS.map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterTier(t)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 5,
                    border: `1px solid ${filterTier === t ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    backgroundColor: filterTier === t ? 'rgba(0,229,201,0.1)' : 'var(--surface-container)',
                    color: filterTier === t ? 'var(--primary-container)' : 'var(--on-surface-variant)',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono, monospace',
                    cursor: 'pointer',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Active filter */}
            <div style={{ display: 'flex', gap: 5 }}>
              {(['active', 'disabled', 'all'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterActive(f)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 5,
                    border: `1px solid ${filterActive === f ? 'var(--border-highlight)' : 'var(--border-subtle)'}`,
                    backgroundColor: filterActive === f ? 'rgba(0,229,201,0.1)' : 'var(--surface-container)',
                    color: filterActive === f ? 'var(--primary-container)' : 'var(--on-surface-variant)',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono, monospace',
                    cursor: 'pointer',
                  }}
                >
                  {f === 'active' ? '● Active' : f === 'disabled' ? '○ Disabled' : 'All Status'}
                </button>
              ))}
            </div>

            <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)', marginLeft: 'auto' }}>
              {filtered.length} / {CORPUS_SOURCES.length} sources
            </span>
          </div>

          {/* Sources table */}
          <div className="nk-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table className="nk-table">
                <thead>
                  <tr>
                    <th>Source ID</th>
                    <th>Document Title</th>
                    <th>Publisher</th>
                    <th style={{ textAlign: 'center' }}>Year</th>
                    <th>Type</th>
                    <th style={{ textAlign: 'center' }}>Authority</th>
                    <th style={{ textAlign: 'center' }}>Age Range</th>
                    <th style={{ textAlign: 'center' }}>Status</th>
                    <th style={{ width: 40 }} />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((source) => (
                    <SourceRow key={source.source_id} source={source} />
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={9} style={{ padding: 32, textAlign: 'center' }}>
                        <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>
                          No sources match the current filters.
                        </p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Corpus role explanation */}
          <div style={{ marginTop: 32, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            {[
              { folder: '01_PRIMARY_KNOWLEDGE', label: 'Primary Knowledge', desc: 'Tier 1 institutional guidelines and peer-reviewed publications directly consulted for RDA and clinical recommendations.', color: 'var(--primary-container)' },
              { folder: '02_SUPPORTING_KNOWLEDGE', label: 'Supporting Knowledge', desc: 'Tier 2 expert reports and specialized references that supplement primary guidelines with additional evidence.', color: 'var(--secondary)' },
              { folder: '03_EVALUATION_CONTEXT', label: 'Evaluation Context', desc: 'Survey data used for evaluation grounding only. Not indexed for retrieval.', color: 'var(--chart-accent)' },
              { folder: '04_OUT_OF_SCOPE_INFANT', label: 'Out-of-Scope (Infant)', desc: 'Infant nutrition documents (0–4 years) retained for research context. Retrieval is disabled for all documents in this folder.', color: 'var(--confidence-medium)' },
            ].map((role) => (
              <div key={role.folder} style={{ padding: '18px 20px', backgroundColor: 'var(--surface-raised)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: role.color, display: 'block', flexShrink: 0 }} />
                  <span className="font-geist" style={{ fontSize: 14, fontWeight: 600, color: 'var(--on-surface)' }}>{role.label}</span>
                </div>
                <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.6 }}>{role.desc}</p>
                <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: role.color, display: 'block', marginTop: 8 }}>{role.folder}</span>
              </div>
            ))}
          </div>
        </div>

        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '16px 24px', textAlign: 'center', marginTop: 40 }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            NUTRIKID CORPUS — {CORPUS_STATS.active_documents} ACTIVE DOCUMENTS · {CORPUS_STATS.total_pages.toLocaleString()} PAGES · {CORPUS_STATS.canonical_chunks.toLocaleString()} CHUNKS · INSTITUTIONAL SOURCES ONLY
          </p>
        </footer>
      </main>
    </>
  );
}
