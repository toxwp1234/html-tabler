#!/usr/bin/env python3
"""HYBRID: per-cell random effects + neighbour waves (pure CSS, no JS).

Merges playground.py (every cell rolls its own idle/hover/click effect) with
wild.py (a cell's hover/click ripples out to its NEIGHBOURS). So the grid is
alive in two layers at once:

  * Each cell:   its own idle animation + its own random hover + click effect.
  * Its region:  hovering shoves neighbours aside (wave/flee); clicking scatters
                 them (shatter) — via sibling combinators and :has().

How the two layers avoid fighting over `transform`:
  * The hovered / clicked cell uses ITS OWN effect (higher specificity than the
    neighbour rules, which never target the hovered cell itself).
  * Neighbour shove/shatter use `transform`; a MOTION cell's transform is busy
    spinning, so spinners simply don't get shoved (they keep spinning — fine).
  * Idle filters and neighbour glows both touch `filter`; whichever the cell has
    wins. No crashes, just graceful overlap.

:has() is heavy on big grids. Keep n*m modest; shrink if it stutters.
Nondescript <title>. For a browser only (a toy).

Input: n m scale  (scale = cell size in px)

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python hybrid.py 20 20 26
"""

import colorsys
import random
import re
import sys

READABLE = "index.html"
OPTIMAL = "optimal.html"

COLOR_MODE = "rainbow"
BASE_HUE = 280
PALETTE = 48
IDLE_CHANCE = 0.7
MOTION_CHANCE = 0.3

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cname(index, prefix=""):
    base = len(_ALPHABET)
    name = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, base)
        name = _ALPHABET[rem] + name
    return prefix + name


def rgb_to_hex(r, g, b):
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def make_palette(rng):
    cols = []
    for _ in range(PALETTE):
        if COLOR_MODE == "mono":
            h = (BASE_HUE % 360) / 360.0
            cols.append(rgb_to_hex(*colorsys.hls_to_rgb(
                h, rng.uniform(0.25, 0.75), rng.uniform(0.5, 1.0))))
        else:
            cols.append(f"#{rng.randint(0, 0xFFFFFF):06x}")
    return cols


def complement(hex_color):
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return rgb_to_hex(*colorsys.hls_to_rgb((h + 0.5) % 1.0, l, s))


