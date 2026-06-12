---
name: how-to
description: >-
  Turn a sequence of screenshots/images into a polished, presentable "how-to
  guide" PDF. Produces a typeset cover page (eyebrow + title + intro), places
  every image on a uniform white rounded card with a soft drop shadow and 1px
  border on a light gray background, and adds a footer with a slide counter
  (x / N). Can also add numbered step headers ("8  Review your result") to
  slides that lack one, and patch out unwanted UI (logos, zoom controls) either
  with a solid fill or by copying a clean column (gradient-safe). Use whenever
  the user wants to convert screenshots/images into a styled walkthrough,
  tutorial, onboarding, or guide PDF. Also use when the user wants a guide PDF
  of content with NO screenshots to start from (documenting skills, an API, a
  concept) — render each slide as styled HTML → PNG (optionally in the design
  skill's aesthetic), then assemble those into the PDF.
---

# how-to — styled guide PDF

Build a clean, consistent walkthrough PDF. Every page is the same size with a
shadowed white card, a 1px border around the image, and an optional footer slide
counter. Page 1 is an optional typeset cover.

This skill has **two flows**. Decide which applies, then **read that flow's
reference file in full and follow it** — the detailed steps, the script, and the
JSON config schema all live there. Don't work from this page alone.

## Pick the flow

| If… | Flow | Then read | Driver script |
|-----|------|-----------|---------------|
| The user **gave you images** (screenshots, exported diagrams) | **1 — assemble** | **`references/flow-images.md`** | `scripts/build_guide_pdf.py` |
| The user wants a guide but there are **no images** (skills, an API, a concept, a checklist) | **2 — generate, then assemble** | **`references/flow-content.md`** | `scripts/render_slides.py` → `scripts/build_guide_pdf.py` |

Flow 2 first **generates** styled slides from content (HTML → PNG via headless
Chrome, in the `design` aesthetic by default), then hands those PNGs to Flow 1's
assembler. So Flow 2 uses *both* reference files; start with `flow-content.md`.

## Before you start (both flows)

- **Dependencies.** Assembling needs Pillow (`python3 -c "import PIL"`; if missing,
  `pip install Pillow`). Generating (Flow 2) also needs headless Chrome — present
  on macOS at `/Applications/Google Chrome.app`.
- **Scratch space.** Working files (configs, HTML, PNGs) live fine in a temp dir
  like `/tmp/<name>-guide/`; only the final PDF needs a real home.
- **Always verify.** After building, render a page or two of the PDF to thumbnails
  and Read them — confirm the cover, layout, any patches/headers, and (Flow 2) that
  fonts loaded. Adjust the config and re-run if needed.
- **Examples.** `references/guide.json` (assembler) and `references/slides.json`
  (generator) are complete, real configs to copy from.
