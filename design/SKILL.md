---
name: design
description: Atharva's personal frontend design system — an editorial, technical, archival aesthetic combining serif display type, monospace metadata, warm paper-toned palettes, rust accents, dot-grid textures, and schematic-style component framing. Use this skill whenever Atharva asks for any kind of frontend, UI, web page, landing page, dashboard, artifact, component, mockup, poster, slide design, or "make this look good" / "style this" / "design this" request — even if they don't explicitly invoke this skill or mention design preferences. The skill defines a specific aesthetic point of view (paper not screen, one surgical accent, mono-as-metadata, italic-as-emphasis, hairlines not boxes, number everything) and should override generic frontend defaults like Inter-on-white, purple gradients, or cookie-cutter dashboard layouts.
---

# Atharva's Design System

A reference aesthetic for any frontend work Atharva asks for. The look is editorial-technical: warm paper canvas, surgical rust accent, literary serif display paired with mono metadata, hairline-bounded schematic cards. It reads like a well-typeset technical manual or an archival spec sheet, not a SaaS landing page.

This skill describes the **taste**, not a fixed template. Apply it to whatever Atharva is building — a landing page, a dashboard, a docs site, an internal tool, a presentation — and adapt the principles to fit. The design.strategy - derived example in `examples/this-style-example.html` shows one full execution; reference it for proportions, spacing, and detail handling, but don't copy it wholesale.

## When to use

Apply this skill any time Atharva asks for:
- A web page, landing page, marketing site, or portfolio
- A dashboard, internal tool, or admin interface
- A React/HTML/CSS component or full artifact
- A "design", "mockup", "style", "theme", or "look and feel" request
- Slides or a poster where visual design matters
- Anything where you'd otherwise reach for generic AI defaults

If the request is purely functional (e.g. "fix this bug in my React state logic") and Atharva isn't asking about appearance, skip this skill. But if any styling decision is involved, default to this aesthetic.

## The six commitments

These are non-negotiable. Every design that comes out of this skill respects all six.

### 1. Paper, not screen
The canvas is **warm cream**, never pure white. Subtle texture — a radial dot-grid or fine noise — sits behind everything to evoke archival print. Use tinted paper layers (cream → tinted panel → deeper panel) instead of shadows or elevation.

### 2. One accent, used surgically
A single chromatic accent (rust orange `#C0622A` by default) does all the emotional work. It appears on:
- Italic emphasis in display headlines
- Section numbers and indices
- Corner ticks on cards
- Links and CTAs
- Small status indicators

Never use a second saturated color. Never spread the accent across large fills. If a design "needs more color," resist — add typographic contrast instead.

### 3. Mono as metadata
Every label, code reference, index number, system state, version string, and "// SECTION" marker runs in monospace. The serif speaks; the mono annotates. This creates the signature spec-sheet feel.

### 4. Italic as emphasis
Replace bold with **serif italic** in the accent color. Headlines read like a magazine pull-quote, not a marketing banner. `<em>` does what `<strong>` would in a generic design.

### 5. Hairlines, not boxes
Containers are bounded by **1px borders** on tinted backgrounds. No drop shadows. No rounded corners (or barely any — 0–4px max). Add accent-colored corner ticks (10px L-brackets at top-left + bottom-right) on featured cards to imply schematic framing without weight.

### 6. Number everything
Sections get `// 01 — SECTION NAME` headers. Cards get `001`, `002` indices. Principles get `PRINCIPLE 04`. Numbering implies authorship, version, intentionality — it makes the work feel deliberate.

## Default token palette

Use these CSS variables as the starting point. Adjust hues if context demands (a dashboard for a finance product might warrant a deeper paper; a docs site might lean cooler), but keep the **structure** — three paper tones, three accent depths, three ink levels.

```css
:root {
  /* Surfaces — warm cream, layered */
  --bg:       #F4EFE4;  /* canvas */
  --bg-alt:   #ECE5D2;  /* panel */
  --bg-deep:  #E4DCC4;  /* nested */

  /* Ink — never pure black */
  --ink:       #1A1A1A;  /* primary body */
  --ink-soft:  #3A352D;  /* secondary */
  --ink-mute:  #8A8377;  /* labels, captions */
  --line:      #D9D1BC;  /* hairline rules */

  /* Accent — the one chromatic note */
  --accent:       #C0622A;  /* rust — primary */
  --accent-soft:  #E89A6B;  /* highlight tint */
  --accent-deep:  #8A4218;  /* pressed/serious */
}
```

**Alternative accent moods** if rust doesn't fit the project:
- Deep sea: `#1E5A6B` / `#3D8A9E` / `#0F3340`
- Oxblood: `#7A2828` / `#B85454` / `#4D1414`
- Moss: `#4A6B3D` / `#7A9E5E` / `#2D4520`
- Indigo ink: `#2D3866` / `#5468A8` / `#161E40`

