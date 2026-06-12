#!/usr/bin/env python3
"""
build_guide_pdf.py — turn a sequence of screenshots into a polished, uniform
"how-to guide" PDF.

Style:
  * Typeset cover page  : indigo eyebrow + accent rule, big bold title, gray intro.
  * Every content page  : soft gray background, centered WHITE rounded card with a
                          subtle drop shadow + 1px border, image fit inside with padding.
  * Footer on every page: left = caption, right = slide number "x / N".
  * Optional per-slide  : a numbered header band ("8  Review your result") added on top
                          of slides that don't already have one.
  * Optional cleanup    : patch out unwanted UI (logos, zoom controls) with a solid
                          fill OR by copying a clean vertical column (gradient-safe).

USAGE
  Config-driven (full control):
      python3 build_guide_pdf.py --config guide.json

  Quick mode (a folder/glob of images, sorted by name):
      python3 build_guide_pdf.py --images "/path/to/folder" \
          --output out.pdf --title "My Guide" \
          --intro "One or two sentences describing the guide." \
          --footer "ACME · How-to"

CONFIG SCHEMA (guide.json)
{
  "output": "My Guide.pdf",
  "title":  "How to Export a Report",
  "intro":  "Learn how to ...",            // omit title+intro to skip the cover page
  "eyebrow": "MY PRODUCT  ·  GUIDE",        // optional; shown above the title
  "footer": "ACME  ·  How-to",              // string = caption+counter;
                                                        // "" = counter only; false = no footer band

  "page":   {"width": 1754, "height": 1240},  // optional; default A4 landscape @150dpi
  "slides": [
    {"image": "step1.png"},
    {"image": "step2.png",
       "patches": [
         {"box": [1274,40,1474,120], "sample_column": 1258},   // gradient-safe cover-up
         {"box": [1288,610,1384,786], "fill": [243,245,248]}    // solid fill cover-up
       ]
    },
    {"image": "result.png",
       "header": {"number": 8, "label": "Review your Client Diagnostics result"}
    }
  ]
}
Notes
  * Slides render in the order listed (or filename order in quick mode).
  * "patches" run before the optional "header" band is added.
  * "sample_column": copies that source x-column over the box rows — use when the
    area has a vertical gradient so a solid fill would leave a visible seam.
"""
import argparse, glob, json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---- palette (the look we settled on) ---------------------------------------
BG     = (236, 239, 243)
CARD   = (255, 255, 255)
BORDER = (226, 230, 236)
FOOT   = (120, 128, 140)
STRIP  = (242, 245, 249)   # header band bg
ACCENT = (99, 91, 222)     # indigo eyebrow / rule
TITLE_C= (22, 27, 42)
INTRO_C= (92, 101, 118)

DEF_W, DEF_H = 1754, 1240  # A4 landscape @ ~150dpi
MARGIN = 58
PAD    = 40                # image padding inside the card

BOLD_FONTS = [
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    '/Library/Fonts/Arial Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
]
REG_FONTS = [
    '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/Library/Fonts/Arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
]

def _font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fb(size): return _font(BOLD_FONTS, size)
def fr(size): return _font(REG_FONTS, size)


def rounded_mask(size, rad):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius=rad, fill=255)
    return m