# --- Per-cell effect pools (from playground) -------------------------------
HOVERS_T = [
    "transform:scale(2.2) rotate(8deg);box-shadow:0 0 14px rgba(0,0,0,.5)",
    "transform:scale(1.5) rotate(180deg)",
    "transform:perspective(200px) rotateY(180deg) scale(1.3)",
    "transform:perspective(200px) rotateX(180deg) scale(1.3)",
    "transform:skew(-18deg,6deg) scale(1.6)",
    "transform:scale(1.7);filter:invert(1)",
    "transform:scale(1.7) rotate(3deg);filter:brightness(1.7) saturate(2);"
    "box-shadow:0 0 18px 4px var(--x)",
    "transform:translateY(-10px) scale(1.7);box-shadow:0 12px 14px rgba(0,0,0,.5)",
    "transform:translate(3px,-3px) scale(1.6);filter:hue-rotate(120deg)",
    "transform:scale(2.4) rotate(-12deg);filter:contrast(1.5)",
    "transform:scale(1.6);background:var(--x)",
    "transform:rotate(360deg) scale(2)",
    "transform:scaleX(2.6)",
    "transform:scaleY(2.6)",
    "transform:skewX(30deg) scale(1.5)",
    "transform:translate(-7px,-7px) scale(1.9);box-shadow:0 0 20px rgba(0,0,0,.6)",
    "transform:scale(.4) rotate(45deg)",
    "transform:rotate(-90deg) scale(1.7);filter:saturate(2.5)",
    "transform:scale(1.9);filter:blur(1px) brightness(1.4)",
    "transform:perspective(240px) rotate3d(1,1,0,55deg) scale(1.5)",
]
ACTIVES_T = [
    "transform:rotate(720deg) scale(.6)",
    "transform:scale(.12)",
    "transform:scale(3) rotate(25deg)",
    "transform:scaleX(2.2) scaleY(.4)",
    "transform:rotate(360deg) scale(2.6);background:var(--x)",
    "transform:rotate(-360deg) scale(.3)",
    "transform:scale(4)",
    "transform:skew(40deg,0) scale(1.8)",
    "transform:translateY(22px) scale(.5)",
    "transform:rotate(180deg) scaleX(-1) scale(1.8)",
]
HOVERS_F = [
    "filter:invert(1)",
    "filter:hue-rotate(180deg) saturate(2)",
    "filter:brightness(2.2)",
    "filter:saturate(3.5)",
    "filter:contrast(2.2)",
    "filter:sepia(1) brightness(1.3)",
    "filter:grayscale(1)",
    "filter:drop-shadow(0 0 7px var(--x)) brightness(1.4)",
    "background:var(--x)",
]
ACTIVES_F = [
    "filter:brightness(3.5)",
    "filter:invert(1) hue-rotate(120deg)",
    "filter:contrast(3) saturate(3)",
    "filter:opacity(.1)",
    "filter:sepia(1) brightness(1.6) saturate(2)",
    "filter:drop-shadow(0 0 12px var(--x)) brightness(2)",
]
IDLES_F = [
    ("hue", "from{filter:hue-rotate(0)}to{filter:hue-rotate(360deg)}", 6),
    ("brea", "0%,100%{filter:brightness(.6)}50%{filter:brightness(1.6)}", 3),
    ("blnk", "0%,100%{opacity:1}45%{opacity:1}50%{opacity:.1}55%{opacity:1}", 4),
    ("satp", "0%,100%{filter:saturate(.4)}50%{filter:saturate(2.2)}", 5),
    ("conp", "0%,100%{filter:contrast(.7)}50%{filter:contrast(1.9)}", 4),
    ("glow", "0%,100%{filter:drop-shadow(0 0 0 var(--x))}"
             "50%{filter:drop-shadow(0 0 8px var(--x))}", 3),
]
IDLES_M = [
    ("spin", "from{transform:rotate(0)}to{transform:rotate(360deg)}", 4),
    ("spnr", "from{transform:rotate(0)}to{transform:rotate(-360deg)}", 5),
    ("flt", "0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}", 2),
    ("wob", "0%,100%{transform:rotate(-12deg)}50%{transform:rotate(12deg)}", 1),
    ("puls", "0%,100%{transform:scale(.85)}50%{transform:scale(1.2)}", 2),
    ("orb", "from{transform:rotate(0) translateX(3px) rotate(0)}"
            "to{transform:rotate(360deg) translateX(3px) rotate(-360deg)}", 3),
]

# --- Neighbour wave rules (from wild), NEIGHBOURS ONLY ----------------------
# The hovered/clicked cell is left to its own random effect; these only move the
# cells AROUND it.
NEIGHBOUR_RULES = [
    # WAVE + FLEE: push left/right neighbours away, fading with distance.
    "td:hover + td{transform:translateX(15px) scale(1.6);z-index:15}",
    "td:hover + td + td{transform:translateX(9px) scale(1.3);z-index:14}",
    "td:hover + td + td + td{transform:translateX(4px) scale(1.12)}",
    "td:has(+ td:hover){transform:translateX(-15px) scale(1.6);z-index:15}",
    "td:has(+ td + td:hover){transform:translateX(-9px) scale(1.3);z-index:14}",
    "td:has(+ td + td + td:hover){transform:translateX(-4px) scale(1.12)}",
    "tr:has(+ tr:has(td:hover)) td{filter:brightness(1.5)}",
    "tr:has(td:hover) + tr td{filter:brightness(1.5)}",
    # SHATTER: neighbours fly outward on click.
    "td:active + td{transform:translate(26px,-15px) rotate(32deg);z-index:26}",
    "td:active + td + td{transform:translate(40px,-6px) rotate(20deg);z-index:25}",
    "td:has(+ td:active){transform:translate(-26px,-15px) rotate(-32deg);z-index:26}",
    "td:has(+ td + td:active){transform:translate(-40px,-6px) rotate(-20deg);z-index:25}",
    "tr:has(td:active) + tr td{transform:translateY(22px) scale(.8);"
    "filter:brightness(1.7)}",
    "tr:has(+ tr:has(td:active)) td{transform:translateY(-22px) scale(.8);"
    "filter:brightness(1.7)}",
]


