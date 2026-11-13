#!/usr/bin/env python3
"""Generate Halcyon's user account pictures, in the spirit of Vista's: one
glossy, softly lit subject per square, filling the frame.

    gen_user_pictures.py OUTDIR      writes OUTDIR/<Name>.svg

The package renders them to PNG (rsvg-convert) and installs them where
Plasma's user picture chooser looks (/usr/share/plasma/avatars/photos).
All artwork here is original.
"""
import math
import os
import sys

S = 256  # drawn on a 256 x 256 canvas, rendered larger


def svg(defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{S}" height="{S}" viewBox="0 0 {S} {S}">\n'
            f'<defs>\n{COMMON}\n{defs}\n</defs>\n{body}\n'
            f'<rect width="{S}" height="{S}" fill="url(#vignette)"/>\n</svg>\n')


# Shared filters and the soft vignette every picture ends with.
COMMON = '''
<filter id="blur2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>
<filter id="blur6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="blur12" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="12"/></filter>
<filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
 <feGaussianBlur in="SourceAlpha" stdDeviation="5"/><feOffset dy="5"/>
 <feComponentTransfer><feFuncA type="linear" slope="0.45"/></feComponentTransfer>
 <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<radialGradient id="vignette" cx="0.5" cy="0.5" r="0.75">
 <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.35"/></radialGradient>
<linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#fff" stop-opacity="0.85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
'''


