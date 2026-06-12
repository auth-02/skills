# Flow 2 — no images → generate, then assemble  (`render_slides.py` → `build_guide_pdf.py`)

Use when the user wants a guide of content with **nothing to screenshot**
(documenting skills, an API, a concept, a checklist). Don't refuse and don't fall
back to plain text — generate the slides, then assemble them. Needs headless
Chrome (macOS: `/Applications/Google Chrome.app`) plus Pillow for the assemble step.

## Workflow

1. **Gather the content.** Read the real source (files, `SKILL.md`s, docs). One
   slide per topic; keep each to a lead line + 2 short blocks so it breathes.

2. **Write a content config** `slides.json` (schema below) and render it:
   ```bash
   python3 ~/.claude/skills/how-to/scripts/render_slides.py --config /abs/slides.json
   ```
   This writes `slide0.png` (cover, if present) + `slide1.png …` to `out_dir`, in
   the `design` skill's aesthetic by default (warm paper, one rust accent, serif
   display + mono labels, hairline rules, corner ticks). Chrome fetches Google
   Fonts when online; the config's defaults include local fallbacks so it still
   renders offline. `--html-only` skips rendering; `--out` overrides `out_dir`.

3. **Assemble** the generated PNGs with `build_guide_pdf.py` (see
   `references/flow-images.md`), using **`"footer": false`** — the generated slides
   already carry their own footer, so the builder's footer would be redundant:
   ```bash
   python3 ~/.claude/skills/how-to/scripts/build_guide_pdf.py --config /abs/guide.json
   ```
   The `guide.json` just lists the generated PNGs as slides. Then verify (render a
   PDF page, Read it).

Working files (HTML, PNGs, configs) live fine in a scratch dir like
`/tmp/<name>-guide/`; only the final PDF needs a real home.

## content config schema (slides.json)

```json
{
  "out_dir": "/tmp/my-guide",
  "page": {"width": 1754, "height": 1240},
  "theme": {"accent": "#C0622A", "bg": "#F4EFE4"},
  "cover": {
    "eyebrow": "CLAUDE CODE  ·  ~/.claude/skills",
    "title": "My Skills",
    "sub": "a field guide — what each one does.",
    "intro": "Short paragraph. Inline <code>tags</code> allowed.",
    "index": [ {"n": "// 01", "t": "manifest", "d": "Plan before code."} ]
  },
  "slides": [
    {
      "tag": "// 01  —  PLANNING",
      "title": "manifest",
      "lead": "write the plan before the code.",
      "counter": "SKILL 1 / 5",
      "blocks": [
        {"label": "What it does", "html": "A living markdown doc ..."},
        {"label": "How to use",   "html": "Fires at the <strong>start</strong> ..."}
      ],
      "foot_left": "~/.claude/skills/manifest",
      "foot_right": "LIVING TASK MANIFEST"
    }
  ]
}
```

- `lead`, `intro`, and block `html` values are **raw HTML** — use `<strong>`,
  `<em>`, `<code>`, `&amp;`, `&ldquo;`, `&nbsp;` etc.
- Omit `cover` to skip the cover slide. `blocks` can be any number of label/value rows.
- `theme` overrides any `:root` CSS var (`accent`, `bg`, `ink`, `serif`, `mono`, …);
  omit it for the default design aesthetic.
- A full real example is `references/slides.json`.
