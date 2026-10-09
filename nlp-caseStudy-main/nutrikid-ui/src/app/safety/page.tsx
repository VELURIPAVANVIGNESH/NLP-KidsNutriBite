'use client';

import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { CORPUS_STATS } from '@/lib/corpus';

const SAFETY_MECHANISMS = [
  {
    id: 'AGE_BOUNDARY',
    label: 'Age Boundary Enforcement',
    icon: 'child_care',
    color: 'var(--primary-container)',
    status: 'ENFORCED',
    statusColor: 'var(--confidence-high)',
    description: 'All queries are validated against a hard age boundary: 5.0 ≤ age ≤ 15.0 years. Ages outside this range trigger an immediate, informative refusal before any retrieval or generation is invoked.',
    implementation: 'generation/qwen_generator.py → run_qwen_pipeline()',
    detail: `If child_age < 5.0 or child_age > 15.0:
→ Return scope_status: "out_of_scope"
→ Return human-readable refusal message
→ No retrieval. No generation. No model inference.`,
  },
  {
    id: 'EVIDENCE_GROUNDING',
    label: 'Evidence Grounding',
    icon: 'verified',
    color: 'var(--secondary)',
    status: 'ENFORCED',
    statusColor: 'var(--confidence-high)',
    description: 'The system prompt explicitly instructs the model to answer ONLY using the provided evidence passages. If the retrieved evidence does not contain the specific recommendation requested, the model is instructed to state this explicitly rather than fabricate an answer.',
    implementation: 'generation/qwen_generator.py → SYSTEM_PROMPT',
    detail: 'Rule: "Answer ONLY using the evidence passages provided. Do NOT hallucinate."\nRule: "If evidence is insufficient, state: The retrieved evidence contains insufficient information to determine [X]"',
  },
  {
    id: 'NUTRIENT_FIDELITY',
    label: 'Nutrient Fidelity Guard',
    icon: 'biotech',
    color: 'var(--chart-accent)',
    status: 'ENFORCED',
    statusColor: 'var(--confidence-high)',
    description: 'Post-generation deterministic validation detects and blocks cross-nutrient unit contamination — for example, preventing iodine µg/day values (90 µg) from being incorrectly presented as protein RDA in grams. This guards the GEN001 class of errors.',
    implementation: 'generation/nutrient_fidelity_guard.py → apply_fidelity_guard()',
    detail: 'Guard rules: protein (g/day), iron/zinc (mg/day), iodine/folate (µg/day)\nIf contamination detected → override with "Insufficient Evidence" response\nfidelity_check.passed: true/false returned in API response',
  },
  {
    id: 'CORPUS_SCOPE',
    label: 'Corpus Scope Restriction',
    icon: 'folder_off',
    color: 'var(--confidence-medium)',
    status: 'ENFORCED',
    statusColor: 'var(--confidence-high)',
    description: 'Only documents with retrieval_enabled: true in the corpus manifest are indexed and retrievable. Documents in 04_OUT_OF_SCOPE_INFANT (age 0–4) and evaluation-context-only documents are explicitly excluded from the FAISS and BM25 indexes.',
    implementation: 'preprocessing/preprocess_knowledge.py → filter_enabled_sources()',
    detail: 'Active (retrieval_enabled=true): 22 documents\nExcluded (infant 0-4y): NK-027 to NK-032\nExcluded (eval context): NK-025, NK-026\nOut-of-scope leakage verified: 0 chunks in evaluation',
  },
  {
    id: 'INSUFFICIENT_EVIDENCE',
    label: 'Insufficient Evidence Handling',
    icon: 'block',
    color: 'var(--confidence-low)',
    status: 'ENFORCED',
    statusColor: 'var(--confidence-high)',
    description: 'When the retrieval pipeline returns no evidence passages (empty evidence_items), the system returns a standardized "Insufficient Evidence" response rather than allowing the model to generate a response without grounding.',
    implementation: 'generation/qwen_generator.py → generate_answer()',
    detail: 'if not evidence_items:\n→ Return: "Insufficient Evidence: The retrieved corpus contains insufficient evidence for this query."\n→ citations: []\n→ No model inference attempted',
  },
  {
    id: 'NON_DIAGNOSTIC',
    label: 'Non-Diagnostic Status',
    icon: 'stethoscope_arrow',
    color: 'var(--on-surface-variant)',
    status: 'BY DESIGN',
    statusColor: 'var(--secondary)',
    description: 'NutriKid is explicitly not a medical diagnostic tool. The system is designed for evidence retrieval and synthesis only. All responses are evidence-grounded retrieval outputs and should not replace qualified clinical judgment.',
    implementation: 'System design principle — enforced at UI and documentation level',
    detail: 'Displayed on: homepage, ask page, all footers\nAPI response includes no diagnostic framing\nNo disease diagnosis, prescription, or treatment recommendations',
  },
];