def wrap(text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Builder:
    def __init__(self, PW, PH, footer_text, total, show_footer=True):
        self.PW, self.PH = PW, PH
        self.footer_text = footer_text
        self.total = total
        self.show_footer = show_footer
        # When the footer is hidden, let the card use the full bottom margin too.
        bottom = (PH - 78) if show_footer else (PH - MARGIN)
        self.card = (MARGIN, MARGIN, PW - MARGIN, bottom)
        self.ffoot = fr(26)

    def _base(self):
        page = Image.new('RGB', (self.PW, self.PH), BG)
        x0, y0, x1, y1 = self.card
        cw, ch = x1 - x0, y1 - y0
        rad = 26
        sh = Image.new('RGBA', (self.PW, self.PH), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0+10, x1, y1+14), radius=rad, fill=(60, 70, 90, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        page = Image.alpha_composite(page.convert('RGBA'), sh).convert('RGB')
        card = Image.new('RGB', (cw, ch), CARD)
        page.paste(card, (x0, y0), rounded_mask((cw, ch), rad))
        return page, cw, ch

    def _footer(self, page, idx):
        if not self.show_footer:
            return
        dr = ImageDraw.Draw(page)
        if self.footer_text:
            dr.text((MARGIN+4, self.PH-56), self.footer_text, font=self.ffoot, fill=FOOT, anchor="lm")
        dr.text((self.PW-MARGIN-4, self.PH-56), f"{idx} / {self.total}", font=self.ffoot, fill=FOOT, anchor="rm")

    def cover(self, idx, title, intro, eyebrow):
        page, cw, ch = self._base()
        dr = ImageDraw.Draw(page)
        Lx = self.card[0] + 110
        maxw = cw - 220
        fEy, fT, fI = fb(30), fb(70), fr(34)
        tlines = wrap(title, fT, maxw) if title else []
        ilines = wrap(intro, fI, maxw) if intro else []
        tlh, ilh, eh, gap1, gap2 = 84, 50, 40, 34, 46
        block = (eh + gap1 if eyebrow else 0) + len(tlines)*tlh + (gap2 if ilines else 0) + len(ilines)*ilh
        y = self.card[1] + (ch - block)//2
        top = y
        if eyebrow:
            dr.text((Lx, y), eyebrow, font=fEy, fill=ACCENT)
            dr.rectangle((Lx, y+eh+6, Lx+70, y+eh+10), fill=ACCENT)
            y += eh + gap1
        for ln in tlines:
            dr.text((Lx, y), ln, font=fT, fill=TITLE_C); y += tlh
        if ilines:
            y += gap2 - tlh + tlh  # noop spacer kept explicit
        for ln in ilines:
            dr.text((Lx, y), ln, font=fI, fill=INTRO_C); y += ilh
        self._footer(page, idx)
        return page

    def content(self, idx, img):
        page, cw, ch = self._base()
        iw, ih = cw - 2*PAD, ch - 2*PAD
        im = img.copy(); im.thumbnail((iw, ih), Image.LANCZOS)
        ox = self.card[0] + (cw - im.size[0])//2
        oy = self.card[1] + (ch - im.size[1])//2
        page.paste(im, (ox, oy))
        ImageDraw.Draw(page).rectangle((ox-1, oy-1, ox+im.size[0], oy+im.size[1]), outline=BORDER, width=1)
        self._footer(page, idx)
        return page


def resolve_path(path, base_dir):
    """Find an image even when the path uses a different space character than the
    file on disk (macOS screenshots use a narrow no-break space U+202F before AM/PM)."""
    if not os.path.isabs(path):
        path = os.path.join(base_dir, path)
    if os.path.exists(path):
        return path
    d, name = os.path.dirname(path), os.path.basename(path)
    def norm(s):
        for ch in (" ", " ", " "):
            s = s.replace(ch, " ")
        return s
    target = norm(name)
    try:
        for cand in os.listdir(d or "."):
            if norm(cand) == target:
                return os.path.join(d, cand)
    except FileNotFoundError:
        pass
    return path  # let the caller raise a clear error


def apply_patches(im, patches):
    for p in patches:
        x0, y0, x1, y1 = p["box"]
        if "sample_column" in p:
            sx = p["sample_column"]
            col = im.crop((sx, y0, sx+1, y1)).resize((x1-x0, y1-y0))
            im.paste(col, (x0, y0))
        elif "fill" in p:
            ImageDraw.Draw(im).rectangle((x0, y0, x1, y1), fill=tuple(p["fill"]))
    return im


def add_header(im, number, label):
    W = im.size[0]
    bandH = 132
    band = Image.new('RGB', (W, bandH), (255, 255, 255))
    bd = ImageDraw.Draw(band)
    bd.rounded_rectangle((24, 18, W-24, 102), radius=16, fill=STRIP)
    cx, cy, r = 72, 60, 30
    bd.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(255, 255, 255))
    bd.text((cx, cy), str(number), font=fb(40), fill=(20, 24, 38), anchor="mm")
    if label:
        bd.text((cx+r+26, cy), label, font=fb(38), fill=(28, 32, 46), anchor="lm")
    out = Image.new('RGB', (W, bandH + im.size[1]), (255, 255, 255))
    out.paste(band, (0, 0)); out.paste(im, (0, bandH))
    return out


def build(cfg, base_dir):
    PW = cfg.get("page", {}).get("width", DEF_W)
    PH = cfg.get("page", {}).get("height", DEF_H)
    title  = cfg.get("title")
    intro  = cfg.get("intro")
    eyebrow= cfg.get("eyebrow")
    footer = cfg.get("footer", "")
    # footer: false  -> no footer band at all (no caption, no "x / N" counter).
    # footer: "text" -> caption left + counter right.  footer omitted/"" -> counter only.
    show_footer = footer is not False
    footer_text = footer if isinstance(footer, str) else ""
    slides = cfg["slides"]
    has_cover = bool(title or intro)
    total = len(slides) + (1 if has_cover else 0)

    b = Builder(PW, PH, footer_text, total, show_footer)
    pages = []
    idx = 1
    if has_cover:
        pages.append(b.cover(idx, title or "", intro or "", eyebrow)); idx += 1

    for s in slides:
        path = resolve_path(s["image"], base_dir)
        im = Image.open(path).convert('RGB')
        if s.get("crop"):
            im = im.crop(tuple(s["crop"]))
        if s.get("patches"):
            im = apply_patches(im, s["patches"])
        if s.get("header"):
            h = s["header"]
            im = add_header(im, h.get("number", ""), h.get("label", ""))
        pages.append(b.content(idx, im)); idx += 1

    out = cfg["output"]
    if not os.path.isabs(out):
        out = os.path.join(base_dir, out)
    pages[0].save(out, 'PDF', resolution=150.0, save_all=True, append_images=pages[1:])
    return out, len(pages)


def collect_images(spec):
    if os.path.isdir(spec):
        files = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG"):
            files += glob.glob(os.path.join(spec, ext))
        return sorted(files)
    return sorted(glob.glob(spec))


def main():
    ap = argparse.ArgumentParser(description="Build a styled how-to guide PDF from images.")
    ap.add_argument("--config", help="Path to a guide.json config (full control).")
    ap.add_argument("--images", help="Folder or glob of images (quick mode).")
    ap.add_argument("--output", help="Output PDF path (quick mode).")
    ap.add_argument("--title", default="")
    ap.add_argument("--intro", default="")
    ap.add_argument("--eyebrow", default="")
    ap.add_argument("--footer", default="")
    args = ap.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        base = os.path.dirname(os.path.abspath(args.config))
        out, n = build(cfg, base)
    else:
        if not args.images or not args.output:
            ap.error("quick mode needs --images and --output (or use --config)")
        imgs = collect_images(args.images)
        if not imgs:
            ap.error(f"no images found at {args.images}")
        cfg = {
            "output": args.output,
            "title": args.title, "intro": args.intro,
            "eyebrow": args.eyebrow, "footer": args.footer,
            "slides": [{"image": p} for p in imgs],
        }
        out, n = build(cfg, os.getcwd())

    print(f"saved {out}  ({n} pages)")


if __name__ == "__main__":
    main()
