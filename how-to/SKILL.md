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

## Two flows — pick by whether the user gave you images

1. **Images provided** (screenshots, exported diagrams) → assemble them directly:
   `scripts/build_guide_pdf.py`.
2. **No images** (documenting skills, an API, a concept, a checklist — nothing to
   screenshot) → first **generate** the slides from content with
   `scripts/render_slides.py` (styled HTML → PNG via headless Chrome, in the
   `design` aesthetic by default), then assemble those PNGs with
   `scripts/build_guide_pdf.py` (usually `"footer": false`, since generated slides
   carry their own footer).

Both scripts are Python. `build_guide_pdf.py` needs Pillow
(`python3 -c "import PIL"`; if missing, `pip install Pillow`). `render_slides.py`
needs headless Chrome (present on macOS at `/Applications/Google Chrome.app`).
Example configs: `references/guide.json` (assembler) and
`references/slides.json` (generator).

---

# Flow 1 — images → PDF  (`build_guide_pdf.py`)

## Workflow

1. **Gather the images and their order.** Ask the user for the input folder (or
   list of images). They render in the order given, or filename order for a
   folder. Look at the images (Read them) to understand the content before
   configuring — especially to spot:
   - the **cover text** (a title slide whose text should become the typeset
     cover instead of an image),
   - any **slide that needs a numbered header** added (a result/output slide
     that lacks a step number),
   - any **UI to patch out** (watermarks/logos, zoom controls, cursors).

2. **Decide cover vs. content.** If one screenshot is just a title + intro
   paragraph, don't ship it as an image — extract that text into `title` /
   `intro` so page 1 is crisp typeset text. Otherwise omit `title`/`intro` and
   there will be no cover page.

3. **Write a config** `guide.json` (preferred — full control) and run:
   ```bash
   python3 ~/.claude/skills/how-to/scripts/build_guide_pdf.py --config /abs/path/guide.json
   ```
   Or quick mode for a plain folder with no per-slide tweaks:
   ```bash
   python3 ~/.claude/skills/how-to/scripts/build_guide_pdf.py \
     --images "/abs/path/to/folder" --output "/abs/path/Guide.pdf" \
     --title "My Guide" --intro "One or two sentences." \
     --eyebrow "PRODUCT  ·  BETA" --footer "ACME  ·  How-to"
   ```

4. **Verify.** The script prints `saved <path> (N pages)`. Render a couple of
   pages to thumbnails and Read them to confirm layout, the cover, any added
   headers, and that patches fully covered the target UI. Adjust the config and
   re-run if needed.

## config schema (guide.json)

```json
{
  "output": "My Guide.pdf",
  "title":  "How to Run a TIFIN RM Client Portfolio Diagnostic",
  "intro":  "Learn how to access and initiate a comprehensive diagnostic report ...",
  "eyebrow": "CLIENT DIAGNOSTICS  ·  BETA",
  "footer": "TIFIN RM  ·  Client Diagnostics (Beta)  —  How to run a client portfolio diagnostic",
  "page":   {"width": 1754, "height": 1240},
  "slides": [
    { "image": "step1.png" },
    { "image": "step2.png",
      "patches": [
        { "box": [1274,40,1474,120], "sample_column": 1258 },
        { "box": [1288,610,1384,786], "fill": [243,245,248] }
      ]
    },
    { "image": "result.png",
      "header": { "number": 8, "label": "Review your Client Diagnostics result" }
    }
  ]
}
```

- Paths in the config are relative to the config file's directory.
- **`crop`**: `[x0,y0,x1,y1]` trims the source image before anything else — use it
  to drop a baked-in title region from a slide when that text is becoming the
  typeset cover, or to remove window chrome. `crop` → `patches` → `header`.
- Omit `title`/`intro` to skip the cover page (counter starts at slide 1).
- **`footer`**: a string shows that caption (left) + the `x / N` counter (right) on
  every page; `""` shows the counter only; **`false`** removes the whole footer band
  (no caption, no counter) and lets the card use the full bottom margin. Set it to
  `false` when the slides already carry their own footer/branding.
- `page` is optional; default is A4 landscape at ~150dpi (1754×1240).
- **`patches`** run before the header band. Two kinds:
  - `"fill": [r,g,b]` — solid rectangle. Sample the surrounding background color
    first so it blends.
  - `"sample_column": x` — copies source column `x` across the box rows. Use when
    the area has a **vertical gradient** (a flat fill would leave a seam).
- **`header`** adds a top band matching the in-app step style: a rounded
  `(242,245,249)` strip, a white circle with the bold `number`, and the `label`.
  Use it to make an un-numbered output slide read as the final step.

## No images? Generate the slides from content first

This skill ships images → PDF, but the most common real request is *"make a guide
of X"* with **no screenshots to work from** (documenting skills, an API, a concept,
a checklist). Don't refuse and don't fall back to plain text — **render each slide
yourself, then feed those PNGs to the builder.** The builder still does the cover
framing, card, border, and counter; you just supply the content slides.

Pipeline that works well:

1. **Gather the content.** Read the real source (files, `SKILL.md`s, docs). One
   slide per topic; keep each slide to a lead line + 2 short blocks so it breathes.
2. **Write one HTML file per slide** sized to the page (e.g. `1754×1240`,
   `html,body{width;height;overflow:hidden}`). Style it deliberately — for the
   user's own work, **invoke the `design` skill's aesthetic** (cream paper, one
   rust accent, serif display + mono labels, hairline rules, corner ticks); it
   makes the guide feel authored and doubles as a demo of that skill. A cover
   slide + one slide per topic.
3. **Render each HTML to PNG with headless Chrome** (present on macOS):
   ```bash
   CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
     --force-device-scale-factor=1 --window-size=1754,1240 \
     --screenshot="/abs/slideN.png" "file:///abs/slideN.html"
   ```
   Chrome fetches Google Fonts when online; always set robust local fallbacks
   (e.g. `'Fraunces','Georgia',serif`, `'JetBrains Mono','Menlo',monospace`) so it
   still renders offline. Confirm each PNG is exactly the page size.
4. **Build with `footer: false`** when your slides already carry their own footer —
   otherwise you get a redundant second footer band. Then verify as usual
   (render a page from the PDF and Read it).

Working files (HTML, PNGs, `guide.json`) live fine in a scratch dir like
`/tmp/<name>-guide/`; only the final PDF needs a real home.

## finding patch / header coordinates

Coordinates are pixels in the **original image**. To find them, crop the region
and Read it, or sample colors with Pillow:

```python
from PIL import Image
im = Image.open("result.png").convert("RGB")
print(im.size)
im.crop((1148, 510, 1408, 810)).save("/tmp/corner.png")   # inspect a corner
print(im.getpixel((1255, 55)))                             # sample bg color
```

Pick `fill` from a clean nearby pixel; for `sample_column` pick an x-column that
is blank for the full height of the box.

## notes

- Filenames with unusual whitespace can break literal-path shell commands; use
  globbing (`*.png`) or pass them through the config, which opens them in Python.
- All pages share one size, so mixed image aspect ratios just get centered with
  white space inside the card — that is the intended uniform look.
