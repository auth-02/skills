# My Skills — field guide

> *a field guide — what each one does, and when it fires.*

A one-page-per-skill PDF for the seven skills in this repo. Not a skill itself —
the meta-artifact that documents the rest.

```
field-guide/
├── My Skills.pdf            ← the deliverable (open this)
├── My Skills.slides.json    ← content · source of truth, edit this
└── My Skills.guide.json     ← assembler · lists the rendered pages
```

## Regenerate

Built with the **how-to** skill (Flow 2 — content → slides), rendered in the
**kagaz** aesthetic. Two steps: render the slides, then bind them.

```bash
python3 ~/.claude/skills/how-to/scripts/render_slides.py  --config "field-guide/My Skills.slides.json"
python3 ~/.claude/skills/how-to/scripts/build_guide_pdf.py --config "field-guide/My Skills.guide.json"
```

## Add a skill

1. Add a slide object to `My Skills.slides.json` + an `index` entry on the cover.
2. Bump every `counter` (`SKILL n / N`) and the cover count.
3. Add the new `slideN.png` to `My Skills.guide.json`.
4. Regenerate, then eyeball a page or two.

---

*One accent. Paper, not screen. Rendered in [kagaz](../kagaz).*