def build_page(n, m, scale, rng):
    palette = make_palette(rng)
    color_cls = [cname(i, "c") for i in range(len(palette))]
    ht_cls = [cname(i, "ht") for i in range(len(HOVERS_T))]
    at_cls = [cname(i, "at") for i in range(len(ACTIVES_T))]
    hf_cls = [cname(i, "hf") for i in range(len(HOVERS_F))]
    af_cls = [cname(i, "af") for i in range(len(ACTIVES_F))]
    idf_cls = [cname(i, "if") for i in range(len(IDLES_F))]
    idm_cls = [cname(i, "im") for i in range(len(IDLES_M))]
    DELAYS = 16
    delay_cls = [cname(i, "d") for i in range(DELAYS)]
    delays = [-round(0.37 * i, 3) for i in range(DELAYS)]

    def pick(pool):
        return pool[rng.randrange(len(pool))]

    rows = ["<table>", "  <tbody>"]
    for _r in range(n):
        cells = []
        for _c in range(m):
            classes = [color_cls[rng.randrange(len(palette))]]
            if rng.random() < MOTION_CHANCE:
                classes.append(pick(idm_cls))
                classes.append(pick(delay_cls))
                classes.append(pick(hf_cls))
                classes.append(pick(af_cls))
            else:
                classes.append(pick(ht_cls))
                classes.append(pick(at_cls))
                if rng.random() < IDLE_CHANCE:
                    classes.append(pick(idf_cls))
                    classes.append(pick(delay_cls))
            cells.append(f'<td class="{" ".join(classes)}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;position:relative;"
        "transform-origin:center;"
        "transition:transform .22s cubic-bezier(.2,.8,.3,1.4),"
        "filter .2s ease,background .3s ease}",
        # The hovered/clicked cell just rises above its disturbed neighbours;
        # its actual effect comes from its own random class (higher specificity).
        "td:hover{z-index:20;cursor:crosshair;transition:transform .09s,filter .09s}",
        "td:active{z-index:30;transition:transform .05s,filter .05s}",
    ]
    for col, cls in zip(palette, color_cls):
        css.append(f".{cls}{{background:{col};--x:{complement(col)}}}")
    for body, cls in zip(HOVERS_T, ht_cls):
        css.append(f".{cls}:hover{{{body}}}")
    for body, cls in zip(ACTIVES_T, at_cls):
        css.append(f".{cls}:active{{{body}}}")
    for body, cls in zip(HOVERS_F, hf_cls):
        css.append(f".{cls}:hover{{{body}}}")
    for body, cls in zip(ACTIVES_F, af_cls):
        css.append(f".{cls}:active{{{body}}}")
    for (name, kf, secs), cls in zip(IDLES_F, idf_cls):
        css.append(f".{cls}{{animation:{name} {secs}s ease-in-out infinite}}")
        css.append(f"@keyframes {name}{{{kf}}}")
    for (name, kf, secs), cls in zip(IDLES_M, idm_cls):
        timing = "linear" if name in ("spin", "spnr", "orb") else "ease-in-out"
        css.append(f".{cls}{{animation:{name} {secs}s {timing} infinite}}")
        css.append(f"@keyframes {name}{{{kf}}}")
    for delay, cls in zip(delays, delay_cls):
        css.append(f".{cls}{{animation-delay:{delay}s}}")
    css.extend(NEIGHBOUR_RULES)
    style_css = "\n".join(css)

    title = cname(rng.randrange(1 << 20))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
{style_css}
</style>
</head>
<body>
{table_html}
</body>
</html>
"""


def minify(html):
    html = re.sub(r"\n\s*", "", html)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 26

    rng = random.Random()
    html = build_page(n, m, scale, rng)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f"hybrid {n}x{m} ({n * m} cells), scale={scale}px | "
          f"per-cell random effects + neighbour wave/flee/shatter")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
