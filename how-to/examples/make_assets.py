#!/usr/bin/env python3
"""Generate illustrative 'screenshot' images for the how-to skill's own example
guide. Run once to (re)create examples/assets/*.png, then build the PDF via
examples/guide.json. These are mock UI panels, not real captures."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")
os.makedirs(OUT, exist_ok=True)

FB = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FR = '/System/Library/Fonts/Supplemental/Arial.ttf'
FM = '/System/Library/Fonts/SFNSMono.ttf'
def fb(s): return ImageFont.truetype(FB, s)
def fr(s): return ImageFont.truetype(FR, s)
def fm(s): return ImageFont.truetype(FM, s)

W, H = 1440, 760
LIGHT = (245, 247, 250)
ACCENT = (99, 91, 222)

def card(dr, box, fill, radius=18, outline=None):
    dr.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)

def dots(dr, x, y):
    for i, c in enumerate([(237,106,94), (245,191,79), (98,197,84)]):
        dr.ellipse((x+i*26, y, x+i*26+16, y+16), fill=c)

# ---- step 1: gather your screenshots (file list) ----------------------------
def step1():
    im = Image.new('RGB', (W, H), LIGHT); dr = ImageDraw.Draw(im)
    card(dr, (50, 46, W-50, H-46), (255,255,255), outline=(228,232,238))
    dr.text((86, 80), "my-screenshots", font=fb(38), fill=(28,32,46))
    dr.text((88, 132), "Drop your captures in one folder — they render in filename order.",
            font=fr(26), fill=(120,128,140))
    rows = [("01-open-app.png", "1.2 MB"), ("02-search.png", "980 KB"),
            ("03-results.png", "1.1 MB"), ("04-detail.png", "1.0 MB")]
    y = 210
    for name, size in rows:
        card(dr, (86, y, W-86, y+96), (250,251,253), radius=14, outline=(232,236,242))
        # thumbnail square
        card(dr, (104, y+18, 104+96, y+78), (224,228,236), radius=10)
        dr.line((120, y+58, 152, y+38), fill=(150,156,168), width=4)
        dr.ellipse((150, y+30, 168, y+48), outline=(150,156,168), width=4)
        dr.text((228, y+28), name, font=fb(30), fill=(34,39,54))
        dr.text((W-220, y+32), size, font=fr(26), fill=(140,148,160))
        y += 116
    im.save(os.path.join(OUT, "step1.png"))

# ---- step 2: write guide.json (code editor) ---------------------------------
def step2():
    im = Image.new('RGB', (W, H), LIGHT); dr = ImageDraw.Draw(im)
    card(dr, (50, 46, W-50, H-46), (30,33,44))
    card(dr, (50, 46, W-50, 100), (40,43,56), radius=18)
    dr.rectangle((50, 82, W-50, 100), fill=(40,43,56))
    dots(dr, 80, 65)
    dr.text((W/2, 73), "guide.json", font=fm(26), fill=(180,186,198), anchor="mm")
    KEY=(130,170,255); STR=(126,206,138); PUN=(150,156,170); NUM=(230,180,120)
    lines = [
        [("{", PUN)],
        [('  "title"', KEY), (": ", PUN), ('"My Product — Quick Start"', STR), (",", PUN)],
        [('  "intro"', KEY), (": ", PUN), ('"A two-line walkthrough of the basics."', STR), (",", PUN)],
        [('  "eyebrow"', KEY), (": ", PUN), ('"MY PRODUCT  ·  GUIDE"', STR), (",", PUN)],
        [('  "footer"', KEY), (": ", PUN), ('"ACME  ·  How-to"', STR), (",", PUN)],
        [('  "output"', KEY), (": ", PUN), ('"My Guide.pdf"', STR), (",", PUN)],
        [('  "slides"', KEY), (": [", PUN)],
        [('    { ', PUN), ('"image"', KEY), (": ", PUN), ('"step1.png"', STR), (" },", PUN)],
        [('    { ', PUN), ('"image"', KEY), (": ", PUN), ('"step2.png"', STR), (",", PUN)],
        [('        ', PUN), ('"header"', KEY), (": { ", PUN), ('"number"', KEY), (": ", PUN),
         ("4", NUM), (", ", PUN), ('"label"', KEY), (": ", PUN), ('"Verify"', STR), (" } }", PUN)],
        [('  ]', PUN)],
        [("}", PUN)],
    ]
    y = 130; mono = fm(28)
    for parts in lines:
        x = 90
        for txt, col in parts:
            dr.text((x, y), txt, font=mono, fill=col)
            x += dr.textlength(txt, font=mono)
        y += 46
    im.save(os.path.join(OUT, "step2.png"))

# ---- step 3: run the build script (terminal) --------------------------------
def step3():
    im = Image.new('RGB', (W, H), LIGHT); dr = ImageDraw.Draw(im)
    card(dr, (50, 46, W-50, H-46), (15,17,23))
    card(dr, (50, 46, W-50, 100), (28,30,40), radius=18)
    dr.rectangle((50, 82, W-50, 100), fill=(28,30,40))
    dots(dr, 80, 65)
    dr.text((W/2, 73), "bash — how-to", font=fm(26), fill=(150,156,168), anchor="mm")
    mono = fm(28)
    def line(y, segs):
        x = 90
        for txt, col in segs:
            dr.text((x, y), txt, font=mono, fill=col)
            x += dr.textlength(txt, font=mono)
    G=(120,210,140); W2=(225,228,235); D=(120,128,145); P=(120,170,255)
    line(150, [("$ ", G), ("python3 ~/.claude/skills/how-to/scripts/build_guide_pdf.py \\", W2)])
    line(196, [("      --config ", W2), ("guide.json", P)])
    line(266, [("saved /Users/you/My Guide.pdf  ", W2), ("(5 pages)", G)])
    line(336, [("$ ", G), ("open \"My Guide.pdf\"", W2)])
    dr.text((90, 430), "Tip: no config? quick mode takes a folder:", font=fr(24), fill=(150,156,168))
    line(478, [("$ ", G), ("...build_guide_pdf.py --images ./shots --output g.pdf \\", W2)])
    line(524, [('      --title "My Guide" --intro "..."', W2)])
    im.save(os.path.join(OUT, "step3.png"))

# ---- step 4: verify the output (two page mockups) ---------------------------
def step4():
    im = Image.new('RGB', (W, H), LIGHT); dr = ImageDraw.Draw(im)
    dr.text((W/2, 90), "Open the PDF and check the layout", font=fb(36), fill=(28,32,46), anchor="mm")
    def page(px, label, cover=False):
        pw, ph = 470, 360
        # page bg
        card(dr, (px, 170, px+pw, 170+ph), (236,239,243), radius=16, outline=(225,229,236))
        # card with shadow feel
        cx0, cy0, cx1, cy1 = px+26, 196, px+pw-26, 170+ph-50
        card(dr, (cx0, cy0, cx1, cy1), (255,255,255), radius=12, outline=(228,232,238))
        if cover:
            dr.text((cx0+30, cy0+70), "MY PRODUCT  ·  GUIDE", font=fb(16), fill=ACCENT)
            dr.rectangle((cx0+30, cy0+96, cx0+90, cy0+100), fill=ACCENT)
            dr.text((cx0+30, cy0+116), "My Product —", font=fb(34), fill=(28,32,46))
            dr.text((cx0+30, cy0+154), "Quick Start", font=fb(34), fill=(28,32,46))
            dr.text((cx0+30, cy0+210), "A two-line walkthrough", font=fr(20), fill=(120,128,140))
        else:
            # numbered header band
            card(dr, (cx0+16, cy0+16, cx1-16, cy0+56), (242,245,249), radius=10)
            dr.ellipse((cx0+26, cy0+22, cx0+62, cy0+50), fill=(255,255,255))
            dr.text((cx0+44, cy0+36), "1", font=fb(22), fill=(20,24,38), anchor="mm")
            dr.text((cx0+78, cy0+36), "Open the app", font=fb(20), fill=(28,32,46), anchor="lm")
            # image area
            card(dr, (cx0+16, cy0+70, cx1-16, cy1-20), (235,238,243), radius=8)
        # footer line
        dr.text((cx0, 170+ph-34), "ACME  ·  How-to", font=fr(16), fill=(140,148,160))
        dr.text((cx1, 170+ph-34), label, font=fr(16), fill=(140,148,160), anchor="rm")
        # green check
        gx, gy = px+pw-20, 156
        dr.ellipse((gx-22, gy-2, gx+10, gy+30), fill=(98,197,84))
        dr.line((gx-14, gy+14, gx-6, gy+22), fill=(255,255,255), width=4)
        dr.line((gx-6, gy+22, gx+4, gy+6), fill=(255,255,255), width=4)
    page(120, "1 / 5", cover=True)
    page(W-120-470, "2 / 5", cover=False)
    dr.text((W/2, 600), "Re-run after edits — same style, every time.", font=fr(26),
            fill=(120,128,140), anchor="mm")
    im.save(os.path.join(OUT, "step4.png"))

for f in (step1, step2, step3, step4):
    f()
print("assets written to", OUT)
