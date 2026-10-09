---
name: Clinical Precision & Pediatric Nutrition Research
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#3d4947'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#6d7a77'
  outline-variant: '#bcc9c6'
  surface-tint: '#006a60'
  primary: '#00685e'
  on-primary: '#ffffff'
  primary-container: '#008377'
  on-primary-container: '#f4fffb'
  inverse-primary: '#67d9c9'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#545c72'
  on-tertiary: '#ffffff'
  tertiary-container: '#6c748b'
  on-tertiary-container: '#fefcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f6e5'
  primary-fixed-dim: '#67d9c9'
  on-primary-fixed: '#00201c'
  on-primary-fixed-variant: '#005048'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#dae2fd'
  tertiary-fixed-dim: '#bec6e0'
  on-tertiary-fixed: '#131b2e'
  on-tertiary-fixed-variant: '#3f465c'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 3rem
    fontWeight: '700'
    lineHeight: 3.5rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 2rem
    fontWeight: '600'
    lineHeight: 2.5rem
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
  body-lg:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.375rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1.125rem
  label-lg:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '600'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 0.75rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system reflects an exacting standard of pediatric nutritional science and clinical diagnostics. It targets pediatricians, clinical dietitians, researchers, and healthcare professionals who require absolute clarity, high information density, and uncompromised legibility when evaluating patient growth trajectories and metabolic metrics.

The visual aesthetic operates at the intersection of **Modern Corporate Healthcare** and **Scientific Instrument Precision**. It eschews decorative fluff in favor of razor-sharp hierarchy, clinical clean surfaces, high-contrast typography, and deliberate accentuation. The mood is authoritative, sterile yet human-centered, profoundly trustworthy, and rigorously analytical.

## Colors
The palette leverages clinical whites, surgical cool slates, and analytical teals to evoke diagnostic accuracy.

- **Primary (`#009688` / Medical Teal):** Communicates vitality, pediatric care, and primary interactive agency. Used for focal call-to-actions, primary active states, and clinical verification metrics.
- **Secondary (`#0284c7` / Analytical Cyan):** Signifies telemetry, longitudinal data plots, comparative centile curves, and secondary links.
- **Tertiary (`#0f172a` / Deep Clinical Navy):** Anchors table headers, structural framing, metric totals, and authoritative emphasis.
- **Neutrals & Surfaces:** Pure White (`#ffffff`) serves as the base for data cards and modal surfaces. Cool Slate 50 (`#f8fafc`) and Slate 100 (`#f1f5f9`) establish background contrast and non-interactive track zones.
- **Borders & Dividers:** Slate 200 (`#e2e8f0`) for low-contrast structure; Slate 300 (`#cbd5e1`) for high-precision table grids and input borders.
- **Semantic Signals:** Success/Normal (`#059669`), Warning/Borderline (`#d97706`), Critical/Malnutrition Risk (`#dc2626`).

## Typography
The system pairs **Plus Jakarta Sans** for headlines with **Inter** for body text and telemetry labels. Plus Jakarta Sans brings an approachable, slightly rounded modernism suited to pediatric domains, while Inter ensures neutral, uncompromised legibility across dense biometric grids and tabular datasets.

- Tabular figures (`font-variant-numeric: tabular-nums`) must be enforced for all biometric parameters (height percentiles, z-scores, caloric intakes).
- High contrast is maintained strictly across all weights: primary headings use Deep Charcoal (`#0f172a`), running body uses Intermediate Slate (`#334155`), and supportive metadata uses Slate (`#64748b`).

## Layout & Spacing
The layout follows a fluid 12-column grid system optimized for clinical dashboards and dual-pane patient charting.

