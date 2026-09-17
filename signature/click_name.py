#!/usr/bin/env python3
"""Click-to-reveal name: a colorful mosaic that shows your name while pressed.

At rest it is an abstract colorful bar — the name is invisible (letter cells and
background cells draw from the same random palette). Press/hold the mosaic and
`:active` fires: letter cells snap to a left-to-right gradient and background
cells go dark, so your name appears crisply. Release and it dissolves back.

Pure CSS, no JS. `table:active` matches while any cell inside is pressed, so a
click anywhere on the block reveals the name.

Uses the 5x7 base in font.py. Nondescript <title>.

Input: scale [text] [colorA] [colorB]
    scale = cell px; text uses '_' for space.

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python click_name.py 10
    python click_name.py 10 WIKTOR_PAWLAK
    python click_name.py 12 WP "#6366f1" "#22d3ee"
"""

import random
import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

MARGIN = 1
PALETTE = 40                 # random colors for the resting mosaic
FIELD_DARK = "#0b1220"       # background color shown behind the name on click
COLOR_A = "#8b5cf6"          # reveal gradient start (left)
COLOR_B = "#22d3ee"          # reveal gradient end (right)
SEED = None                  # set an int to reproduce the resting mosaic

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cname(index, prefix=""):
    base = len(_ALPHABET)
    name = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, base)
        name = _ALPHABET[rem] + name
    return prefix + name


def lerp_hex(a, b, t):
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return f"#{round(ar+(br-ar)*t):02x}{round(ag+(bg-ag)*t):02x}{round(ab+(bb-ab)*t):02x}"


def text_grid(text):
    """Word -> grid of 'X'/'.' rows with a margin all around."""
    text = text.replace("_", " ")
    core = ["" for _ in range(font.GLYPH_H)]
    for i, ch in enumerate(text):
        g = font.glyph(ch)
        for row in range(font.GLYPH_H):
            core[row] += g[row]
            if i != len(text) - 1:
                core[row] += "."
    width = len(core[0]) if core else 0
    grid = []
    blank = "." * (width + 2 * MARGIN)
    for _ in range(MARGIN):
        grid.append(blank)
    for row in core:
        grid.append("." * MARGIN + row + "." * MARGIN)
    for _ in range(MARGIN):
        grid.append(blank)
    return grid


def build_page(scale, text, color_a, color_b, rng):
    grid = text_grid(text)
    n, m = len(grid), (len(grid[0]) if grid else 0)

    palette = [f"#{rng.randint(0, 0xFFFFFF):06x}" for _ in range(PALETTE)]
    pal_cls = [cname(i, "p") for i in range(PALETTE)]
    grad_colors = [lerp_hex(color_a, color_b, c / max(1, m - 1)) for c in range(m)]
    grad_cls = [cname(c, "g") for c in range(m)]

    rows = ["<table>", "  <tbody>"]
    for r in range(n):
        cells = []
        for c in range(m):
            rest = pal_cls[rng.randrange(PALETTE)]     # random resting color
            if grid[r][c] == "X":
                # letter: rest color now, gradient color when pressed
                cells.append(f'<td class="l {rest} {grad_cls[c]}"></td>')
            else:
                cells.append(f'<td class="b {rest}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse;cursor:pointer}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;"
        "transition:background .25s ease}",
        # While pressed: background cells go dark, letters take their gradient.
        f"table:active .b{{background:{FIELD_DARK}}}",
    ]
    for col, cls in zip(palette, pal_cls):
        css.append(f".{cls}{{background:{col}}}")
    # Reveal gradient (only applies under table:active, so the name is hidden
    # at rest). Higher specificity than the resting palette class, so it wins.
    for col, cls in zip(grad_colors, grad_cls):
        css.append(f"table:active .{cls}{{background:{col}}}")
    style_css = "\n".join(css)

    title = cname((n * 131 + m) & 0xFFFF)
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
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)   # single-token only
    html = html.replace("</td>", "")
    return html


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    text = sys.argv[2] if len(sys.argv) > 2 else "WIKTOR_PAWLAK"
    color_a = sys.argv[3] if len(sys.argv) > 3 else COLOR_A
    color_b = sys.argv[4] if len(sys.argv) > 4 else COLOR_B

    rng = random.Random(SEED)
    html = build_page(scale, text, color_a, color_b, rng)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f'click-to-reveal "{text}" scale={scale}px')
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
