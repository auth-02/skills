#!/usr/bin/env python3
"""
render_slides.py — generate styled slide PNGs from CONTENT when there are no
screenshots to start from. Companion to build_guide_pdf.py:

    content config (JSON)  --render_slides.py-->  slide PNGs  --build_guide_pdf.py-->  guide PDF

Use this when the user wants a guide of textual/conceptual material (documenting
skills, an API, a checklist, a concept) and provides no images. Each slide is a
deliberately typeset HTML page rendered to a PNG with headless Chrome; the
default look is the "design" skill aesthetic (warm paper, one rust accent,
serif display + mono labels, hairline rules, corner ticks). Then feed the PNGs
to build_guide_pdf.py (usually with "footer": false, since these slides carry
their own footer).

USAGE
    python3 render_slides.py --config slides.json [--out /abs/dir] [--html-only]

    --out        override out_dir from the config (where slideN.html/png land)
    --html-only  write the HTML but skip Chrome rendering (e.g. Chrome absent)

CONFIG SCHEMA (slides.json)
{
  "out_dir": "/tmp/my-guide",                  // where slide files are written
  "page": {"width": 1754, "height": 1240},     // optional; default A4 landscape @150dpi
  "theme": {"accent": "#C0622A", "bg": "#F4EFE4"},  // optional :root var overrides
  "cover": {                                    // optional; becomes slide0
    "eyebrow": "CLAUDE CODE  ·  ~/.claude/skills",
    "title":   "My Skills",
    "sub":     "a field guide — what each one does.",
    "intro":   "Short paragraph. Inline <code>tags</code> allowed.",
    "index":   [ {"n": "// 01", "t": "manifest", "d": "Plan before code."}, ... ]
  },
  "slides": [                                   // one per topic
    {
      "tag":   "PLANNING · PLAN-BEFORE-CODE",   // mono kicker, upper-left
      "title": "manifest",                      // big serif heading
      "lead":  "write the plan before the code.", // rust italic one-liner
      "counter": "SKILL 1 / 5",                 // optional, upper-right
      "blocks": [                               // label/value rows (any number)
        {"label": "What it does", "html": "A living markdown doc ... <code>x</code>."},
        {"label": "How to use",   "html": "Fires at the <strong>start</strong> ..."}
      ],
      "foot_left":  "~/.claude/skills/manifest", // optional footer, lower-left
      "foot_right": "LIVING TASK MANIFEST"       // optional footer, lower-right
    }
  ]
}

Block/lead/intro values are raw HTML — use <strong>, <em>, <code>, &amp;, &ldquo; etc.
Paths are absolute. Render order is: cover (if present), then slides in order.
"""
import argparse, json, os, subprocess, sys

DEF_W, DEF_H = 1754, 1240

DEFAULT_THEME = {
    "bg": "#F4EFE4", "bg-alt": "#ECE5D2", "ink": "#1A1A1A", "ink-soft": "#3A352D",
    "ink-mute": "#8A8377", "line": "#D9D1BC", "accent": "#C0622A", "accent-deep": "#8A4218",
    "serif": "'Fraunces','Georgia','Times New Roman',serif",
    "mono": "'JetBrains Mono','Menlo',monospace",
    "body": "'Inter','Helvetica Neue',sans-serif",
}

FONTS_IMPORT = ("@import url('https://fonts.googleapis.com/css2?"
                "family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600"
                "&family=JetBrains+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap');")


def css(theme, PW, PH, ncols):
    root = "\n".join(f"  --{k}:{v};" for k, v in theme.items())
    return f"""{FONTS_IMPORT}
:root{{
{root}
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{PW}px;height:{PH}px;overflow:hidden;background:var(--bg);color:var(--ink);
  font-family:var(--body);font-size:21px;line-height:1.55;
  background-image:radial-gradient(circle at 1px 1px, rgba(58,53,45,.06) 1px, transparent 0);
  background-size:22px 22px;}}
.page{{position:relative;width:{PW}px;height:{PH}px;padding:96px 110px;}}
.tick{{position:absolute;width:26px;height:26px;border:2px solid var(--accent);}}
.tl{{top:54px;left:60px;border-right:0;border-bottom:0;}}
.br{{bottom:54px;right:60px;border-left:0;border-top:0;}}
.meta{{display:flex;justify-content:space-between;align-items:baseline;
  font-family:var(--mono);font-size:18px;letter-spacing:.16em;color:var(--ink-mute);
  text-transform:uppercase;border-bottom:1px solid var(--line);padding-bottom:20px;}}
.meta .num{{color:var(--accent);}}
h1{{font-family:var(--serif);font-weight:500;font-size:108px;letter-spacing:-.03em;
  margin-top:46px;line-height:1;}}
.lead{{font-family:var(--serif);font-style:italic;font-size:40px;color:var(--accent-deep);
  margin-top:20px;letter-spacing:-.01em;}}
.body{{margin-top:54px;display:grid;grid-template-columns:230px 1fr;gap:30px 40px;}}
.lbl{{font-family:var(--mono);font-size:17px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-mute);padding-top:6px;}}
.val{{font-size:23px;color:var(--ink-soft);line-height:1.62;}}
.val strong{{color:var(--ink);font-weight:500;}}
.val em{{font-style:italic;color:var(--accent-deep);}}
code{{font-family:var(--mono);font-size:.86em;background:var(--bg-alt);
  border:1px solid var(--line);padding:1px 7px;color:var(--accent-deep);}}
.foot{{position:absolute;left:110px;right:110px;bottom:70px;border-top:1px solid var(--line);
  padding-top:18px;font-family:var(--mono);font-size:16px;letter-spacing:.1em;
  color:var(--ink-mute);text-transform:uppercase;display:flex;justify-content:space-between;}}
.cover{{display:flex;flex-direction:column;justify-content:center;height:100%;}}
.cover .eyebrow{{font-family:var(--mono);font-size:20px;letter-spacing:.22em;color:var(--accent);text-transform:uppercase;}}
.cover h1{{font-size:140px;margin-top:30px;}}
.cover .sub{{font-family:var(--serif);font-style:italic;font-size:46px;color:var(--accent-deep);margin-top:14px;}}
.cover .intro{{font-size:26px;color:var(--ink-soft);max-width:1100px;margin-top:46px;line-height:1.6;}}
.cover .index{{margin-top:58px;display:grid;grid-template-columns:repeat({ncols},1fr);gap:24px;}}
.cover .ix{{border-top:2px solid var(--accent);padding-top:14px;}}
.cover .ix .n{{font-family:var(--mono);font-size:15px;color:var(--ink-mute);letter-spacing:.1em;}}
.cover .ix .t{{font-family:var(--serif);font-size:29px;margin-top:6px;}}
.cover .ix .d{{font-size:15px;color:var(--ink-mute);margin-top:6px;line-height:1.45;}}
"""