Pick one and stick to it. Never combine accent moods.

## Default type stack

```css
--font-display: 'Fraunces', 'Times New Roman', serif;
--font-body:    'Inter', system-ui, sans-serif;
--font-mono:    'JetBrains Mono', 'SF Mono', Menlo, monospace;
```

**Fraunces** is the signature — use weight 500 (not 700), tight letter-spacing (-0.025 to -0.035em), and lean on the italics. **Inter** handles body copy at 15–16px with 1.55 line-height. **JetBrains Mono** at 10–13px, UPPERCASE for labels, letter-spacing +0.12 to +0.18em.

**Acceptable display swaps** if Fraunces is wrong for the project:
- More editorial: `Tiempos`, `Source Serif Pro`
- More architectural: `PP Editorial New`, `Domaine Display`
- More archival: `EB Garamond`, `Cormorant Garamond`

**Never use** for display: Inter, Roboto, Arial, Poppins, Montserrat, Space Grotesk, Plus Jakarta Sans, or any other AI-default font.

## Layout patterns

**Sections** are tall (96px vertical padding on desktop), separated by 1px top borders. Each opens with a mono-set meta-row:

```html
<div class="meta-row">
  <span>// 02 — Typography</span>
  <span>3 FAMILIES</span>
</div>
<h2 class="sec-title">A serif for <em>voice.</em> A mono for <em>truth.</em></h2>
```

**Cards** sit on `--bg-alt` with hairline borders. Featured cards get accent corner ticks via `::before` (top-left) and `::after` (bottom-right) pseudo-elements. Index number sits absolute top-right in mono.

**Terminal blocks** use mono on `--bg-alt` with a status header (red dot · READY · filename right-aligned in mono caps).

**Grids** prefer asymmetric column splits (e.g., 200px label column + flexible content column for spec sheets) over symmetric grids. Generous gap (24–40px).

## Motion

Keep motion **restrained**. The aesthetic is paper, and paper doesn't bounce. Use:
- 160–200ms ease transitions on hover (color shifts, border color, text underline)
- Subtle reveal on scroll for hero sections only (10–15px translate, 400ms)
- No parallax, no large-scale movement, no autoplay video

## Don'ts (hard rules)

- ❌ Pure white (`#FFF`) backgrounds
- ❌ Pure black (`#000`) text
- ❌ Drop shadows of any kind (`box-shadow` reserved for the rare modal)
- ❌ Rounded corners over 4px
- ❌ Gradient fills (linear or radial, except the dot-grid texture)
- ❌ Multiple saturated colors
- ❌ Emoji as functional UI elements (decorative use sparingly OK)
- ❌ Inter as a display font
- ❌ Bold weight as primary emphasis (use italic + accent color)
- ❌ Centered body copy in long-form sections
- ❌ Hero sections with stock-photo backgrounds or AI-generated imagery

## Workflow when generating a design

1. **Read the request and identify the form** — landing page? dashboard? component? Adapt the principles to the form; don't force every design to look like the this example.
2. **Pick the accent mood** — rust by default. Only swap if the project context strongly suggests otherwise (e.g., a healthcare tool might lean moss or sea).
3. **Confirm the type stack** — Fraunces by default unless a serif swap is more appropriate.
4. **Sketch the section structure with mono meta-rows and numbered indices** — this is what makes the work feel like Atharva's, not generic.
5. **Build with the six commitments as a checklist** — before finishing, verify each one is honored.
6. **Reference `examples/this-style-example.html`** for proportions, spacing rhythm, component patterns, and detail-handling — but don't lift content or structure wholesale. It's an example, not a template.

## Bundled references

- **`references/tokens.md`** — Copy-paste CSS variables, Google Fonts import line, and accent mood swap table. Read this first when starting a new project.
- **`references/components.md`** — Copy-paste HTML+CSS snippets for the signature components (meta-row, schematic card, terminal block, button pair, spec-sheet grid, mono labels). Read when you need to drop in any of these.
- **`examples/this-style-example.html`** — Full executed example of the aesthetic. Use as a calibration artifact: when in doubt about spacing, type sizes, corner-tick proportions, or how patterns fit together, open it and look. **Do not copy its content** (it's about a fictional filesystem product). **Do borrow** its proportions, CSS variable structure, and component patterns.

## A note on adapting to context

This skill encodes a strong aesthetic point of view. That's the point. But Atharva works across many domains — financial tooling, AI infrastructure, developer tools, internal dashboards — and the design should always feel **appropriate** to the subject, not pasted on. A portfolio diagnostics dashboard for institutional clients should feel more reserved and data-dense; a developer-tool landing page can lean more playful in its mono-typography choices. The six commitments hold; the expression flexes.
