---
name: NutriKid Clinical Interface
colors:
  surface: '#0e141d'
  surface-dim: '#0e141d'
  surface-bright: '#343944'
  surface-container-lowest: '#080e17'
  surface-container-low: '#161c25'
  surface-container: '#1a2029'
  surface-container-high: '#242a34'
  surface-container-highest: '#2f353f'
  on-surface: '#dde2f0'
  on-surface-variant: '#b9cac5'
  inverse-surface: '#dde2f0'
  inverse-on-surface: '#2b313b'
  outline: '#84948f'
  outline-variant: '#3b4a46'
  surface-tint: '#00dfc4'
  primary: '#70ffe5'
  on-primary: '#00372f'
  primary-container: '#00e5c9'
  on-primary-container: '#006155'
  inverse-primary: '#006b5d'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#b5f5e6'
  on-tertiary: '#003730'
  tertiary-container: '#99d8ca'
  on-tertiary-container: '#1f6055'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#41fcdf'
  primary-fixed-dim: '#00dfc4'
  on-primary-fixed: '#00201b'
  on-primary-fixed-variant: '#005046'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#b0efe1'
  tertiary-fixed-dim: '#94d3c5'
  on-tertiary-fixed: '#00201b'
  on-tertiary-fixed-variant: '#075046'
  background: '#0e141d'
  on-background: '#dde2f0'
  surface-variant: '#2f353f'
  surface-base: '#070C13'
  surface-raised: '#0E1724'
  surface-overlay: '#152233'
  border-subtle: rgba(255, 255, 255, 0.08)
  border-highlight: rgba(0, 229, 201, 0.25)
  surgical-blue: '#0284C7'
  confidence-high: '#10B981'
  confidence-medium: '#F59E0B'
  confidence-low: '#EF4444'
  provenance-tag: '#082F49'
  citation-text: '#93C5FD'
  chart-accent: '#A5D334'
  ice-glow: '#E2F9FB'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-provenance:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.05em
  label-tabular:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: '0'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers an authoritative, deterministic clinical decision-support interface tailored for pediatric nutritionists, clinical dietitians, and pediatric intensive care specialists. 

The emotional tone balances surgical precision with clinical assurance: objective, analytical, transparent, and calm under high-cognitive-load settings. It translates complex retrieval-augmented intelligence into immediate, high-fidelity clinical guidance without visual noise or ambiguity.

The design movement combines **Technical Glassmorphism** with **High-Density Clinical Minimalism**:
- Subdued, deep navy/slate backdrops that minimize eye fatigue during extended clinical rounds.
- Ultra-refined 1px structural boundaries with selective luminous accents in cyan, cool surgical blue, and bio-teal.
- Deep information density featuring structured metadata, persistent source attribution, and deterministic verification badges.
- Crisp, monospaced data anchors that emphasize algorithmic accountability, page provenance, and confidence intervals.

## Colors

The palette employs a deep midnight foundation anchored by high-clarity luminescent accents.

- **Primary (`#00E5C9`)**: Electric luminous cyan used exclusively for active focus states, verified pediatric guideline indicators, retrieval certainty signals, and key clinical action paths.
- **Secondary (`#38BDF8`)**: Cool surgical azure for non-destructive actions, secondary metadata tags, contextual links, and informational status bars.
- **Tertiary (`#014D43`)**: Deep clinical pine; serves as grounded backdrop fills for verified evidence blocks, callout panels, and low-contrast surface elevation.
- **Neutral (`#0B111A`)**: Deep near-black navy foundation. Tonal tiers (`#070C13` base, `#0E1724` cards, `#152233` dialogs) structure the information architecture without harsh pure-black cutoffs.

### Semantic Provenance & Metrics
Status tokens strictly demarcate RAG retrieval fidelity:
- **High Confidence (`#10B981`)**: Direct guideline concordance (≥95%).
- **Medium Caution (`#F59E0B`)**: Extrapolated dosage/nutritional calculations requiring human clinician validation.
- **Low Confidence/Outlier (`#EF4444`)**: Insufficient pediatric trial evidence or conflicting literature citations.

## Typography

Typography enforces a strict division of cognitive duties across three specialized font families:

- **Headlines (Geist)**: Pure geometry, tight tracking, and contemporary neutrality for clinical section headers, modal banners, and diagnostic case summaries.
- **Body & Clinical Narrative (Inter)**: High x-height, clear optical kerning, and open counters optimized for rapid parsing of complex medical prose, enteral feed protocols, and patient histories.
- **Provenance, Metrics & IDs (JetBrains Mono)**: Monospaced glyphs applied to document tracking IDs (e.g., `NK-015-C00014`), confidence percentages, dosing mathematics, gestational age calculations, and exact source bibliography page references.

Tabular figures are enabled globally by default on numeric strings to guarantee vertical alignment across clinical data columns.

## Layout & Spacing

