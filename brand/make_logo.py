"""Troi of Silo One: the logo, drawn as geometry and set in Sora (SIL OFL 1.1), written as self-contained SVG.

The mark: a silo capsule (Silo One) with one orbit around it (the One), passing behind the capsule and in front of it,
and one satellite riding the orbit (Troi, the presence that stays in orbit around you). In the wordmark the O of TROI
is that orbit and its satellite."""
import math
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ---- palette
INK = "#0B1020"            # text on light
SNOW = "#F4F6FF"           # text on dark
SUB_DARK = "#97A3D6"       # the tagline on dark
SUB_LIGHT = "#4B5680"      # the tagline on light
# each theme keeps every colour at 3:1 or better against its ground (on dark: #05070F; on light: white)
PAL = {"dark": {"silo": [("0", "#D6DCFF"), ("0.45", "#8C95F7"), ("1", "#6457F2")],      # capsule, top to bottom
                "gold": [("0", "#FFE19A"), ("0.5", "#F4AE45"), ("1", "#D9761C")],      # orbit, left to right
                "sat": "#FFF4DA"},
       "light": {"silo": [("0", "#7C84F2"), ("0.45", "#5B5CEB"), ("1", "#3527B8")],
                 "gold": [("0", "#C98016"), ("0.5", "#B0641A"), ("1", "#8E450B")],
                 "sat": "#BF7418"}}