def doc(style, inner):
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{style}</style></head>'
            f'<body>{inner}</body></html>')


def cover_html(style, c):
    ix = "".join(f'<div class="ix"><div class="n">{i.get("n","")}</div>'
                 f'<div class="t">{i.get("t","")}</div>'
                 f'<div class="d">{i.get("d","")}</div></div>' for i in c.get("index", []))
    parts = ['<div class="page cover"><span class="tick tl"></span><span class="tick br"></span>']
    if c.get("eyebrow"): parts.append(f'<div class="eyebrow">{c["eyebrow"]}</div>')
    if c.get("title"):   parts.append(f'<h1>{c["title"]}</h1>')
    if c.get("sub"):     parts.append(f'<div class="sub">{c["sub"]}</div>')
    if c.get("intro"):   parts.append(f'<div class="intro">{c["intro"]}</div>')
    if ix:               parts.append(f'<div class="index">{ix}</div>')
    parts.append('</div>')
    return doc(style, "".join(parts))


def slide_html(style, s):
    left = s.get("tag", "")
    num = ""
    # auto-number from the counter "SKILL 3 / 5" -> "// 03" if no explicit kicker number
    blocks = "".join(f'<div class="lbl">{b.get("label","")}</div><div class="val">{b.get("html","")}</div>'
                     for b in s.get("blocks", []))
    meta = (f'<div class="meta"><span>{left}</span>'
            f'<span>{s.get("counter","")}</span></div>')
    foot = ""
    if s.get("foot_left") or s.get("foot_right"):
        foot = (f'<div class="foot"><span>{s.get("foot_left","")}</span>'
                f'<span>{s.get("foot_right","")}</span></div>')
    inner = (f'<div class="page"><span class="tick tl"></span><span class="tick br"></span>'
             f'{meta}<h1>{s.get("title","")}</h1>'
             f'<div class="lead">{s.get("lead","")}</div>'
             f'<div class="body">{blocks}</div>{foot}</div>')
    return doc(style, inner)


def find_chrome():
    cands = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    from shutil import which
    return which("google-chrome") or which("chromium") or which("chrome")


def render(chrome, html_path, png_path, PW, PH):
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={PW},{PH}",
                    f"--screenshot={png_path}", f"file://{html_path}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def main():
    ap = argparse.ArgumentParser(description="Render styled slide PNGs from a content config.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", help="override out_dir")
    ap.add_argument("--html-only", action="store_true", help="write HTML but skip PNG rendering")
    a = ap.parse_args()

    with open(a.config) as f:
        cfg = json.load(f)
    out = a.out or cfg.get("out_dir") or os.path.dirname(os.path.abspath(a.config))
    os.makedirs(out, exist_ok=True)
    PW = cfg.get("page", {}).get("width", DEF_W)
    PH = cfg.get("page", {}).get("height", DEF_H)
    theme = {**DEFAULT_THEME, **cfg.get("theme", {})}
    cover = cfg.get("cover")
    ncols = max(1, len(cover.get("index", []))) if cover else 1
    style = css(theme, PW, PH, ncols)

    pages = []
    if cover:
        pages.append(("slide0", cover_html(style, cover)))
    start = 1 if cover else 0
    for i, s in enumerate(cfg.get("slides", [])):
        pages.append((f"slide{start + i}", slide_html(style, s)))

    chrome = None if a.html_only else find_chrome()
    if not a.html_only and not chrome:
        print("WARNING: no headless Chrome found — writing HTML only.", file=sys.stderr)

    pngs = []
    for name, html in pages:
        hp = os.path.join(out, name + ".html")
        with open(hp, "w") as f:
            f.write(html)
        if chrome:
            pp = os.path.join(out, name + ".png")
            render(chrome, hp, pp, PW, PH)
            pngs.append(pp)

    print(f"wrote {len(pages)} HTML slides to {out}")
    if pngs:
        print(f"rendered {len(pngs)} PNGs:")
        for p in pngs:
            print("  " + p)
        print("\nNext: assemble with build_guide_pdf.py (a guide.json listing these "
              "PNGs, usually \"footer\": false).")


if __name__ == "__main__":
    main()
