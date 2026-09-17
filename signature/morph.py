#!/usr/bin/env python3
"""Morphing wordmark: text A at rest, text B on hover.

Shows text A (default "WIKTOR PAWLAK") as a clean gradient wordmark. Hover it and
it morphs into text B (default the phone number) — same style, letters rearrange.
Move away and it returns. Pure CSS, no JS.

Each cell knows whether it is lit in frame A and in frame B:
  * lit in A only  -> shown at rest, hidden on hover
  * lit in B only  -> hidden at rest, shown on hover
  * lit in both    -> always shown
Both texts are centered in one shared grid, so any two lengths line up.

Uses the 5x7 base in font.py. Transparent background, so it floats cleanly on
the email. Nondescript <title>.

Input: scale [textA] [textB] [colorA] [colorB]
    scale = cell px; '_' = space in either text.

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python morph.py 10
    python morph.py 10 WIKTOR_PAWLAK 889_519_397
    python morph.py 10 WIKTOR_PAWLAK PAWLAK_WIKTOR "#6366f1" "#22d3ee"
"""

import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

MARGIN = 1
COLOR_A = "#6366f1"   # gradient start (left)
COLOR_B = "#22d3ee"   # gradient end (right)

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


def core(text):
    """7 rows of 'X'/'.' for the text (glyphs side by side, 1-col gaps)."""
    text = text.replace("_", " ")
    rows = ["" for _ in range(font.GLYPH_H)]
    for i, ch in enumerate(text):
        g = font.glyph(ch)
        for r in range(font.GLYPH_H):
            rows[r] += g[r]
            if i != len(text) - 1:
                rows[r] += "."
    return rows


def pad_center(rows, target_w):
    """Center each row within target_w columns."""
    w = len(rows[0]) if rows else 0
    left = (target_w - w) // 2
    right = target_w - w - left
    return ["." * left + row + "." * right for row in rows]


def build_page(scale, text_a, text_b, color_a, color_b):
    a_core, b_core = core(text_a), core(text_b)
    target_w = max(len(a_core[0]), len(b_core[0]))
    a_core = pad_center(a_core, target_w)
    b_core = pad_center(b_core, target_w)

    # Full grids with a margin border.
    def framed(rows):
        blank = "." * (target_w + 2 * MARGIN)
        out = [blank] * MARGIN
        out += ["." * MARGIN + row + "." * MARGIN for row in rows]
        out += [blank] * MARGIN
        return out

    A, B = framed(a_core), framed(b_core)
    n, m = len(A), len(A[0])

    col_colors = [lerp_hex(color_a, color_b, c / max(1, m - 1)) for c in range(m)]
    col_cls = [cname(c, "k") for c in range(m)]

    rows = ["<table>", "  <tbody>"]
    for r in range(n):
        cells = []
        for c in range(m):
            on_a, on_b = A[r][c] == "X", B[r][c] == "X"
            if not on_a and not on_b:
                cells.append('<td class="e"></td>')
                continue
            marks = []
            if on_a:
                marks.append("a")
            if on_b:
                marks.append("b")
            marks.append(col_cls[c])
            cells.append(f'<td class="{" ".join(marks)}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;background:transparent;"
        "transition:background .35s ease}",
        # Rest: frame A cells are lit with their column color (--col).
        ".a{background:var(--col)}",
        # Hover: hide A, then light B (B rule after A, so 'both' cells stay lit).
        "table:hover .a{background:transparent}",
        "table:hover .b{background:var(--col)}",
    ]
    for col, cls in zip(col_colors, col_cls):
        css.append(f".{cls}{{--col:{col}}}")
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
    text_a = sys.argv[2] if len(sys.argv) > 2 else "WIKTOR_PAWLAK"
    text_b = sys.argv[3] if len(sys.argv) > 3 else "889_519_397"
    color_a = sys.argv[4] if len(sys.argv) > 4 else COLOR_A
    color_b = sys.argv[5] if len(sys.argv) > 5 else COLOR_B

    html = build_page(scale, text_a, text_b, color_a, color_b)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f'morph "{text_a}" -> (hover) "{text_b}", scale={scale}px')
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
