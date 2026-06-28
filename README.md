# skills

A collection of skills, mirrored to `~/skills` and version-controlled. Each is
invoked automatically when its trigger appears, or on request by name. Ordered as
a project flows — **plan, build, run, design, then share, document, and illustrate.**

| # | Skill | Does | When it fires |
|---|-------|------|---------------|
| 01 | [manifest](manifest/SKILL.md) | Plan before code; a living task doc. | Start of any 3+ step feature, migration, or refactor. |
| 02 | [stacked](stacked/SKILL.md) | Decompose into reviewable layers. | Build/refactor work spanning multiple layers. |
| 03 | [cmux](cmux/SKILL.md) | Drive terminals & the browser by CLI. | Any mention of cmux — panes, terminals, browser automation. |
| 04 | [kagaz](kagaz/SKILL.md) | Editorial-technical design + PDF system. | Any UI, page, report, or PDF — the house aesthetic. |
| 05 | [dak](dak/SKILL.md) | Local artifact → shareable URL. | "Send me a link", "publish this", "host this". |
| 06 | [how-to](how-to/SKILL.md) | Styled walkthrough guide PDFs. | Turning screenshots or content into a guide. |
| 07 | [ian-illustrations](ian-illustrations/SKILL.md) | Xiaohei hand-drawn article art. | Generating illustrations from article content. |

## The guide

A typeset, one-page-per-skill PDF lives in [`colophon/`](colophon/COLOPHON.md) — the
visual companion to this table, built with **how-to** and rendered in **kagaz**. See
its [colophon](colophon/COLOPHON.md) to regenerate or extend it.

## Layout

```
skills/
├── <skill>/            # SKILL.md + references/ scripts/ examples/
└── colophon/           # My Skills.pdf — the guide + how it's made
```

Each skill folder carries a `SKILL.md` (its trigger + instructions) and, as
needed, `references/`, `scripts/`, and `examples/`.