The interface employs a dense, structured 12-column responsive grid engineered for multi-column clinical workflows (e.g., patient parameters sidebar, center RAG narrative answer, right-hand source document inspector).

### Grid & Breakpoints
- **Desktop (≥ 1440px)**: 12 columns, 24px (`gutter-lg`) gutters, 40px (`margin-lg`) canvas margins. Max layout bound at 1800px to maintain ocular scanning efficiency across data tables.
- **Tablet / Workstation (768px - 1439px)**: 8 columns, 16px (`gutter`) gutters, 24px (`margin-md`) margins. The document inspector converts into a slide-over panel.
- **Mobile Handheld (< 768px)**: 4 columns, 12px gutters, 16px (`margin`) margins. Full stacked triage view prioritizing critical recommendations followed by expand-on-demand provenance cards.

### Spacing Rhythm
Spatial increments use strict 4px base factors. Internal component padding favors vertical compactness (`space-xs` and `space-sm`) to ensure medical charts and dosage verification sequences remain visible without continuous vertical scrolling.

## Elevation & Depth

Visual separation does not rely on heavy drop shadows; rather, it uses a clinical **Surface-Tier and Translucent Boundary** paradigm.

### Depth Layers
- **Canvas Base (`#070C13`)**: The ground plane for application navigation and workspace framing.
- **Surface Layer 1 (`#0E1724` with 80% opacity and 12px blur)**: Data cards, patient metric panels, and clinical calculation blocks. Outlined with `rgba(255, 255, 255, 0.08)`.
- **Surface Layer 2 (`#152233` with 90% opacity and 16px blur)**: Active inspector panels, focused citation overlays, and elevated dropdown menus.
- **Floating Modals & Critical Overlays**: Backed by a full blur filter (`backdrop-filter: blur(24px)`) and a deliberate 1px luminescent border in `rgba(0, 229, 201, 0.20)`.

### Ambient Glows
Diffused ambient glows are restricted to real-time operations: a subtle 8px blur with 15% opacity cyan tint marks actively synthesizing RAG outputs, while high-confidence source matches exhibit a gentle emerald edge glow.

## Shapes

The system uses a **Soft (Level 1)** geometric standard (4px base radii, 8px on larger containers).

- **4px (`rounded-sm` / base)**: Input fields, data pills, monospaced tag badges, segmented dosage switches, and inline citation triggers.
- **8px (`rounded-lg`)**: Primary cards, document comparison sheets, clinical data tables, and slide-in trays.
- **12px (`rounded-xl`)**: Primary application modals and system-level alerts.

Rounded geometries are intentionally restrained to convey institutional authority, structural rigor, and seamless alignment against rigid tabular grids.

## Components

### Buttons
- **Primary Clinical Action**: Cyan fill (`#00E5C9`), near-black text (`#070C13`, Geist Medium), 4px radius, 36px total height. Hover generates a soft cyan radiance (`box-shadow: 0 0 12px rgba(0, 229, 201, 0.3)`).
- **Secondary / Evidence Action**: Transparent background, 1px border (`rgba(255, 255, 255, 0.15)`), white text (`#F8FAFC`). Hover engages a surface shift (`#0E1724`) and light border transition (`rgba(56, 189, 248, 0.4)`).
- **Destructive Action**: Crimson border (`#EF4444`), semi-translucent deep red fill (`rgba(239, 68, 68, 0.1)`), bright coral text.

### Provenance Chips & Confidence Badges
- Rendered in `JetBrains Mono` at 11px uppercase.
- Contain a dual-element schema: a 6px status bead indicating guideline confidence (green/amber/red) coupled with the alphanumeric retrieval token (e.g., `[NK-REF-42]`).
- Hovering triggers an immediate inline mini-preview of the retrieved study, author, journal impact factor, and exact page quote.

### Scientific Data Tables
- Header row fixed at 32px height, uppercase 11px mono labels with `border-subtle` bottom rule.
- Zebra row banding suppressed; instead, uses a 1px divider (`rgba(255, 255, 255, 0.04)`) and a swift highlight wash (`rgba(56, 189, 248, 0.05)`) on row hover.
- Tabular figures aligned right for numerical pediatric parameters (e.g., mL/kg/day, kcal/oz, osmolarity mOsm/kg).

### Input Fields & Search Bars
- Background: `#0A1017`, border: 1px `rgba(255, 255, 255, 0.12)`.
- Active focus invokes a precise 1px electric cyan frame with an inset glow: `box-shadow: 0 0 0 1px #00E5C9`.
- Query input includes embedded prompt syntax highlighting for pediatric patient variables (age, weight, gestational week, primary diagnosis).

### RAG Synthesis Cards & Inspector Drawer
- **Output Container**: Surface-raised background featuring a left-edge indicator bar colored by guideline concordance.
- **Source Inspector Drawer**: Right-anchored split pane showing verbatim PDF extracts, bounding box highlights matching the retrieved snippet, and direct PubMed/Cochrane DOI cross-references.