const BOUNDARY_EXAMPLES = [
  { age: 2, question: 'Protein for 2-year-old toddler', status: 'out_of_scope', response: 'Age 2.0 is outside the NutriKid scope (5–15 years). This is a protective system boundary, not a technical error.', color: 'var(--confidence-medium)' },
  { age: 17, question: 'Calcium for 17-year-old', status: 'out_of_scope', response: 'Age 17.0 is outside the NutriKid scope (5–15 years). Evidence for adolescents aged 16+ requires specialist consultation.', color: 'var(--confidence-medium)' },
  { age: 8, question: 'Iron RDA for 8-year-old', status: 'in_scope', response: 'Proceeds to retrieval → reranking → generation with evidence-grounded response.', color: 'var(--confidence-high)' },
  { age: 15, question: 'Sodium limits for 15-year-old', status: 'in_scope', response: 'Age at upper boundary — accepted and processed normally.', color: 'var(--confidence-high)' },
];

export default function SafetyPage() {
  return (
    <>
      <Navbar />
      <main style={{ paddingTop: 64, minHeight: '100vh', backgroundColor: 'var(--surface-base)' }}>
        <div style={{ maxWidth: 1300, margin: '0 auto', padding: '40px 24px' }}>

          {/* Page header */}
          <div style={{ marginBottom: 40, textAlign: 'center' }}>
            <span className="badge badge-high" style={{ marginBottom: 12 }}>Safety Governance</span>
            <h1 className="text-headline-xl" style={{ color: 'var(--on-surface)', marginBottom: 16, marginTop: 8 }}>
              NutriKid Safety & Scope Governance
            </h1>
            <p className="text-body-lg" style={{ color: 'var(--on-surface-variant)', maxWidth: 700, margin: '0 auto', lineHeight: 1.7 }}>
              NutriKid is built with safety boundaries as first-class system constraints — not afterthoughts.
              Every mechanism described here is implemented in the actual codebase.
            </p>
          </div>

          {/* Critical disclaimer */}
          <div style={{ marginBottom: 40, padding: '20px 24px', backgroundColor: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 12, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 28, color: 'var(--confidence-low)', flexShrink: 0 }}>gpp_maybe</span>
            <div>
              <h2 className="font-geist" style={{ fontSize: 17, fontWeight: 700, color: 'var(--on-surface)', marginBottom: 10 }}>
                Clinical Disclaimer — Read Before Use
              </h2>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  'NutriKid is a research evidence retrieval tool, not a medical device or diagnostic system.',
                  'Answers are evidence-grounded retrieval outputs, not medical prescriptions or clinical diagnoses.',
                  'All outputs must be reviewed by qualified clinical nutrition professionals before any clinical application.',
                  'NutriKid does not diagnose disease, prescribe treatment, or guarantee medical accuracy.',
                  'System scope is strictly limited to children aged 5.0–15.0 years.',
                  'Evidence is sourced from institutional publications, not from real-time clinical data or patient records.',
                ].map((point, i) => (
                  <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--confidence-low)', flexShrink: 0, marginTop: 2 }}>warning</span>
                    <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.6 }}>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Scope boundary summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 40 }}>
            {[
              { label: 'Age Scope Minimum', value: `${CORPUS_STATS.age_scope_min} years`, icon: 'arrow_downward', color: 'var(--secondary)' },
              { label: 'Age Scope Maximum', value: `${CORPUS_STATS.age_scope_max} years`, icon: 'arrow_upward', color: 'var(--primary-container)' },
              { label: 'Scope Enforcement', value: 'Pre-retrieval', icon: 'shield', color: 'var(--confidence-high)' },
              { label: 'Refusal Precision', value: '100% (Verified)', icon: 'verified', color: 'var(--confidence-high)' },
              { label: 'Fidelity Guard', value: 'Post-generation', icon: 'biotech', color: 'var(--chart-accent)' },
              { label: 'Out-of-Scope Leakage', value: '0 chunks', icon: 'block', color: 'var(--confidence-high)' },
            ].map((m) => (
              <div key={m.label} className="metric-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: m.color }}>{m.icon}</span>
                  <span className="metric-label" style={{ fontSize: 10 }}>{m.label}</span>
                </div>
                <span className="metric-value" style={{ fontSize: 18, color: m.color }}>{m.value}</span>
              </div>
            ))}
          </div>

          {/* Safety mechanisms */}
          <div style={{ marginBottom: 40 }}>
            <h2 className="font-geist" style={{ fontSize: 20, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 20 }}>
              Implemented Safety Mechanisms
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {SAFETY_MECHANISMS.map((mech) => (
                <div
                  key={mech.id}
                  style={{ backgroundColor: 'var(--surface-raised)', borderTop: '1px solid var(--border-subtle)', borderRight: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)', borderLeft: `3px solid ${mech.color}`, borderRadius: 10, padding: '20px 24px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
                    <div style={{ width: 38, height: 38, borderRadius: 8, backgroundColor: 'var(--surface-container)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 20, color: mech.color }}>{mech.icon}</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
                        <h3 className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)' }}>{mech.label}</h3>
                        <span className="badge" style={{ fontSize: 9, color: mech.statusColor, backgroundColor: `${mech.statusColor}15`, border: `1px solid ${mech.statusColor}40` }}>
                          {mech.status}
                        </span>
                      </div>
                      <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', lineHeight: 1.7, marginBottom: 12 }}>{mech.description}</p>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                        <div>
                          <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 6 }}>IMPLEMENTATION</span>
                          <span className="badge badge-citation" style={{ fontSize: 10 }}>{mech.implementation}</span>
                        </div>
                        <div>
                          <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--on-surface-variant)', display: 'block', marginBottom: 6 }}>LOGIC</span>
                          <pre style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: mech.color, lineHeight: 1.5, whiteSpace: 'pre-wrap', backgroundColor: 'var(--surface-container-low)', padding: '8px 10px', borderRadius: 6 }}>
                            {mech.detail}
                          </pre>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Age boundary examples */}
          <div style={{ marginBottom: 40 }}>
            <h2 className="font-geist" style={{ fontSize: 18, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 16 }}>
              Age Boundary Behaviour Examples
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
              {BOUNDARY_EXAMPLES.map((ex) => (
                <div
                  key={ex.age}
                  style={{ padding: '18px 20px', backgroundColor: 'var(--surface-container)', borderRadius: 10, borderTop: `1px solid ${ex.color}30`, borderRight: `1px solid ${ex.color}30`, borderBottom: `1px solid ${ex.color}30`, borderLeft: `3px solid ${ex.color}` }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span className="font-mono text-label-code" style={{ fontSize: 13, fontWeight: 700, color: ex.color }}>Age: {ex.age}y</span>
                    <span className="badge" style={{ fontSize: 9, color: ex.color, backgroundColor: `${ex.color}15`, border: `1px solid ${ex.color}40` }}>
                      {ex.status === 'in_scope' ? '✓ IN SCOPE' : '✗ OUT OF SCOPE'}
                    </span>
                  </div>
                  <p className="text-body-sm" style={{ color: 'var(--on-surface-variant)', marginBottom: 8 }}>
                    <em>&quot;{ex.question}&quot;</em>
                  </p>
                  <div style={{ padding: '8px 10px', backgroundColor: 'var(--surface-container-low)', borderRadius: 6 }}>
                    <p className="text-body-sm" style={{ color: ex.color, fontSize: 11 }}>{ex.response}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Language note */}
          <div style={{ padding: '20px 24px', backgroundColor: 'var(--surface-raised)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
            <h3 className="font-geist" style={{ fontSize: 15, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 10 }}>
              Language & Claims Policy
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--confidence-high)', display: 'block', marginBottom: 8 }}>✓ ACCEPTABLE LANGUAGE</span>
                {['Evidence-grounded', 'Source-traceable', 'Age-bounded', 'Validation-aware', 'Retrieved from institutional guidelines'].map((t) => (
                  <div key={t} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--confidence-high)' }}>check</span>
                    <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{t}</span>
                  </div>
                ))}
              </div>
              <div>
                <span className="font-mono text-label-provenance" style={{ fontSize: 9, color: 'var(--confidence-low)', display: 'block', marginBottom: 8 }}>✗ NOT ACCEPTABLE</span>
                {['100% hallucination-free', 'Guaranteed medically accurate', 'Replaces clinical judgment', 'Diagnostic capability', 'Zero error rate'].map((t) => (
                  <div key={t} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--confidence-low)' }}>close</span>
                    <span className="text-body-sm" style={{ color: 'var(--on-surface-variant)' }}>{t}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Test the system */}
          <div style={{ marginTop: 40, textAlign: 'center', padding: '32px 24px', backgroundColor: 'var(--surface-raised)', borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
            <h3 className="font-geist" style={{ fontSize: 18, fontWeight: 600, color: 'var(--on-surface)', marginBottom: 12 }}>
              Test the Age Boundary Yourself
            </h3>
            <p className="text-body-md" style={{ color: 'var(--on-surface-variant)', marginBottom: 20 }}>
              The Clinical Query Engine has a built-in out-of-scope test preset. Try age 2 to see the actual refusal response.
            </p>
            <Link href="/ask" className="btn-primary" style={{ fontSize: 14 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>auto_awesome</span>
              Open Query Engine
            </Link>
          </div>
        </div>

        <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--surface-raised)', padding: '16px 24px', textAlign: 'center', marginTop: 40 }}>
          <p className="font-mono text-label-provenance" style={{ fontSize: 10, color: 'var(--on-surface-variant)' }}>
            NUTRIKID SAFETY GOVERNANCE · AGE SCOPE: {CORPUS_STATS.age_scope_min}–{CORPUS_STATS.age_scope_max} YEARS · NOT A MEDICAL DEVICE · NOT FOR CLINICAL DIAGNOSIS
          </p>
        </footer>
      </main>
    </>
  );
}
