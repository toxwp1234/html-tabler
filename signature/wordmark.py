#!/usr/bin/env python3
"""Elegant wordmark: your name in a pixel font, gradient-tinted, with a shimmer.

A restrained, professional signature decoration. The text (default "WIKTOR
PAWLAK") is drawn in the 5x7 pixel font. Letter cells are tinted with a smooth
left-to-right gradient between two accent colors; background cells are
transparent, so the wordmark floats cleanly on the email's own background.

A diagonal highlight sweeps across the letters forever (each cell brightens with
a delay based on its row+col), like the sheen on a premium card. Monochrome-ish
and geometric — no rainbow noise.

Uses the 5x7 base in font.py. Nondescript <title>.

Input: scale [text] [colorA] [colorB]
    scale = cell px; text uses '_' for space.

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python wordmark.py 8
    python wordmark.py 8 WIKTOR_PAWLAK
    python wordmark.py 10 WP "#6366f1" "#22d3ee"
"""

import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

MARGIN = 1
COLOR_A = "#6366f1"   # gradient start (left)
COLOR_B = "#22d3ee"   # gradient end (right)

SWEEP_SECONDS = 3.0   # time for the shimmer to cross once
SWEEP_PERIOD = 26     # diagonal wavelength in cells (distinct delay buckets)

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
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def text_grid(text):
    """Word -> grid of 'X'/'.' rows, letters side by side, with a margin."""
    text = text.replace("_", " ")
    core = ["" for _ in range(font.GLYPH_H)]
    for i, ch in enumerate(text):
        g = font.glyph(ch)
        for row in range(font.GLYPH_H):
            core[row] += g[row]
            if i != len(text) - 1:
                core[row] += "."      # 1-col gap
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


def build_page(scale, text, color_a, color_b):
    grid = text_grid(text)
    n, m = len(grid), (len(grid[0]) if grid else 0)

    # Column gradient: one color per column.
    col_colors = [lerp_hex(color_a, color_b, c / max(1, m - 1)) for c in range(m)]
    col_cls = [cname(c, "g") for c in range(m)]

    # Diagonal shimmer: delay bucket per cell from (row+col) mod period.
    delay_cls = [cname(i, "d") for i in range(SWEEP_PERIOD)]
    delays = [-round(SWEEP_SECONDS * i / SWEEP_PERIOD, 3) for i in range(SWEEP_PERIOD)]

    rows = ["<table>", "  <tbody>"]
    for r in range(n):
        cells = []
        for c in range(m):
            if grid[r][c] == "X":
                d = delay_cls[(r + c) % SWEEP_PERIOD]
                cells.append(f'<td class="k {col_cls[c]} {d}"></td>')
            else:
                cells.append('<td class="e"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;background:transparent}}",
        # Letter cells run the shimmer; the highlight is a brief brightness spike.
        f".k{{animation:shine {SWEEP_SECONDS}s ease-in-out infinite}}",
        "@keyframes shine{0%,100%{filter:brightness(1)}"
        "6%{filter:brightness(1.9)}14%{filter:brightness(1)}}",
    ]
    for col, cls in zip(col_colors, col_cls):
        css.append(f".{cls}{{background:{col}}}")
    for delay, cls in zip(delays, delay_cls):
        css.append(f".{cls}{{animation-delay:{delay}s}}")
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
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    text = sys.argv[2] if len(sys.argv) > 2 else "WIKTOR_PAWLAK"
    color_a = sys.argv[3] if len(sys.argv) > 3 else COLOR_A
    color_b = sys.argv[4] if len(sys.argv) > 4 else COLOR_B

    html = build_page(scale, text, color_a, color_b)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f'wordmark "{text}" scale={scale}px, gradient {color_a} -> {color_b}')
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
