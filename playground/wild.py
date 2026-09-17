#!/usr/bin/env python3
"""n x m table with WILD neighbor-reacting effects (pure CSS, no JS).

Unlike playground.py (each cell reacts alone), here a cell's hover/click ripples
out to its NEIGHBOURS using sibling combinators (+) and the :has() relative
selector:

  * WAVE + FLEE (hover): the hovered cell pops; its left/right neighbours are
    shoved away and scaled (a parting ripple); the rows above and below glow.
  * SHATTER (click): neighbours fly outward with rotation, like glass shards.

These selectors are heavy for the browser on big grids (:has re-evaluates a lot),
so keep n*m modest. If it stutters, shrink the grid or drop a rule.

The page <title> is deliberately nondescript. For a browser only (a toy).

Input: n m scale  (scale = cell size in px)

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python wild.py 18 18 28
"""

import colorsys
import random
import re
import sys

READABLE = "index.html"
OPTIMAL = "optimal.html"

COLOR_MODE = "rainbow"     # "rainbow" or "mono"
BASE_HUE = 200
PALETTE = 40
IDLE_CHANCE = 0.5          # light filter idle on some cells

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


# Light idle animations (filter/opacity only, so they never fight the
# transform-based neighbour effects). (name, keyframes, seconds)
IDLES = [
    ("hue", "from{filter:hue-rotate(0)}to{filter:hue-rotate(360deg)}", 7),
    ("brea", "0%,100%{filter:brightness(.7)}50%{filter:brightness(1.5)}", 4),
    ("blnk", "0%,100%{opacity:1}48%{opacity:1}52%{opacity:.2}56%{opacity:1}", 5),
]

# The wild neighbour rules. Order matters: hover rules first, then click rules,
# so that while a cell is pressed the shatter transform wins over any wave.
WILD_RULES = [
    # --- WAVE + FLEE (hover) -------------------------------------------------
    # Hovered cell itself.
    "td:hover{transform:scale(2.6);z-index:20;"
    "box-shadow:0 0 16px rgba(0,0,0,.55)}",
    # Right-hand neighbours: shoved right + scaled, fading with distance.
    "td:hover + td{transform:translateX(16px) scale(1.7);z-index:15}",
    "td:hover + td + td{transform:translateX(10px) scale(1.35);z-index:14}",
    "td:hover + td + td + td{transform:translateX(5px) scale(1.15)}",
    # Left-hand neighbours (reached with :has looking forward to the hover).
    "td:has(+ td:hover){transform:translateX(-16px) scale(1.7);z-index:15}",
    "td:has(+ td + td:hover){transform:translateX(-10px) scale(1.35);z-index:14}",
    "td:has(+ td + td + td:hover){transform:translateX(-5px) scale(1.15)}",
    # Rows directly above and below the hovered row glow and swell.
    "tr:has(+ tr:has(td:hover)) td{filter:brightness(1.5);transform:scale(1.15)}",
    "tr:has(td:hover) + tr td{filter:brightness(1.5);transform:scale(1.15)}",
    # --- SHATTER (click) ----------------------------------------------------
    "td:active{transform:scale(.3) rotate(30deg);z-index:30;"
    "filter:brightness(1.6)}",
    "td:active + td{transform:translate(28px,-16px) rotate(35deg);z-index:26}",
    "td:active + td + td{transform:translate(44px,-6px) rotate(22deg);z-index:25}",
    "td:has(+ td:active){transform:translate(-28px,-16px) rotate(-35deg);z-index:26}",
    "td:has(+ td + td:active){transform:translate(-44px,-6px) rotate(-22deg);z-index:25}",
    "tr:has(td:active) + tr td{transform:translateY(24px) scale(.8);"
    "filter:brightness(1.7)}",
    "tr:has(+ tr:has(td:active)) td{transform:translateY(-24px) scale(.8);"
    "filter:brightness(1.7)}",
]


def build_page(n, m, scale, rng):
    palette = make_palette(rng)
    color_cls = [cname(i, "c") for i in range(len(palette))]
    idle_cls = [cname(i, "i") for i in range(len(IDLES))]
    DELAYS = 12
    delay_cls = [cname(i, "d") for i in range(DELAYS)]
    delays = [-round(0.5 * i, 3) for i in range(DELAYS)]

    rows = ["<table>", "  <tbody>"]
    for _r in range(n):
        cells = []
        for _c in range(m):
            classes = [color_cls[rng.randrange(len(palette))]]
            if rng.random() < IDLE_CHANCE:
                classes.append(idle_cls[rng.randrange(len(IDLES))])
                classes.append(delay_cls[rng.randrange(DELAYS)])
            cells.append(f'<td class="{" ".join(classes)}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;position:relative;"
        "transform-origin:center;"
        "transition:transform .25s cubic-bezier(.2,.8,.3,1.4),"
        "filter .25s ease,background .3s ease}",
        "td:hover{cursor:crosshair}",
    ]
    for col, cls in zip(palette, color_cls):
        css.append(f".{cls}{{background:{col}}}")
    for (name, kf, secs), cls in zip(IDLES, idle_cls):
        css.append(f".{cls}{{animation:{name} {secs}s ease-in-out infinite}}")
        css.append(f"@keyframes {name}{{{kf}}}")
    for delay, cls in zip(delays, delay_cls):
        css.append(f".{cls}{{animation-delay:{delay}s}}")
    css.extend(WILD_RULES)
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 28

    rng = random.Random()
    html = build_page(n, m, scale, rng)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f"wild {n}x{m} ({n * m} cells), scale={scale}px | "
          f"wave + flee + shatter (neighbour effects via :has)")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