# ---- the mark, in a 256 x 256 box
def mark(uid, mode="color", heavy=False, theme="dark"):
    """SVG for the mark (no outer <svg>). mode: color | white | ink. heavy: thicker strokes for small sizes.
    theme: the ground it sits on (dark or light), which picks the palette."""
    SILO, GOLD, SAT = PAL[theme]["silo"], PAL[theme]["gold"], PAL[theme]["sat"]
    cx, cy = 128.0, 128.0
    cap_w, cap_h = (72.0, 188.0) if heavy else (68.0, 188.0)
    x0, y0 = cx - cap_w / 2, cy - cap_h / 2
    rx, ry, rot = (108.0, 32.0, -14.0)
    sw = 19.0 if heavy else 12.0                       # orbit stroke
    gap = 8.0 if heavy else 6.5                         # the air between the orbit and what it passes
    sat_r = 17.0 if heavy else 11.5
    t = math.radians(34.0)                              # where the satellite rides, on the near arc, right side
    ex, ey = rx * math.cos(t), ry * math.sin(t)
    a = math.radians(rot)
    sx, sy = cx + ex * math.cos(a) - ey * math.sin(a), cy + ex * math.sin(a) + ey * math.cos(a)

    if mode == "color":
        silo_fill, orbit_stroke, sat_fill = f"url(#{uid}-silo)", f"url(#{uid}-gold)", SAT
    else:
        c = "#FFFFFF" if mode == "white" else INK
        silo_fill = orbit_stroke = sat_fill = c

    # the orbit as two half-ellipses in its own frame: the far arc (upper, y<0) and the near arc (lower, y>0)
    far = f"M {cx - rx} {cy} A {rx} {ry} 0 0 1 {cx + rx} {cy}"
    near = f"M {cx + rx} {cy} A {rx} {ry} 0 0 1 {cx - rx} {cy}"
    tr = f"rotate({rot} {cx} {cy})"
    defs = []
    if mode == "color":
        defs.append(f'<linearGradient id="{uid}-silo" x1="0" y1="{y0}" x2="0" y2="{y0 + cap_h}" gradientUnits="userSpaceOnUse">'
                    + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in SILO) + "</linearGradient>")
        defs.append(f'<linearGradient id="{uid}-gold" x1="{cx - rx}" y1="0" x2="{cx + rx}" y2="0" gradientUnits="userSpaceOnUse">'
                    + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in GOLD) + "</linearGradient>")
        defs.append(f'<radialGradient id="{uid}-glow" cx="{sx}" cy="{sy}" r="{sat_r * 2.6}" gradientUnits="userSpaceOnUse">'
                    f'<stop offset="0" stop-color="#FFE7A8" stop-opacity="0.55"/><stop offset="1" stop-color="#FFE7A8" stop-opacity="0"/></radialGradient>')
    # the capsule loses a band where the near arc crosses in front of it; the orbit loses a ring around the satellite
    defs.append(f'<mask id="{uid}-cut" maskUnits="userSpaceOnUse" x="-64" y="-64" width="384" height="384">'
                f'<rect x="-64" y="-64" width="384" height="384" fill="#fff"/>'
                f'<path d="{near}" transform="{tr}" fill="none" stroke="#000" stroke-width="{sw + 2 * gap}" stroke-linecap="round"/></mask>')
    defs.append(f'<mask id="{uid}-sat" maskUnits="userSpaceOnUse" x="-64" y="-64" width="384" height="384">'
                f'<rect x="-64" y="-64" width="384" height="384" fill="#fff"/>'
                f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{sat_r + gap}" fill="#000"/></mask>')
    body = [f'<defs>{"".join(defs)}</defs>',
            f'<g mask="url(#{uid}-sat)"><path d="{far}" transform="{tr}" fill="none" stroke="{orbit_stroke}" stroke-width="{sw}" stroke-linecap="round"/></g>',
            f'<rect x="{x0}" y="{y0}" width="{cap_w}" height="{cap_h}" rx="{cap_w / 2}" fill="{silo_fill}" mask="url(#{uid}-cut)"/>',
            f'<g mask="url(#{uid}-sat)"><path d="{near}" transform="{tr}" fill="none" stroke="{orbit_stroke}" stroke-width="{sw}" stroke-linecap="round"/></g>']
    if mode == "color" and not heavy and theme == "dark":
        body.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{sat_r * 2.6}" fill="url(#{uid}-glow)"/>')
    body.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{sat_r}" fill="{sat_fill}"/>')
    return "".join(body)


# ---- type
def font_at(weight):
    f = TTFont(HERE / "Sora.ttf")
    return instantiateVariableFont(f, {"wght": weight})


class Face:
    def __init__(self, weight):
        self.f = font_at(weight)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.hmtx = self.f["hmtx"]
        self.cap = self.f["OS/2"].sCapHeight

    def glyph(self, ch):
        g = self.cmap[ord(ch)]
        pen = SVGPathPen(self.gs)
        self.gs[g].draw(pen)
        return pen.getCommands(), self.hmtx[g][0]

    def bounds(self, ch):
        from fontTools.pens.boundsPen import BoundsPen
        g = self.cmap[ord(ch)]
        bp = BoundsPen(self.gs)
        self.gs[g].draw(bp)
        return bp.bounds       # xMin, yMin, xMax, yMax


def wordmark(uid, x, baseline, cap_px, fill, mode="color", theme="dark"):
    """TROI with the orbit O. Returns (svg, width_px). x is the left edge of the T's ink."""
    GOLD, SAT = PAL[theme]["gold"], PAL[theme]["sat"]
    face = Face(620)
    s = cap_px / face.cap
    stem = (lambda b: b[2] - b[0])(face.bounds("I"))           # the stem width, in font units
    out, pen_x = [], x
    t_b = face.bounds("T")
    pen_x -= t_b[0] * s                                         # start the T's ink exactly at x
    track = 18                                                  # font units between letters, a little open
    kern = {("T", "R"): -38, ("R", "O"): -6, ("O", "I"): 4}     # optical pairs (font units)
    letters = "TROI"
    ink_right = x
    for i, ch in enumerate(letters):
        if ch == "O":
            # the orbit O: a true circle at the stem's weight, overshooting the cap height a little like a real O
            o_b = face.bounds("O")
            d_font = (o_b[3] - o_b[1])                          # the O's own height (with overshoot)
            r_out = d_font / 2
            r_mid = r_out - stem / 2
            ocx = pen_x + (o_b[0] + r_out) * s
            ocy = baseline - ((o_b[1] + o_b[3]) / 2) * s
            a = math.radians(-38)                               # the satellite, at about two o'clock
            sat_r = stem * 0.62 * s
            sx, sy = ocx + r_mid * s * math.cos(a), ocy + r_mid * s * math.sin(a)
            gap = stem * 0.26 * s
            ring = f'url(#{uid}-wgold)' if mode == "color" else fill
            satc = SAT if mode == "color" else fill
            out.append(f'<defs><mask id="{uid}-wsat" maskUnits="userSpaceOnUse" x="{ocx - 2 * r_out * s}" y="{ocy - 2 * r_out * s}" width="{4 * r_out * s}" height="{4 * r_out * s}">'
                       f'<rect x="{ocx - 2 * r_out * s}" y="{ocy - 2 * r_out * s}" width="{4 * r_out * s}" height="{4 * r_out * s}" fill="#fff"/>'
                       f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{sat_r + gap:.2f}" fill="#000"/></mask>'
                       + (f'<linearGradient id="{uid}-wgold" x1="{ocx - r_out * s}" y1="0" x2="{ocx + r_out * s}" y2="0" gradientUnits="userSpaceOnUse">'
                          + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in GOLD) + "</linearGradient>" if mode == "color" else "")
                       + "</defs>")
            out.append(f'<circle cx="{ocx:.2f}" cy="{ocy:.2f}" r="{r_mid * s:.2f}" fill="none" stroke="{ring}" stroke-width="{stem * s:.2f}" mask="url(#{uid}-wsat)"/>')
            out.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="{sat_r:.2f}" fill="{satc}"/>')
            adv = face.hmtx[face.cmap[ord("O")]][0]
            ink_right = ocx + r_out * s
        else:
            d, adv = face.glyph(ch)
            out.append(f'<path d="{d}" transform="translate({pen_x:.2f} {baseline:.2f}) scale({s:.5f} {-s:.5f})" fill="{fill}"/>')
            b = face.bounds(ch)
            ink_right = pen_x + b[2] * s
        if i < len(letters) - 1:
            pen_x += (adv + track + kern.get((ch, letters[i + 1]), 0)) * s
    return "".join(out), ink_right - x


def tagline(x, baseline, cap_px, fill, width_to=None, text="OF SILO ONE"):
    """Tracked small caps. If width_to is given, the tracking is chosen so the line spans exactly that width."""
    face = Face(520)
    s = cap_px / face.cap
    glyphs = []
    for ch in text:
        if ch == " ":
            glyphs.append((None, face.hmtx[face.cmap[32]][0], None))
        else:
            d, adv = face.glyph(ch)
            glyphs.append((d, adv, face.bounds(ch)))
    first_b, last_b = glyphs[0][2], glyphs[-1][2]
    natural = sum(g[1] for g in glyphs[:-1]) - first_b[0] + last_b[2]      # ink width without tracking, font units
    gaps = len(glyphs) - 1
    track = ((width_to / s - natural) / gaps) if width_to else 0.34 * face.cap
    out, pen_x = [], x - first_b[0] * s
    for d, adv, b in glyphs:
        if d:
            out.append(f'<path d="{d}" transform="translate({pen_x:.2f} {baseline:.2f}) scale({s:.5f} {-s:.5f})" fill="{fill}"/>')
        pen_x += (adv + track) * s
    return "".join(out), (natural + track * gaps) * s


# ---- files
def svg(w, h, inner, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{title}">'
            f"<title>{title}</title>{inner}</svg>\n")


def place(inner, x, y, scale):
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({scale:.5f})">{inner}</g>'


def lockup_horizontal(theme):
    uid = f"h{theme}"
    fill, sub = (SNOW, SUB_DARK) if theme == "dark" else (INK, SUB_LIGHT)
    m = 256.0                                    # the mark at full size
    cap = 104.0
    wx = m + 44.0
    base = 128.0 + cap * 0.30                     # TROI sits a little above the mark's centre, the tagline below
    wm, ww = wordmark(uid, wx, base, cap, fill, theme=theme)
    tl, tw = tagline(wx + 2, base + cap * 0.62, cap * 0.215, sub, width_to=ww - 4)
    return svg(wx + ww + 8, m, mark(uid, theme=theme) + wm + tl, "Troi of Silo One")


def lockup_stacked(theme):
    uid = f"s{theme}"
    fill, sub = (SNOW, SUB_DARK) if theme == "dark" else (INK, SUB_LIGHT)
    cap = 120.0
    wm0, ww = wordmark(uid + "m", 0, 0, cap, fill, theme=theme)      # measure first
    W = max(ww, 256.0) + 80
    m_scale = 1.0
    wx = (W - ww) / 2
    base = 256 + 40 + cap
    wm, _ = wordmark(uid, wx, base, cap, fill, theme=theme)
    tl, tw = tagline(wx + 2, base + cap * 0.62, cap * 0.215, sub, width_to=ww - 4)
    inner = place(mark(uid, theme=theme), (W - 256) / 2, 0, m_scale) + wm + tl
    return svg(W, base + cap * 0.62 + 12, inner, "Troi of Silo One")


def icon(size=1024, heavy=False, uid="i"):
    r = size * 0.2237                               # the macOS icon corner
    stars = [(0.18, 0.2, 1.6, 0.55), (0.82, 0.16, 1.2, 0.45), (0.9, 0.62, 1.4, 0.35), (0.12, 0.74, 1.1, 0.35), (0.7, 0.86, 1.0, 0.3), (0.3, 0.9, 1.3, 0.25)]
    bg = (f'<defs><radialGradient id="{uid}-space" cx="{size * 0.32}" cy="{size * 0.18}" r="{size * 1.05}" gradientUnits="userSpaceOnUse">'
          f'<stop offset="0" stop-color="#27306B"/><stop offset="0.45" stop-color="#0D1233"/><stop offset="1" stop-color="#04050C"/></radialGradient>'
          f'<clipPath id="{uid}-clip"><rect width="{size}" height="{size}" rx="{r}"/></clipPath></defs>'
          f'<g clip-path="url(#{uid}-clip)"><rect width="{size}" height="{size}" fill="url(#{uid}-space)"/>'
          + ("" if heavy else "".join(f'<circle cx="{size * x:.1f}" cy="{size * y:.1f}" r="{size / 1024 * rr * 2:.2f}" fill="#fff" opacity="{o}"/>' for x, y, rr, o in stars))
          + f'<rect width="{size}" height="{size}" rx="{r}" fill="none" stroke="#fff" stroke-opacity="0.07" stroke-width="{size / 512:.2f}"/></g>')
    s = size * (0.74 if heavy else 0.66) / 256
    off = (size - 256 * s) / 2
    return svg(size, size, bg + place(mark(uid + "m", heavy=heavy), off, off, s), "Troi")


files = {
    "mark.svg": svg(256, 256, mark("m"), "Troi"),
    "mark-on-light.svg": svg(256, 256, mark("ml", theme="light"), "Troi"),
    "mark-white.svg": svg(256, 256, mark("mw", "white"), "Troi"),
    "mark-ink.svg": svg(256, 256, mark("mi", "ink"), "Troi"),
    "icon.svg": icon(1024),
    "favicon.svg": icon(256, heavy=True, uid="f"),
    "lockup-dark.svg": lockup_horizontal("dark"),
    "lockup-light.svg": lockup_horizontal("light"),
    "lockup-stacked-dark.svg": lockup_stacked("dark"),
    "lockup-stacked-light.svg": lockup_stacked("light"),
}
for name, text in files.items():
    (OUT / name).write_text(text)
    print(f"{name}: {len(text) / 1024:.1f} KB")
