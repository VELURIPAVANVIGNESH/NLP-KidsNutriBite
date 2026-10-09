'use client';

import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { CORPUS_STATS, RETRIEVAL_METRICS, GENERATION_METRICS } from '@/lib/corpus';

const PIPELINE_STAGES = [
  { stage: '01', label: 'User Query', desc: 'Clinical question intake + age parameters', icon: 'input', color: 'var(--on-surface-variant)' },
  { stage: '02', label: 'Scope Boundary', desc: 'Strict age gate: 5.0 ≤ age ≤ 15.0 or refusal', icon: 'shield_with_heart', color: 'var(--secondary)', highlight: true },
  { stage: '03', label: 'Hybrid Retrieval', desc: 'BM25 (lexical) + FAISS (bge-small-en-v1.5)', icon: 'device_hub', color: 'var(--chart-accent)' },
  { stage: '04', label: 'Neural Rerank', desc: 'bge-reranker-base cross-encoder scoring', icon: 'model_training', color: 'var(--primary-container)' },
  { stage: '05', label: 'Passage Filter', desc: 'Jaccard deduplication & citation windowing', icon: 'filter_alt', color: 'var(--secondary)' },
  { stage: '06', label: 'Local Synthesis', desc: 'Qwen2.5-1.5B-Instruct — prompt-constrained', icon: 'memory', color: 'var(--ice-glow)' },
  { stage: '07', label: 'Fidelity Guard', desc: 'Deterministic unit validation (g vs mg vs μg)', icon: 'check_box', color: 'var(--primary-container)', highlight: true },
  { stage: '08', label: 'Grounded Answer', desc: 'Traceable, age-specific clinical response', icon: 'verified', color: 'var(--confidence-high)' },
];

const BENEFICIARIES = [
  { icon: 'stethoscope', label: 'Pediatricians', desc: 'Clinical nutrition guidance at point of care' },
  { icon: 'nutrition', label: 'Dietitians', desc: 'Evidence-backed meal planning for school-age children' },
  { icon: 'school', label: 'School Nutrition', desc: 'Compliant school feeding program design' },
  { icon: 'family_restroom', label: 'Parents & Caregivers', desc: 'Trusted guidance on children\'s nutrition needs' },
  { icon: 'science', label: 'Researchers', desc: 'Systematic access to pediatric nutrition literature' },
];

const DIFFERENTIATORS = [
  { icon: 'child_care', label: 'Age-Bounded Retrieval', desc: 'Strict 5–15 year validation. Out-of-scope ages are refused, not approximated.' },
  { icon: 'device_hub', label: 'Hybrid Search (BM25 + Dense)', desc: 'Lexical precision fused with semantic recall via Reciprocal Rank Fusion.' },
  { icon: 'model_training', label: 'Neural Reranking', desc: 'BGE Cross-Encoder achieves +93.29% MRR improvement over baseline hybrid.' },
  { icon: 'verified', label: 'Evidence Provenance', desc: 'Every answer cites real chunk IDs, source documents, and page numbers.' },
  { icon: 'check_circle', label: 'Nutrient Fidelity Guard', desc: 'Deterministic post-generation validation prevents unit cross-contamination.' },
  { icon: 'database', label: 'Food Composition Data', desc: '8,351 Indian food composition rows from ICMR-NIN IFCT 2017.' },
];