def bokeh(colors, n=14, seed=1, rmin=10, rmax=34, opacity=0.35):
    """Out-of-focus light circles for the background."""
    out, x = [], seed * 9301 + 49297
    for i in range(n):
        x = (x * 9301 + 49297) % 233280
        cx = x / 233280 * S
        x = (x * 9301 + 49297) % 233280
        cy = x / 233280 * S
        x = (x * 9301 + 49297) % 233280
        r = rmin + x / 233280 * (rmax - rmin)
        c = colors[i % len(colors)]
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{c}" opacity="{opacity}" filter="url(#blur2)"/>')
    return "\n".join(out)


def rot(cx, cy, n, body, start=0):
    return "\n".join(f'<g transform="rotate({start + i * 360 / n:.2f} {cx} {cy})">{body}</g>' for i in range(n))


PICTURES = {}


def picture(name):
    def deco(fn):
        PICTURES[name] = fn
        return fn
    return deco


@picture("Goldfish")
def goldfish():
    defs = '''
<radialGradient id="water" cx="0.5" cy="0.3" r="0.9">
 <stop offset="0" stop-color="#bff3ff"/><stop offset="0.5" stop-color="#2aa8dc"/><stop offset="1" stop-color="#05406e"/></radialGradient>
<radialGradient id="body" cx="0.4" cy="0.35" r="0.7">
 <stop offset="0" stop-color="#fff0a0"/><stop offset="0.35" stop-color="#ffa21f"/><stop offset="1" stop-color="#d0420a"/></radialGradient>
<linearGradient id="fin" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#ff8a1c" stop-opacity="0.95"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0.55"/></linearGradient>
<radialGradient id="bubble" cx="0.35" cy="0.3" r="0.7">
 <stop offset="0" stop-color="#fff" stop-opacity="0.9"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.1"/>
 <stop offset="1" stop-color="#fff" stop-opacity="0.6"/></radialGradient>'''
    rays = "\n".join(f'<polygon points="{x},0 {x + 22},0 {x - 40},256 {x - 70},256" fill="#fff" opacity="0.08"/>'
                     for x in (60, 130, 200))
    body = f'''
<rect width="256" height="256" fill="url(#water)"/>
{rays}
{bokeh(["#e8fbff", "#9fe6ff"], n=10, seed=3, opacity=0.25)}
<g filter="url(#shadow)">
 <path d="M150 128 C185 92 222 84 240 98 C226 118 226 140 240 160 C222 172 185 164 150 128 Z" fill="url(#fin)"/>
 <path d="M112 92 C120 62 150 58 164 70 C150 76 140 86 136 98 Z" fill="url(#fin)"/>
 <path d="M118 162 C124 186 146 192 156 184 C146 176 140 168 138 158 Z" fill="url(#fin)"/>
 <ellipse cx="108" cy="128" rx="64" ry="42" fill="url(#body)"/>
 <path d="M90 92 C70 110 70 146 90 164" fill="none" stroke="#b8360a" stroke-width="2" opacity="0.5"/>
 <path d="M100 140 C112 150 128 152 138 146 C130 160 112 160 100 140 Z" fill="#ff7a14" opacity="0.8"/>
 <ellipse cx="102" cy="104" rx="46" ry="16" fill="url(#gloss)" opacity="0.6"/>
 <circle cx="72" cy="118" r="10" fill="#fff"/><circle cx="70" cy="118" r="6.5" fill="#111"/>
 <circle cx="68" cy="115" r="2.2" fill="#fff"/>
 <path d="M46 132 Q50 138 46 142" fill="none" stroke="#a83208" stroke-width="2.5" stroke-linecap="round"/>
</g>
<circle cx="40" cy="96" r="7" fill="url(#bubble)" stroke="#fff" stroke-opacity="0.6"/>
<circle cx="30" cy="66" r="10" fill="url(#bubble)" stroke="#fff" stroke-opacity="0.6"/>
<circle cx="44" cy="30" r="13" fill="url(#bubble)" stroke="#fff" stroke-opacity="0.6"/>'''
    return svg(defs, body)


@picture("Chess")
def chess():
    defs = '''
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#2b3440"/><stop offset="1" stop-color="#0c1016"/></linearGradient>
<linearGradient id="white" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#b9b2a4"/><stop offset="0.35" stop-color="#fffdf6"/><stop offset="1" stop-color="#9c9486"/></linearGradient>
<linearGradient id="black" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#000"/><stop offset="0.3" stop-color="#4a4f58"/><stop offset="0.55" stop-color="#16181c"/>
 <stop offset="1" stop-color="#000"/></linearGradient>
<clipPath id="board"><polygon points="-60,256 316,256 236,150 20,150"/></clipPath>'''
    # Board in perspective: squares between the far edge (y=150) and the bottom.
    sq = []
    rows = [150, 162, 178, 200, 230, 268]
    for r in range(len(rows) - 1):
        y0, y1 = rows[r], rows[r + 1]
        for c in range(-4, 12):
            def x(c_, y):
                t = (y - 150) / 106
                left, right = 20 + (-60 - 20) * t, 236 + (316 - 236) * t
                return left + (right - left) * c_ / 8
            pts = f"{x(c, y0):.1f},{y0} {x(c + 1, y0):.1f},{y0} {x(c + 1, y1):.1f},{y1} {x(c, y1):.1f},{y1}"
            fill = "#e9dcc0" if (r + c) % 2 else "#5b3a22"
            sq.append(f'<polygon points="{pts}" fill="{fill}"/>')

    def pawn(cx, base, k, fill):
        w = lambda v: cx + v * k
        h = lambda v: base - v * k
        return f'''<g filter="url(#shadow)">
 <path d="M{w(-30)} {h(0)} L{w(30)} {h(0)} L{w(28)} {h(10)} Q{w(16)} {h(18)} {w(12)} {h(30)}
  L{w(8)} {h(62)} L{w(18)} {h(66)} L{w(18)} {h(72)} L{w(-18)} {h(72)} L{w(-18)} {h(66)} L{w(-8)} {h(62)}
  L{w(-12)} {h(30)} Q{w(-16)} {h(18)} {w(-28)} {h(10)} Z" fill="url(#{fill})"/>
 <circle cx="{cx}" cy="{h(90)}" r="{20 * k}" fill="url(#{fill})"/>
 <ellipse cx="{w(-6)}" cy="{h(98)}" rx="{8 * k}" ry="{6 * k}" fill="#fff" opacity="0.55" filter="url(#blur2)"/>
</g>'''
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#ffcf7a", "#7ab8ff"], n=8, seed=7, rmin=8, rmax=22, opacity=0.25)}
<g clip-path="url(#board)">{"".join(sq)}</g>
<polygon points="-60,256 316,256 236,150 20,150" fill="url(#gloss)" opacity="0.12"/>
<rect y="140" width="256" height="20" fill="url(#bg)" opacity="0.6" filter="url(#blur6)"/>
{pawn(84, 200, 1.0, "black")}
{pawn(170, 232, 1.25, "white")}'''
    return svg(defs, body)


@picture("Beach Ball")
def beach_ball():
    defs = '''
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#1f8be0"/><stop offset="0.6" stop-color="#8fd6ff"/><stop offset="1" stop-color="#d9f3ff"/></linearGradient>
<linearGradient id="sand" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#f6e2b0"/><stop offset="1" stop-color="#d9b874"/></linearGradient>
<radialGradient id="shade" cx="0.35" cy="0.3" r="0.8">
 <stop offset="0" stop-color="#fff" stop-opacity="0.4"/><stop offset="0.55" stop-color="#fff" stop-opacity="0"/>
 <stop offset="1" stop-color="#002" stop-opacity="0.45"/></radialGradient>
<clipPath id="ball"><circle cx="128" cy="120" r="78"/></clipPath>'''
    colors = ["#e8202a", "#ffffff", "#ffd21a", "#ffffff", "#1a7fe8", "#ffffff"]
    segs = []
    for i, c in enumerate(colors):
        a0, a1 = math.radians(i * 60 - 90), math.radians((i + 1) * 60 - 90)
        # Curved gores: each edge bows like a meridian seen from slightly above.
        p0 = (128 + 160 * math.cos(a0), 70 + 160 * math.sin(a0))
        p1 = (128 + 160 * math.cos(a1), 70 + 160 * math.sin(a1))
        segs.append(f'<path d="M128 70 Q{128 + 60 * math.cos(a0 + 0.4):.1f} {70 + 60 * math.sin(a0 + 0.4):.1f} '
                    f'{p0[0]:.1f} {p0[1]:.1f} L{p1[0]:.1f} {p1[1]:.1f} '
                    f'Q{128 + 60 * math.cos(a1 + 0.4):.1f} {70 + 60 * math.sin(a1 + 0.4):.1f} 128 70 Z" fill="{c}"/>')
    body = f'''
<rect width="256" height="256" fill="url(#sky)"/>
<ellipse cx="60" cy="40" rx="50" ry="14" fill="#fff" opacity="0.7" filter="url(#blur6)"/>
<ellipse cx="200" cy="70" rx="40" ry="10" fill="#fff" opacity="0.6" filter="url(#blur6)"/>
<rect y="150" width="256" height="14" fill="#2a9fd0"/>
<rect y="150" width="256" height="3" fill="#fff" opacity="0.6"/>
<rect y="162" width="256" height="94" fill="url(#sand)"/>
<ellipse cx="136" cy="204" rx="70" ry="12" fill="#6b4a1a" opacity="0.4" filter="url(#blur6)"/>
<g clip-path="url(#ball)">{"".join(segs)}<circle cx="128" cy="120" r="78" fill="url(#shade)"/></g>
<circle cx="128" cy="70" r="8" fill="#f2f2f2" stroke="#bbb"/>
<ellipse cx="104" cy="74" rx="34" ry="18" fill="url(#gloss)" opacity="0.7" transform="rotate(-30 104 74)"/>'''
    return svg(defs, body)


@picture("Daisy")
def daisy():
    defs = '''
<radialGradient id="bg" cx="0.5" cy="0.5" r="0.8">
 <stop offset="0" stop-color="#9ad84a"/><stop offset="1" stop-color="#1f5a14"/></radialGradient>
<linearGradient id="petal" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d9e6f0"/></linearGradient>
<radialGradient id="eye" cx="0.4" cy="0.35" r="0.7">
 <stop offset="0" stop-color="#fff59a"/><stop offset="0.5" stop-color="#ffc21a"/><stop offset="1" stop-color="#c7700a"/></radialGradient>'''
    petal = ('<path d="M128 124 C116 96 118 50 128 36 C138 50 140 96 128 124 Z" fill="url(#petal)" '
             'stroke="#b8c8d6" stroke-width="0.8"/>')
    dots = "".join(f'<circle cx="{128 + r * math.cos(a):.1f}" cy="{128 + r * math.sin(a):.1f}" r="1.6" fill="#a85a06" opacity="0.6"/>'
                   for r in (6, 12, 18) for a in [i * 2.4 + r for i in range(int(r * 1.2))])
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#d8ff9a", "#ffffff", "#6fc23a"], n=14, seed=11, opacity=0.3)}
<g filter="url(#shadow)">
 <g transform="rotate(-12 128 128)">{rot(128, 128, 18, petal)}</g>
 <circle cx="128" cy="128" r="26" fill="url(#eye)"/>{dots}
 <ellipse cx="120" cy="116" rx="12" ry="7" fill="#fff" opacity="0.5" filter="url(#blur2)"/>
</g>'''
    return svg(defs, body)


@picture("Butterfly")
def butterfly():
    defs = '''
<radialGradient id="bg" cx="0.5" cy="0.45" r="0.8">
 <stop offset="0" stop-color="#fff6d6"/><stop offset="0.6" stop-color="#f3c25a"/><stop offset="1" stop-color="#8a4f10"/></radialGradient>
<radialGradient id="wing" cx="0.3" cy="0.5" r="0.9">
 <stop offset="0" stop-color="#9ff3ff"/><stop offset="0.4" stop-color="#1e9be0"/><stop offset="0.8" stop-color="#0a3c8c"/>
 <stop offset="1" stop-color="#061a3a"/></radialGradient>'''
    wing = '''
<path d="M128 120 C110 70 60 40 34 58 C14 74 30 118 70 132 C92 140 118 132 128 120 Z" fill="url(#wing)" stroke="#04122a" stroke-width="3"/>
<path d="M128 132 C104 136 66 148 62 178 C60 202 90 212 108 192 C120 178 126 156 128 132 Z" fill="url(#wing)" stroke="#04122a" stroke-width="3"/>
<circle cx="46" cy="70" r="5" fill="#fff" opacity="0.85"/><circle cx="38" cy="90" r="3.5" fill="#fff" opacity="0.85"/>
<circle cx="74" cy="192" r="4" fill="#fff" opacity="0.8"/>
<path d="M126 122 C100 96 70 76 48 68" fill="none" stroke="#04122a" stroke-width="1.4" opacity="0.5"/>
<path d="M126 124 C96 116 70 110 44 104" fill="none" stroke="#04122a" stroke-width="1.4" opacity="0.5"/>'''
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#ffffff", "#ffe08a"], n=12, seed=5, opacity=0.35)}
<g filter="url(#shadow)" transform="rotate(-8 128 128)">
 {wing}
 <g transform="translate(256 0) scale(-1 1)">{wing}</g>
 <ellipse cx="128" cy="134" rx="6" ry="36" fill="#1a1208"/>
 <circle cx="128" cy="96" r="8" fill="#1a1208"/>
 <path d="M126 90 Q114 64 104 58 M130 90 Q142 64 152 58" fill="none" stroke="#1a1208" stroke-width="2.2" stroke-linecap="round"/>
 <circle cx="104" cy="58" r="3" fill="#1a1208"/><circle cx="152" cy="58" r="3" fill="#1a1208"/>
 <ellipse cx="80" cy="76" rx="30" ry="12" fill="url(#gloss)" opacity="0.45" transform="rotate(25 80 76)"/>
 <ellipse cx="176" cy="76" rx="30" ry="12" fill="url(#gloss)" opacity="0.45" transform="rotate(-25 176 76)"/>
</g>'''
    return svg(defs, body)


@picture("Rubber Duck")
def duck():
    defs = '''
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#e8f7ff"/><stop offset="0.55" stop-color="#7cc8ee"/><stop offset="1" stop-color="#1c7ab8"/></linearGradient>
<radialGradient id="yellow" cx="0.35" cy="0.3" r="0.8">
 <stop offset="0" stop-color="#fffbd0"/><stop offset="0.4" stop-color="#ffd81a"/><stop offset="1" stop-color="#d98a00"/></radialGradient>
<linearGradient id="beak" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ffb04a"/><stop offset="1" stop-color="#e2550a"/></linearGradient>'''
    ripples = "".join(f'<ellipse cx="128" cy="196" rx="{rx}" ry="{rx * 0.16:.1f}" fill="none" stroke="#fff" '
                      f'stroke-opacity="{0.6 - i * 0.12:.2f}" stroke-width="2"/>' for i, rx in enumerate((92, 112, 132, 152)))
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#ffffff"], n=8, seed=13, rmin=6, rmax=18, opacity=0.4)}
{ripples}
<g filter="url(#shadow)">
 <path d="M52 168 C48 132 78 120 104 128 C110 110 146 106 176 120 C206 132 214 160 200 182 C186 204 76 206 58 190 C52 184 52 176 52 168 Z" fill="url(#yellow)"/>
 <path d="M188 136 C204 120 214 108 212 98 C222 112 214 140 196 150 Z" fill="url(#yellow)"/>
 <circle cx="104" cy="96" r="44" fill="url(#yellow)"/>
 <path d="M60 104 C40 100 30 110 32 118 C46 122 60 120 70 114 Z" fill="url(#beak)"/>
 <path d="M34 116 C46 118 58 116 68 112" fill="none" stroke="#a83a04" stroke-width="1.5" opacity="0.6"/>
 <circle cx="88" cy="84" r="8" fill="#1a1208"/><circle cx="85" cy="81" r="2.6" fill="#fff"/>
 <path d="M110 150 C130 168 160 166 174 150" fill="none" stroke="#c77a00" stroke-width="3" stroke-linecap="round" opacity="0.6"/>
 <ellipse cx="96" cy="70" rx="24" ry="12" fill="url(#gloss)" opacity="0.8" transform="rotate(-20 96 70)"/>
</g>
<rect y="186" width="256" height="70" fill="#1c7ab8" opacity="0.35"/>'''
    return svg(defs, body)


@picture("Guitar")
def guitar():
    defs = '''
<radialGradient id="bg" cx="0.5" cy="0.4" r="0.8">
 <stop offset="0" stop-color="#7a2a14"/><stop offset="1" stop-color="#1a0604"/></radialGradient>
<radialGradient id="wood" cx="0.4" cy="0.35" r="0.75">
 <stop offset="0" stop-color="#ffd890"/><stop offset="0.5" stop-color="#e09030"/><stop offset="0.85" stop-color="#9a4a10"/>
 <stop offset="1" stop-color="#4a1c04"/></radialGradient>
<linearGradient id="neck" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#3a1a0a"/><stop offset="0.5" stop-color="#6a3a1a"/><stop offset="1" stop-color="#2a1006"/></linearGradient>'''
    frets = "".join(f'<line x1="-9" y1="{y}" x2="9" y2="{y}" stroke="#d8d8d8" stroke-width="1.4"/>' for y in range(-138, -40, 14))
    strings = "".join(f'<line x1="{x}" y1="-150" x2="{x}" y2="76" stroke="#f4f0e0" stroke-width="0.8" opacity="0.85"/>'
                      for x in (-7.5, -4.5, -1.5, 1.5, 4.5, 7.5))
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#ffb050", "#ffe0a0"], n=10, seed=17, opacity=0.2)}
<g transform="translate(136 150) rotate(30) scale(0.8)" filter="url(#shadow)">
 <path d="M0 -36 C34 -38 46 -16 40 4 C36 18 56 30 56 58 C56 96 26 108 0 108 C-26 108 -56 96 -56 58
  C-56 30 -36 18 -40 4 C-46 -16 -34 -38 0 -36 Z" fill="url(#wood)" stroke="#2a0e02" stroke-width="3"/>
 <circle cx="0" cy="14" r="17" fill="#1a0a02" stroke="#2a0e02" stroke-width="4"/>
 <circle cx="0" cy="14" r="22" fill="none" stroke="#3a1a08" stroke-width="2" opacity="0.7"/>
 <rect x="-10" y="-160" width="20" height="160" fill="url(#neck)"/>
 <path d="M-14 -190 L14 -190 L12 -156 L-12 -156 Z" fill="#2a1006"/>
 {"".join(f'<circle cx="{sx}" cy="{y}" r="3" fill="#d8d8d8"/>' for sx in (-17, 17) for y in (-184, -174, -164))}
 {frets}
 <rect x="-14" y="72" width="28" height="7" rx="2" fill="#1a0a02"/>
 {strings}
 <ellipse cx="-22" cy="-6" rx="16" ry="30" fill="url(#gloss)" opacity="0.45" transform="rotate(-20 -22 -6)"/>
</g>'''
    return svg(defs, body)


@picture("Snowflake")
def snowflake():
    defs = '''
<radialGradient id="bg" cx="0.5" cy="0.5" r="0.75">
 <stop offset="0" stop-color="#5bb8f0"/><stop offset="0.6" stop-color="#14508c"/><stop offset="1" stop-color="#061a3a"/></radialGradient>
<linearGradient id="ice" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#bfe8ff"/></linearGradient>'''
    arm = '''<path d="M125 128 L125 38 L128 30 L131 38 L131 128 Z" fill="url(#ice)"/>
<path d="M128 92 L106 70 L110 66 L128 84 L146 66 L150 70 Z" fill="url(#ice)"/>
<path d="M128 62 L114 48 L117 45 L128 56 L139 45 L142 48 Z" fill="url(#ice)"/>
<path d="M128 112 L118 104 L121 101 L128 106 L135 101 L138 104 Z" fill="url(#ice)"/>
<circle cx="128" cy="30" r="4" fill="#fff"/>'''
    sparkles = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" opacity="0.8" filter="url(#blur2)"/>'
                       for x, y, r in ((40, 50, 3), (210, 40, 2.5), (226, 200, 3.5), (30, 214, 2), (186, 236, 2)))
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#bfe8ff", "#ffffff"], n=16, seed=19, rmin=4, rmax=20, opacity=0.25)}
{sparkles}
<circle cx="128" cy="128" r="80" fill="#bfe8ff" opacity="0.25" filter="url(#blur12)"/>
<g filter="url(#shadow)">{rot(128, 128, 6, arm)}
 <polygon points="{" ".join(f"{128 + 16 * math.cos(math.radians(a)):.1f},{128 + 16 * math.sin(math.radians(a)):.1f}" for a in range(30, 390, 60))}"
  fill="#ffffff" stroke="#bfe8ff" stroke-width="2"/></g>'''
    return svg(defs, body)


@picture("Sunset")
def sunset():
    defs = '''
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#2a1a5a"/><stop offset="0.35" stop-color="#c2386a"/><stop offset="0.6" stop-color="#ff9a3a"/>
 <stop offset="0.66" stop-color="#ffd27a"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#d06a3a"/><stop offset="0.4" stop-color="#5a2a5a"/><stop offset="1" stop-color="#140a2a"/></linearGradient>
<radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
 <stop offset="0" stop-color="#fffbe0"/><stop offset="0.7" stop-color="#ffd860"/><stop offset="1" stop-color="#ff9a2a"/></radialGradient>'''
    glints = "".join(f'<rect x="{128 - w / 2:.1f}" y="{y}" width="{w:.1f}" height="2.5" rx="1.2" fill="#ffe8a0" opacity="{0.9 - i * 0.07:.2f}"/>'
                     for i, (y, w) in enumerate(zip(range(176, 256, 9), (90, 74, 80, 60, 66, 46, 52, 36, 40))))
    body = f'''
<rect width="256" height="170" fill="url(#sky)"/>
<circle cx="128" cy="150" r="70" fill="#ffb050" opacity="0.5" filter="url(#blur12)"/>
<circle cx="128" cy="150" r="40" fill="url(#sun)"/>
<ellipse cx="60" cy="70" rx="70" ry="9" fill="#ff8aa0" opacity="0.55" filter="url(#blur6)"/>
<ellipse cx="200" cy="100" rx="60" ry="7" fill="#ffb07a" opacity="0.6" filter="url(#blur6)"/>
<ellipse cx="170" cy="50" rx="50" ry="6" fill="#d86a9a" opacity="0.5" filter="url(#blur6)"/>
<rect y="168" width="256" height="88" fill="url(#sea)"/>
{glints}
<path d="M0 172 C40 160 70 166 96 170 L0 170 Z M180 170 C200 160 230 158 256 166 L256 170 Z" fill="#1a0a2a"/>'''
    return svg(defs, body)


@picture("Dewdrop")
def dewdrop():
    defs = '''
<radialGradient id="bg" cx="0.5" cy="0.5" r="0.8">
 <stop offset="0" stop-color="#c8f08a"/><stop offset="1" stop-color="#2a6a10"/></radialGradient>
<linearGradient id="leaf" x1="0" y1="0" x2="1" y2="1">
 <stop offset="0" stop-color="#b8f05a"/><stop offset="0.5" stop-color="#4fae1c"/><stop offset="1" stop-color="#1c5a08"/></linearGradient>
<radialGradient id="drop" cx="0.5" cy="0.6" r="0.6">
 <stop offset="0" stop-color="#eaffd0" stop-opacity="0.9"/><stop offset="0.6" stop-color="#7ad040" stop-opacity="0.5"/>
 <stop offset="1" stop-color="#1c5a08" stop-opacity="0.8"/></radialGradient>'''
    veins = "".join(f'<path d="M{x} {y} Q{x + 18} {y - 30} {x + 50} {y - 44}" fill="none" stroke="#d8ff9a" stroke-width="1.6" opacity="0.6"/>'
                    for x, y in ((70, 190), (100, 160), (130, 130)))
    veins += "".join(f'<path d="M{x} {y} Q{x - 30} {y - 18} {x - 44} {y - 50}" fill="none" stroke="#d8ff9a" stroke-width="1.6" opacity="0.6"/>'
                     for x, y in ((90, 210), (120, 180), (150, 150)))
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{bokeh(["#f0ffc0", "#ffffff"], n=12, seed=23, opacity=0.3)}
<g filter="url(#shadow)">
 <path d="M30 236 C20 140 90 40 230 22 C236 150 150 232 30 236 Z" fill="url(#leaf)"/>
 <path d="M30 236 C90 170 160 90 230 22" fill="none" stroke="#e8ffb0" stroke-width="3" opacity="0.8"/>
 {veins}
</g>
<ellipse cx="146" cy="128" rx="34" ry="8" fill="#0e3a04" opacity="0.5" filter="url(#blur6)"/>
<circle cx="140" cy="108" r="30" fill="url(#drop)" stroke="#f4ffe0" stroke-opacity="0.7" stroke-width="1.5"/>
<ellipse cx="130" cy="94" rx="13" ry="8" fill="#fff" opacity="0.9" transform="rotate(-30 130 94)"/>
<circle cx="154" cy="124" r="3" fill="#fff" opacity="0.7"/>
<circle cx="190" cy="74" r="10" fill="url(#drop)" stroke="#f4ffe0" stroke-opacity="0.7"/>
<circle cx="187" cy="70" r="3" fill="#fff" opacity="0.9"/>'''
    return svg(defs, body)


@picture("Kite")
def kite():
    defs = '''
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#0a6ad0"/><stop offset="1" stop-color="#9adcff"/></linearGradient>
<linearGradient id="k1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff5a5a"/><stop offset="1" stop-color="#b0101a"/></linearGradient>
<linearGradient id="k2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe55a"/><stop offset="1" stop-color="#e09a00"/></linearGradient>
<linearGradient id="k3" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6ae05a"/><stop offset="1" stop-color="#1a8a10"/></linearGradient>
<linearGradient id="k4" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5ab0ff"/><stop offset="1" stop-color="#1040b0"/></linearGradient>'''
    bows = "".join(f'<path d="M{x - 7} {y - 5} L{x + 7} {y + 5} L{x + 7} {y - 5} L{x - 7} {y + 5} Z" fill="{c}"/>'
                   for x, y, c in ((112, 182, "#ff5a5a"), (98, 208, "#ffe55a"), (90, 234, "#5ab0ff")))
    body = f'''
<rect width="256" height="256" fill="url(#sky)"/>
<ellipse cx="200" cy="200" rx="80" ry="22" fill="#fff" opacity="0.85" filter="url(#blur12)"/>
<ellipse cx="50" cy="60" rx="50" ry="14" fill="#fff" opacity="0.7" filter="url(#blur6)"/>
<ellipse cx="230" cy="40" rx="30" ry="8" fill="#fff" opacity="0.6" filter="url(#blur6)"/>
<circle cx="236" cy="22" r="40" fill="#fffbe0" opacity="0.5" filter="url(#blur12)"/>
<path d="M128 160 C118 190 106 200 100 214 C94 228 92 240 86 256" fill="none" stroke="#fff" stroke-width="1.5" opacity="0.9"/>
<path d="M128 160 C170 200 210 220 256 230" fill="none" stroke="#fff" stroke-width="1" opacity="0.6"/>
{bows}
<g filter="url(#shadow)" transform="rotate(-14 128 100)">
 <polygon points="128,24 128,96 80,80" fill="url(#k1)"/>
 <polygon points="128,24 176,80 128,96" fill="url(#k2)"/>
 <polygon points="80,80 128,96 128,166" fill="url(#k4)"/>
 <polygon points="128,96 176,80 128,166" fill="url(#k3)"/>
 <path d="M128 24 L128 166 M80 80 Q128 100 176 80" fill="none" stroke="#3a2a1a" stroke-width="2"/>
 <polygon points="128,24 176,80 128,166 80,80" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="2"/>
 <polygon points="128,30 168,78 128,90 88,78" fill="url(#gloss)" opacity="0.4"/>
</g>'''
    return svg(defs, body)


@picture("Planet")
def planet():
    defs = '''
<radialGradient id="space" cx="0.3" cy="0.3" r="1">
 <stop offset="0" stop-color="#1a2a6a"/><stop offset="1" stop-color="#02040e"/></radialGradient>
<radialGradient id="globe" cx="0.35" cy="0.3" r="0.8">
 <stop offset="0" stop-color="#bff0ff"/><stop offset="0.35" stop-color="#2aa0e0"/><stop offset="0.8" stop-color="#0a3a8a"/>
 <stop offset="1" stop-color="#020a2a"/></radialGradient>
<radialGradient id="land" cx="0.35" cy="0.3" r="0.8">
 <stop offset="0" stop-color="#c8ff8a"/><stop offset="0.5" stop-color="#4aae2a"/><stop offset="1" stop-color="#0a3a10"/></radialGradient>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#ffe0a0" stop-opacity="0.2"/><stop offset="0.5" stop-color="#fff4d0" stop-opacity="0.95"/>
 <stop offset="1" stop-color="#ffe0a0" stop-opacity="0.2"/></linearGradient>
<clipPath id="globeclip"><circle cx="128" cy="128" r="72"/></clipPath>
<clipPath id="back"><rect x="0" y="0" width="256" height="128"/></clipPath>
<clipPath id="front"><rect x="0" y="128" width="256" height="128"/></clipPath>'''
    stars = []
    x = 31
    for _ in range(40):
        x = (x * 9301 + 49297) % 233280
        sx = x / 233280 * 256
        x = (x * 9301 + 49297) % 233280
        sy = x / 233280 * 256
        stars.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{0.6 + (x % 7) / 6:.2f}" fill="#fff" opacity="{0.4 + (x % 5) / 8:.2f}"/>')
    # Drawn in the ring's own (tilted) frame: the far half behind the globe, the near half in front.
    ring = '<ellipse cx="128" cy="128" rx="118" ry="26" fill="none" stroke="url(#ring)" stroke-width="10"/>'
    body = f'''
<rect width="256" height="256" fill="url(#space)"/>
{"".join(stars)}
<circle cx="128" cy="128" r="90" fill="#2aa0e0" opacity="0.35" filter="url(#blur12)"/>
<g transform="rotate(-18 128 128)"><g clip-path="url(#back)">{ring}</g></g>
<circle cx="128" cy="128" r="72" fill="url(#globe)"/>
<g clip-path="url(#globeclip)" opacity="0.9">
 <path d="M70 90 C90 70 120 76 126 96 C132 116 110 120 104 140 C98 160 76 150 66 130 C60 116 60 100 70 90 Z" fill="url(#land)"/>
 <path d="M150 140 C170 130 196 140 200 160 C204 182 180 196 162 188 C146 180 140 156 150 140 Z" fill="url(#land)"/>
 <path d="M150 70 C162 64 178 70 180 84 C170 90 156 86 150 70 Z" fill="url(#land)"/>
 <ellipse cx="128" cy="128" rx="80" ry="10" fill="#fff" opacity="0.25" transform="rotate(-20 128 128)" filter="url(#blur2)"/>
</g>
<circle cx="128" cy="128" r="72" fill="none" stroke="#9fe6ff" stroke-opacity="0.6" stroke-width="2"/>
<ellipse cx="108" cy="92" rx="40" ry="24" fill="url(#gloss)" opacity="0.55" transform="rotate(-25 108 92)"/>
<g transform="rotate(-18 128 128)"><g clip-path="url(#front)">{ring}</g></g>'''
    return svg(defs, body)


# ------------------------------------------------------------------ skate ---
def concrete(top="#c9d2da", bottom="#6e7a86"):
    return (f'<linearGradient id="concrete" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>')


def wheel(cx, cy, r, color="#f4f0e4"):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" stroke="#7a7466" stroke-width="1.5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.45:.1f}" fill="#9aa2aa" stroke="#4a5058"/>'
            f'<circle cx="{cx - r * 0.3:.1f}" cy="{cy - r * 0.35:.1f}" r="{r * 0.28:.1f}" fill="#fff" opacity="0.7"/>')


@picture("Skateboard")
def skateboard():
    defs = concrete("#ffb35a", "#c2386a") + '''
<linearGradient id="deck" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#3ad0ff"/><stop offset="0.5" stop-color="#1a7ae0"/><stop offset="1" stop-color="#0a2a8a"/></linearGradient>'''
    # The board flies through a sunset, nose up, seen from below so its graphic shows.
    body = f'''
<rect width="256" height="256" fill="url(#concrete)"/>
<circle cx="200" cy="70" r="80" fill="#fff0b0" opacity="0.6" filter="url(#blur12)"/>
<circle cx="200" cy="70" r="30" fill="#fffbe0" opacity="0.9"/>
{bokeh(["#fff0c0", "#ff8aa0"], n=10, seed=29, opacity=0.25)}
<path d="M0 214 L256 196 L256 256 L0 256 Z" fill="#2a1a3a" opacity="0.85"/>
<ellipse cx="128" cy="222" rx="80" ry="8" fill="#000" opacity="0.4" filter="url(#blur6)"/>
<g transform="rotate(-22 128 120)" filter="url(#shadow)">
 <path d="M40 104 C28 104 22 114 24 124 C26 134 34 138 44 138 L212 138 C222 138 230 134 232 124 C234 114 228 104 216 104 Z"
  fill="url(#deck)" stroke="#06184a" stroke-width="2.5"/>
 <path d="M60 112 L118 112 L104 130 L46 130 Z" fill="#ffe14a" opacity="0.95"/>
 <path d="M124 112 L182 112 L168 130 L110 130 Z" fill="#ff4a6a" opacity="0.95"/>
 <circle cx="196" cy="121" r="9" fill="#fff" opacity="0.9"/><circle cx="196" cy="121" r="4" fill="#1a7ae0"/>
 <rect x="64" y="138" width="22" height="8" rx="2" fill="#b8c0c8" stroke="#4a5058"/>
 <rect x="170" y="138" width="22" height="8" rx="2" fill="#b8c0c8" stroke="#4a5058"/>
 {wheel(64, 152, 11)}{wheel(86, 152, 11)}{wheel(170, 152, 11)}{wheel(192, 152, 11)}
 <path d="M44 106 L212 106 C220 106 226 110 228 116 L28 116 C30 110 36 106 44 106 Z" fill="url(#gloss)" opacity="0.5"/>
</g>
<path d="M40 70 L70 80 M30 100 L62 104 M46 44 L72 58" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity="0.6"/>'''
    return svg(defs, body)


@picture("Half Pipe")
def half_pipe():
    curve = "M20 90 C20 190 56 214 128 214 C200 214 236 190 236 90"
    defs = f'''
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#1a6ad8"/><stop offset="1" stop-color="#a8e2ff"/></linearGradient>
<linearGradient id="ramp" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#e8d2a8"/><stop offset="1" stop-color="#a87a44"/></linearGradient>
<clipPath id="rampclip"><path d="{curve} L256 90 L256 256 L0 256 L0 90 Z"/></clipPath>'''
    planks = "".join(f'<line x1="{x}" y1="90" x2="{x}" y2="256" stroke="#7a5428" stroke-width="1" opacity="0.35"/>'
                     for x in range(24, 256, 26))
    body = f'''
<rect width="256" height="256" fill="url(#sky)"/>
<ellipse cx="70" cy="50" rx="60" ry="14" fill="#fff" opacity="0.8" filter="url(#blur6)"/>
<ellipse cx="200" cy="34" rx="44" ry="10" fill="#fff" opacity="0.7" filter="url(#blur6)"/>
<path d="M0 140 L40 120 L80 132 L120 112 L170 128 L210 116 L256 130 L256 160 L0 160 Z" fill="#4a8ab0" opacity="0.5"/>
<path d="M0 90 L0 256 L256 256 L256 90 L236 90 C236 190 200 214 128 214 C56 214 20 190 20 90 Z" fill="url(#ramp)"/>
<g clip-path="url(#rampclip)">{planks}</g>
<path d="M0 90 L{curve[1:]} L256 90" fill="none" stroke="#5a3414" stroke-width="3"/>
<rect x="0" y="84" width="24" height="8" fill="#c8ccd2" stroke="#6a7078"/>
<rect x="232" y="84" width="24" height="8" fill="#c8ccd2" stroke="#6a7078"/>
<path d="M20 92 C22 150 40 180 70 196" fill="none" stroke="#fff" stroke-width="4" opacity="0.35"/>
<g transform="translate(172 80) rotate(-30) scale(1.5)" filter="url(#shadow)">
 <path d="M-34 -6 C-40 -6 -42 6 -34 6 L34 6 C42 6 40 -6 34 -6 Z" fill="#ff4a2a" stroke="#6a1006" stroke-width="2"/>
 {wheel(-20, 12, 6)}{wheel(20, 12, 6)}
</g>
<path d="M150 120 C160 108 166 98 170 92" stroke="#fff" stroke-width="2.5" stroke-linecap="round" opacity="0.7" fill="none"/>
<path d="M138 128 C150 114 158 104 162 96" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity="0.5" fill="none"/>'''
    return svg(defs, body)


@picture("High Tops")
def high_tops():
    defs = '''
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
 <stop offset="0" stop-color="#ffe14a"/><stop offset="1" stop-color="#ff7a1a"/></linearGradient>
<linearGradient id="canvas" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ff5a6a"/><stop offset="1" stop-color="#b0101a"/></linearGradient>
<linearGradient id="sole" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#cfd2d6"/></linearGradient>'''
    laces = "".join(f'<path d="M{100 + i * 9} {80 + i * 13} L{126 + i * 8} {88 + i * 12}" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'
                    for i in range(6))
    eyelets = "".join(f'<circle cx="{c}" cy="{y}" r="2.6" fill="#ddd" stroke="#555"/>'
                      for i in range(6) for c, y in ((100 + i * 9, 80 + i * 13), (126 + i * 8, 88 + i * 12)))
    rays = rot(128, 128, 16, '<polygon points="128,128 120,-80 136,-80" fill="#fff" opacity="0.12"/>')
    body = f'''
<rect width="256" height="256" fill="url(#bg)"/>
{rays}
<ellipse cx="140" cy="228" rx="110" ry="10" fill="#7a2a00" opacity="0.4" filter="url(#blur6)"/>
<g filter="url(#shadow)">
 <path d="M84 52 L140 60 C142 100 150 140 176 156 C200 168 228 170 236 182 L236 200 L40 200 L40 180
  C50 150 70 100 84 52 Z" fill="url(#canvas)" stroke="#5a0408" stroke-width="2.5"/>
 <path d="M90 60 C100 100 120 150 150 170" fill="none" stroke="#5a0408" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.6"/>
 <path d="M86 92 L70 136 L84 134 L72 176 L106 120 L90 122 L102 92 Z" fill="#ffe14a" stroke="#5a0408" stroke-width="2" stroke-linejoin="round"/>
 {laces}{eyelets}
 <path d="M34 196 L240 196 L242 214 C242 220 236 224 228 224 L44 224 C36 224 30 220 30 212 Z" fill="url(#sole)" stroke="#7a7e84" stroke-width="2"/>
 <rect x="30" y="204" width="212" height="4" fill="#b0101a"/>
 <path d="M176 196 C190 176 214 174 238 182 L240 196 Z" fill="url(#sole)" stroke="#7a7e84" stroke-width="2"/>
 <path d="M88 58 L136 64 C136 90 132 110 126 130 C110 110 96 84 88 58 Z" fill="url(#gloss)" opacity="0.35"/>
</g>'''
    return svg(defs, body)


@picture("Helmet")
def helmet():
    defs = concrete("#5a6470", "#1c2228") + '''
<radialGradient id="shell" cx="0.35" cy="0.3" r="0.85">
 <stop offset="0" stop-color="#b8ff6a"/><stop offset="0.45" stop-color="#3ac41a"/><stop offset="1" stop-color="#0c4a06"/></radialGradient>'''
    vents = "".join(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="5" fill="#0a2a04" transform="rotate({a} {x} {y})"/>'
                    for x, y, a in ((100, 70, -30), (128, 62, 0), (156, 70, 30), (86, 96, -50), (170, 96, 50)))
    body = f'''
<rect width="256" height="256" fill="url(#concrete)"/>
{bokeh(["#9aa8b8", "#ffcf7a"], n=12, seed=31, opacity=0.2)}
<ellipse cx="128" cy="214" rx="96" ry="12" fill="#000" opacity="0.5" filter="url(#blur6)"/>
<g filter="url(#shadow)">
 <path d="M30 176 C24 90 76 40 128 40 C180 40 232 90 226 176 C226 190 212 196 196 192 L60 192 C44 196 30 190 30 176 Z"
  fill="url(#shell)" stroke="#063002" stroke-width="3"/>
 <path d="M32 170 C80 182 176 182 224 170 L226 180 C176 194 80 194 30 180 Z" fill="#1a1a1a"/>
 {vents}
 <g transform="rotate(-14 70 130)"><rect x="46" y="116" width="50" height="26" rx="5" fill="#ffe14a" stroke="#7a5a00"/>
  <text x="71" y="135" font-family="sans-serif" font-weight="bold" font-size="15" fill="#c2101a" text-anchor="middle">SK8</text></g>
 <circle cx="178" cy="132" r="17" fill="#1a7ae0" stroke="#fff" stroke-width="3"/>
 <path d="M170 132 L176 138 L188 124" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
 <g transform="rotate(10 128 156)"><rect x="104" y="146" width="48" height="18" rx="9" fill="#ff4a8a" stroke="#fff" stroke-width="2"/>
  <circle cx="116" cy="155" r="4" fill="#fff"/><circle cx="140" cy="155" r="4" fill="#fff"/></g>
 <path d="M60 80 C80 54 110 46 140 48 C110 56 84 72 70 96 Z" fill="#fff" opacity="0.55"/>
</g>'''
    return svg(defs, body)


@picture("Spray Can")
def spray_can():
    defs = '''
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#8a8e96"/><stop offset="1" stop-color="#4a4e56"/></linearGradient>
<linearGradient id="can" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#4a0a6a"/><stop offset="0.3" stop-color="#d86aff"/><stop offset="0.5" stop-color="#9a2ad0"/>
 <stop offset="1" stop-color="#2a0440"/></linearGradient>
<linearGradient id="metal" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#6a6e74"/><stop offset="0.35" stop-color="#f4f6f8"/><stop offset="1" stop-color="#5a5e64"/></linearGradient>
<linearGradient id="tag1" x1="0" y1="0" x2="1" y2="1">
 <stop offset="0" stop-color="#3affd8"/><stop offset="1" stop-color="#1a7ae0"/></linearGradient>
<linearGradient id="tag2" x1="0" y1="0" x2="1" y2="1">
 <stop offset="0" stop-color="#ffe14a"/><stop offset="1" stop-color="#ff5a1a"/></linearGradient>'''
    bricks = "".join(f'<rect x="{(c * 52) - (26 if r % 2 else 0)}" y="{r * 24}" width="50" height="22" fill="none" '
                     f'stroke="#3a3e46" stroke-width="2" opacity="0.6"/>' for r in range(11) for c in range(6))
    mist = "".join(f'<circle cx="{170 + (i * 37) % 60}" cy="{96 + (i * 23) % 50}" r="{1 + i % 3}" fill="#ff6ad8" opacity="0.7"/>'
                   for i in range(18))
    body = f'''
<rect width="256" height="256" fill="url(#wall)"/>
{bricks}
<g opacity="0.92" filter="url(#blur2)">
 <path d="M14 100 C30 40 70 30 80 60 C88 84 50 110 60 130 C70 150 110 120 120 80 C126 60 150 50 160 72
  C170 94 140 130 164 140 C190 150 210 90 240 70" fill="none" stroke="url(#tag1)" stroke-width="16" stroke-linecap="round"/>
 <path d="M30 180 C60 150 90 196 120 170" fill="none" stroke="url(#tag2)" stroke-width="12" stroke-linecap="round"/>
</g>
<circle cx="200" cy="120" r="30" fill="#ff4aa8" opacity="0.35" filter="url(#blur12)"/>
{mist}
<g transform="rotate(18 150 170)" filter="url(#shadow)">
 <rect x="112" y="118" width="70" height="126" rx="10" fill="url(#can)" stroke="#1a0228" stroke-width="2"/>
 <path d="M112 128 C112 104 182 104 182 128 Z" fill="url(#metal)" stroke="#3a3e44" stroke-width="2"/>
 <rect x="138" y="94" width="18" height="16" rx="3" fill="url(#metal)" stroke="#3a3e44"/>
 <rect x="141" y="86" width="12" height="10" rx="2" fill="#f4f4f4" stroke="#555"/>
 <rect x="112" y="160" width="70" height="40" fill="#fff" opacity="0.9"/>
 <path d="M122 186 C130 168 142 196 152 176 C158 166 166 184 172 172" fill="none" stroke="#9a2ad0" stroke-width="5" stroke-linecap="round"/>
 <rect x="122" y="124" width="14" height="114" rx="6" fill="#fff" opacity="0.35"/>
</g>'''
    return svg(defs, body)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "user-pictures"
    os.makedirs(out, exist_ok=True)
    for name, fn in PICTURES.items():
        with open(os.path.join(out, name + ".svg"), "w") as f:
            f.write(fn())