- **Desktop (≥ 1280px):** 12 columns, 24px (`1.5rem`) gutters, 32px (`2rem`) outer margins. Supports persistent left-hand navigation and side-by-side growth charts vs. nutritional intake tables.
- **Tablet (768px – 1279px):** 8 columns, 16px (`1rem`) gutters, 24px (`1.5rem`) outer margins. Side panels collapse into tabbed overlays.
- **Mobile (< 768px):** 4 columns, 12px (`0.75rem`) gutters, 16px (`1rem`) outer margins. Charts reflow into vertical scrollable cards with horizontal pinch-zoom.
- Spacing rhythm strictly utilizes multiples of 4px/8px to ensure structural alignment across complex diagnostic components.

## Elevation & Depth
Depth is established primarily through **tonal separation** and **subtle, crisp outlines** rather than heavy drop shadows, reinforcing a sterile, flat scientific surface.

- **Level 0 (Base Canvas):** `#f8fafc` — provides an anti-glare, cool slate ground.
- **Level 1 (Clinical Cards & Data Surfaces):** `#ffffff` with a crisp 1px solid border (`#e2e8f0`) and an ambient micro-shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.02)`.
- **Level 2 (Hovered Metrics & Tooltips):** `#ffffff` with border `#cbd5e1` and elevation `0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`.
- **Level 3 (Modals, Overlays, Patient Drawers):** `#ffffff` with border `#e2e8f0` and an authoritative backdrop shadow: `0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)`.
- **Active Focus Layers:** Outer rings use semi-transparent teal outlines (`0 0 0 3px rgba(0, 150, 136, 0.15)`) for clinical accessibility compliance.

## Shapes
A "Soft" roundedness tier (`roundedness: 1` — base radius `0.25rem` / `4px`) is utilized. This maintains an exacting scientific and lab-calibrated demeanor, signaling precision and professional discipline.

- Structural containers, telemetry cards, and data tables use `0.375rem` (6px) or `0.5rem` (8px).
- Status tags, indicators, and chips feature contained `0.25rem` (4px) edges. Pill shapes are strictly reserved for live physiological badges (e.g., patient telemetry tags).

## Components

### Buttons
- **Primary:** Medical Teal background (`#009688`), White text (`#ffffff`), hover state `#00796b`. Crisp 4px border radius, medium weight typography.
- **Secondary:** White background (`#ffffff`), Slate 300 border (`#cbd5e1`), Charcoal text (`#0f172a`), hover state `#f8fafc`.
- **Tertiary / Clinical Action:** Ghost styling with `#0284c7` text, hovering to `#f0f9ff`.

### Chips & Clinical Badges
- Compact height (`24px`), small bold text (`label-sm`), uppercase tracking.
- **Percentile Status:** Teal light (`#e0f2f1` fill, `#00796b` text) for normal ranges; Amber light (`#fef3c7` fill, `#92400e` text) for monitoring; Rose light (`#ffe4e6` fill, `#9f1239` text) for critical flags.

### Lists & Data Tables
- Row striping using pure white alternating with `#f8fafc`.
- Header rows utilize Navy Tint (`#0f172a`), uppercase 11px font with 0.05em tracking and a solid `#cbd5e1` bottom border.
- Numeric columns right-aligned with fixed tabular glyph spacing.

### Checkboxes & Radios
- Size: 16x16px. Border: 1.5px solid `#94a3b8`.
- Checked state: `#009688` fill with crisp white internal mark. Minimal 2px radius for checkboxes, full circle for radios.

### Input Fields & Search Bars
- Background: Pure White (`#ffffff`), 1px solid border (`#cbd5e1`), 6px radius.
- Height: 36px (compact clinical density) or 40px (standard).
- Focus: Border switches to `#009688` with a 3px ring of `rgba(0, 150, 136, 0.15)`.

### Cards
- Pure White base, 1px solid `#e2e8f0` outline, subtle 1px ambient shadow. Card headers include a separate bottom border partition (`#f1f5f9`) separating patient bio-data from longitudinal metrics.

### Specialized Clinical Components
- **Percentile Curve Legend:** Micro-indicator with color-matched stroke and min/max reference bands.
- **Nutritional Macro Split Bar:** Segmented inline horizontal bar featuring rounded terminal ends, separating protein, lipid, and carbohydrate ratios with high-contrast scientific fills.