const SOURCES = [
  { abbr: 'ICMR-NIN', full: 'Indian Council of Medical Research — National Institute of Nutrition', color: 'var(--primary-container)' },
  { abbr: 'WHO', full: 'World Health Organization', color: 'var(--secondary)' },
  { abbr: 'FAO/WHO', full: 'Food and Agriculture Organization / WHO', color: 'var(--chart-accent)' },
  { abbr: 'FSSAI', full: 'Food Safety and Standards Authority of India', color: 'var(--confidence-high)' },
];

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>

        {/* ─── HERO SECTION ────────────────────────────────────────────── */}
        <section style={{ position: 'relative', maxWidth: 1800, margin: '0 auto', padding: '60px 32px 80px', overflow: 'hidden' }}>
          {/* Ambient glows */}
          <div style={{ position: 'absolute', top: -80, left: '50%', transform: 'translateX(-50%)', width: 900, height: 400, background: 'radial-gradient(ellipse, rgba(0,229,201,0.08) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />
          <div style={{ position: 'absolute', top: 160, right: 40, width: 400, height: 300, background: 'radial-gradient(ellipse, rgba(2,132,199,0.07) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />

          <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', maxWidth: 900, margin: '0 auto' }}>
            {/* Super-badge */}
            <div className="hero-super-badge">
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--primary-container)', display: 'block', animation: 'pulse-glow 2s ease-in-out infinite' }} />
              <span className="font-mono text-label-provenance text-citation" style={{ letterSpacing: '0.08em' }}>
                EVIDENCE-GROUNDED PEDIATRIC NUTRITION INTELLIGENCE • SCOPE: 5.0–15.0 YEARS
              </span>
            </div>

            {/* Headline */}
            <h1 className="text-headline-xl" style={{ color: 'var(--on-surface)', maxWidth: 820, marginBottom: 20 }}>
              Pediatric nutrition answers,{' '}
              <span className="gradient-primary">grounded in evidence.</span>
            </h1>

            {/* Subline */}
            <p className="text-body-lg" style={{ color: 'var(--on-surface-variant)', maxWidth: 700, marginBottom: 36, lineHeight: '1.7' }}>
              NutriKid is an evidence-grounded clinical RAG system that transforms authoritative pediatric nutrition guidelines into traceable, age-specific answers for children aged 5–15.
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginBottom: 28 }}>
              <Link href="/ask" className="btn-primary" style={{ padding: '12px 24px', fontSize: 15 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>auto_awesome</span>
                Ask NutriKid
              </Link>
              <Link href="/pipeline" className="btn-secondary" style={{ padding: '11px 22px', fontSize: 15 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 19, color: 'var(--secondary)' }}>account_tree</span>
                Explore How It Works
              </Link>
              <Link href="/evaluation" className="btn-ghost" style={{ padding: '11px 16px' }}>
                <span>Inspect Benchmark Data</span>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_forward</span>
              </Link>
            </div>

            {/* Trust tag */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--on-surface-variant)' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--primary-container)' }}>verified_user</span>
              <span className="font-mono text-label-provenance" style={{ fontSize: 10, letterSpacing: '0.06em' }}>
                ICMR-NIN • WHO • FAO • FSSAI — Designed for evidence retrieval, not diagnosis.
              </span>
            </div>
          </div>

          {/* ─── PIPELINE VISUALIZER ─────────────────────────────────── */}
          <div id="pipeline" style={{ marginTop: 64, position: 'relative', zIndex: 1 }}>
            <div style={{ backgroundColor: 'var(--surface-raised)', border: '1px solid var(--border-subtle)', borderRadius: 12, padding: 24 }} className="nk-card">
              {/* Header */}
              <div className="pipeline-header-bar">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--confidence-high)', display: 'block', animation: 'ping 1.5s cubic-bezier(0,0,0.2,1) infinite' }} />
                  <span className="font-mono text-label-code" style={{ color: 'var(--on-surface)', fontSize: 12 }}>
                    NutriKid Deterministic RAG Execution Path
                  </span>
                  <span className="badge badge-primary" style={{ fontSize: 10 }}>INFERENCE PIPELINE v1.4</span>
                </div>
                <div style={{ display: 'flex', gap: 20 }}>
                  <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                    Benchmark Queries: <strong style={{ color: 'var(--primary-container)' }}>30</strong>
                  </span>
                  <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                    MRR (Reranked): <strong style={{ color: 'var(--confidence-high)' }}>0.2751</strong>
                  </span>
                  <span className="font-mono text-label-tabular" style={{ fontSize: 11, color: 'var(--on-surface-variant)' }}>
                    Scope Refusal: <strong style={{ color: 'var(--secondary)' }}>100%</strong>
                  </span>
                </div>
              </div>

              {/* Nodes grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10 }}>
                {PIPELINE_STAGES.map((s) => (
                  <Link key={s.stage} href="/pipeline" style={{ textDecoration: 'none' }}>
                    <div
                      className={`pipeline-node ${s.highlight ? 'highlight' : ''}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span className="font-mono text-label-tabular" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
                          STAGE {s.stage}
                        </span>
                        <span className="material-symbols-outlined" style={{ fontSize: 15, color: s.color }}>
                          {s.icon}
                        </span>
                      </div>
                      <span className="font-geist" style={{ fontSize: 13, fontWeight: 600, color: 'var(--on-surface)', display: 'block', marginBottom: 4 }}>
                        {s.label}
                      </span>
                      <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)', fontSize: 11 }}>
                        {s.desc}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ─── STATS STRIP ─────────────────────────────────────────────── */}
        <section style={{ borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)' }}>
          <div style={{ maxWidth: 1400, margin: '0 auto', padding: '28px 32px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 24 }}>
            {[
              { value: String(CORPUS_STATS.active_documents), label: 'Active Documents', sub: 'Institutional Sources' },
              { value: String(CORPUS_STATS.total_pages).toLocaleString(), label: 'Pages Parsed', sub: '22 active PDFs' },
              { value: CORPUS_STATS.canonical_chunks.toLocaleString(), label: 'Canonical Chunks', sub: '6,422 indexed vectors' },
              { value: '8,351', label: 'Food Composition Rows', sub: 'IFCT 2017 (ICMR-NIN)' },
              { value: `${RETRIEVAL_METRICS.benchmark_queries}`, label: 'Benchmark Queries', sub: 'Evaluation dataset' },
              { value: `${RETRIEVAL_METRICS.reranked_bge.mrr.toFixed(4)}`, label: 'MRR (Reranked)', sub: 'BGE Cross-Encoder' },
              { value: `${GENERATION_METRICS.avg_rouge1.toFixed(2)}`, label: 'ROUGE-1 (Avg)', sub: '5-query generation eval' },
            ].map((stat) => (
              <div key={stat.label} style={{ textAlign: 'center' }}>
                <div className="metric-value" style={{ fontSize: 22, marginBottom: 4 }}>
                  {stat.value}
                </div>
                <div className="metric-label" style={{ fontSize: 11, marginBottom: 2 }}>{stat.label}</div>
                <div className="text-body-sm" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>{stat.sub}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ─── WHO BENEFITS ─────────────────────────────────────────────── */}
        <section style={{ maxWidth: 1400, margin: '0 auto', padding: '64px 32px' }}>
          <div style={{ marginBottom: 40, textAlign: 'center' }}>
            <span className="badge badge-secondary" style={{ marginBottom: 12 }}>Target Users</span>
            <h2 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginTop: 12 }}>
              Built for clinical decision-makers
            </h2>
            <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', maxWidth: 560, margin: '12px auto 0' }}>
              NutriKid provides evidence-grounded nutrition guidance tailored to the needs of healthcare professionals and caregivers.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            {BENEFICIARIES.map((b) => (
              <div key={b.label} className="nk-card" style={{ padding: '20px 16px', textAlign: 'center' }}>
                <div style={{ width: 44, height: 44, borderRadius: 10, backgroundColor: 'var(--surface-container-high)', border: '1px solid var(--border-highlight)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
                  <span className="material-symbols-outlined text-primary" style={{ fontSize: 22 }}>{b.icon}</span>
                </div>
                <span className="font-geist" style={{ fontSize: 14, fontWeight: 600, color: 'var(--on-surface)', display: 'block', marginBottom: 6 }}>{b.label}</span>
                <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{b.desc}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ─── WHY NUTRIKID ────────────────────────────────────────────── */}
        <section style={{ backgroundColor: 'var(--surface-raised)', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ maxWidth: 1400, margin: '0 auto', padding: '64px 32px' }}>
            <div style={{ marginBottom: 40 }}>
              <span className="badge badge-primary" style={{ marginBottom: 12 }}>System Differentiators</span>
              <h2 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginTop: 12 }}>
                Why NutriKid is different
              </h2>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
              {DIFFERENTIATORS.map((d) => (
                <div key={d.label} style={{ display: 'flex', gap: 14, padding: '18px 16px', backgroundColor: 'var(--surface-container-low)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ flexShrink: 0, width: 36, height: 36, borderRadius: 8, backgroundColor: 'rgba(0,229,201,0.08)', border: '1px solid rgba(0,229,201,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--primary-container)' }}>{d.icon}</span>
                  </div>
                  <div>
                    <span className="font-geist" style={{ fontSize: 14, fontWeight: 600, color: 'var(--on-surface)', display: 'block', marginBottom: 4 }}>{d.label}</span>
                    <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{d.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── INSTITUTIONAL SOURCES ───────────────────────────────────── */}
        <section style={{ maxWidth: 1400, margin: '0 auto', padding: '64px 32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, alignItems: 'center' }}>
            <div>
              <span className="badge badge-neutral" style={{ marginBottom: 12 }}>Source Corpus</span>
              <h2 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginTop: 12, marginBottom: 16 }}>
                Institutional authorities
              </h2>
              <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.7, marginBottom: 24 }}>
                NutriKid retrieves evidence exclusively from peer-reviewed publications and official guidelines issued by globally recognized health and nutrition authorities.
              </p>
              <div style={{ padding: '10px 14px', backgroundColor: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 8, marginBottom: 24 }}>
                <p className="text-body-sm" style={{ color: 'var(--confidence-medium)' }}>
                  <strong>Important:</strong> These institutions are sources of the underlying evidence. Their inclusion does not imply endorsement or certification of NutriKid.
                </p>
              </div>
              <Link href="/sources" className="btn-secondary" style={{ fontSize: 13 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 17 }}>folder_open</span>
                View Full Source Corpus
              </Link>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {SOURCES.map((s) => (
                <div key={s.abbr} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 18px', backgroundColor: 'var(--surface-container)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
                  <span className="font-mono text-label-code" style={{ fontSize: 13, fontWeight: 700, color: s.color, minWidth: 80 }}>{s.abbr}</span>
                  <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{s.full}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ─── SAFETY NOTE ─────────────────────────────────────────────── */}
        <section style={{ backgroundColor: 'rgba(239,68,68,0.04)', borderTop: '1px solid rgba(239,68,68,0.1)', borderBottom: '1px solid rgba(239,68,68,0.1)' }}>
          <div style={{ maxWidth: 900, margin: '0 auto', padding: '36px 32px', display: 'flex', gap: 20, alignItems: 'flex-start' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--confidence-medium)', flexShrink: 0 }}>info</span>
            <div>
              <h3 className="font-geist" style={{ fontSize: 16, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 8 }}>
                Clinical Disclaimer
              </h3>
              <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.7 }}>
                NutriKid is a research tool designed to retrieve and synthesize pediatric nutrition evidence. It is{' '}
                <strong style={{ color: 'var(--on-surface)' }}>not a medical diagnostic tool</strong> and should not replace qualified clinical judgment. All answers are evidence-grounded retrieval outputs, not medical prescriptions. Age scope: 5.0–15.0 years only.
              </p>
              <Link href="/safety" className="btn-ghost" style={{ marginTop: 12, padding: '6px 0', fontSize: 12 }}>
                View Safety & Scope Governance
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>arrow_forward</span>
              </Link>
            </div>
          </div>
        </section>

        {/* ─── BOTTOM CTA ──────────────────────────────────────────────── */}
        <section style={{ maxWidth: 800, margin: '0 auto', padding: '80px 32px', textAlign: 'center' }}>
          <h2 className="text-headline-lg" style={{ color: 'var(--on-surface)', marginBottom: 16 }}>
            Ready to retrieve evidence?
          </h2>
          <p className="text-body-lg" style={{ color: 'var(--on-surface-variant)', marginBottom: 32 }}>
            Enter a pediatric nutrition question and child age to get an evidence-grounded, citation-backed answer from 6,422 curated chunks.
          </p>
          <Link href="/ask" className="btn-primary" style={{ padding: '14px 32px', fontSize: 16 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 22 }}>auto_awesome</span>
            Launch Clinical Query Engine
          </Link>
        </section>

        {/* Footer */}
        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '24px 32px', textAlign: 'center' }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)', letterSpacing: '0.04em' }}>
            NUTRIKID PEDIATRIC NUTRITION RAG SYSTEM · {CORPUS_STATS.canonical_chunks.toLocaleString()} CHUNKS · {CORPUS_STATS.active_documents} ACTIVE DOCUMENTS · {CORPUS_STATS.total_pages.toLocaleString()} PAGES · SCOPE: 5.0–15.0 YEARS · NOT FOR CLINICAL DIAGNOSIS
          </p>
        </footer>

      </main>
    </>
  );
}
