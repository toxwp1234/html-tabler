#!/usr/bin/env python3
"""Hidden-signature mosaic: initials woven into a colorful grid.

Looks like abstract color art, but the letters (default "WP") are hidden in it:
letter cells use vivid colors, background cells use muted/dark ones, so the
shape is faintly there if you look — even statically (e.g. in Gmail). Then, in
any client that supports :hover (browser, Apple Mail), moving the mouse over the
mosaic makes the letters LEAP out: letter cells brighten and swell, background
cells fade to grey. The "wow, there's a message hidden in it" moment.

Uses the 5x7 letter base in font.py. Colors are only two palettes, so the file
stays small.

The page <title> is deliberately nondescript.

Input: n m scale [text]   (scale = cell px; text default "WP", '_' = space)

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python signature.py 40 60 10
    python signature.py 40 90 10 WIKTOR
"""

import colorsys
import random
import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

MARGIN = 2
PALETTE = 40          # colors per palette (letter / background)
SEED = None           # set an int to reproduce a favourite mosaic

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cname(index, prefix=""):
    base = len(_ALPHABET)
    name = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, base)
        name = _ALPHABET[rem] + name
    return prefix + name


def hls_hex(h, l, s):
    return "#{:02x}{:02x}{:02x}".format(
        *(round(v * 255) for v in colorsys.hls_to_rgb(h, l, s)))


def make_palettes(rng):
    """Two palettes: vivid (letters) and muted/dark (background)."""
    letter = [hls_hex(rng.random(), rng.uniform(0.5, 0.66), rng.uniform(0.75, 1.0))
              for _ in range(PALETTE)]
    bg = [hls_hex(rng.random(), rng.uniform(0.25, 0.42), rng.uniform(0.3, 0.6))
          for _ in range(PALETTE)]
    return letter, bg


def letter_mask(text, n, m):
    """Boolean n x m mask: True where a cell is part of the (scaled, centered) word."""
    text = text.replace("_", " ")
    gap = 1
    word_w = len(text) * font.GLYPH_W + (len(text) - 1) * gap
    word_h = font.GLYPH_H
    scale = max(1, min((m - 2 * MARGIN) // max(1, word_w),
                       (n - 2 * MARGIN) // word_h))
    gw, gh = word_w * scale, word_h * scale
    off_x = (m - gw) // 2
    off_y = (n - gh) // 2

    mask = [[False] * m for _ in range(n)]
    x = off_x
    for ch in text:
        g = font.glyph(ch)
        for gr in range(font.GLYPH_H):
            for gc in range(font.GLYPH_W):
                if g[gr][gc] == "X":
                    for dy in range(scale):
                        for dx in range(scale):
                            yy, xx = off_y + gr * scale + dy, x + gc * scale + dx
                            if 0 <= yy < n and 0 <= xx < m:
                                mask[yy][xx] = True
        x += (font.GLYPH_W + gap) * scale
    return mask


def build_page(n, m, scale, text, rng):
    letter_pal, bg_pal = make_palettes(rng)
    letter_cls = [cname(i, "l") for i in range(PALETTE)]
    bg_cls = [cname(i, "b") for i in range(PALETTE)]
    mask = letter_mask(text, n, m)

    rows = ["<table>", "  <tbody>"]
    for r in range(n):
        cells = []
        for c in range(m):
            if mask[r][c]:
                cls = letter_cls[rng.randrange(PALETTE)]
                cells.append(f'<td class="l {cls}"></td>')
            else:
                cls = bg_cls[rng.randrange(PALETTE)]
                cells.append(f'<td class="b {cls}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css = [
        "table{border-collapse:collapse}",
        f"td{{width:{scale}px;height:{scale}px;padding:0;position:relative;"
        "transition:filter .4s ease,opacity .4s ease,transform .4s ease}",
        # The reveal: hovering anywhere on the mosaic brightens the letters and
        # fades the background, so the hidden word jumps out.
        "table:hover .l{filter:brightness(1.5) saturate(1.5);transform:scale(1.08);"
        "z-index:2}",
        "table:hover .b{opacity:.12;filter:grayscale(1)}",
        "td:hover{cursor:crosshair}",
    ]
    for col, cls in zip(letter_pal, letter_cls):
        css.append(f".{cls}{{background:{col}}}")
    for col, cls in zip(bg_pal, bg_cls):
        css.append(f".{cls}{{background:{col}}}")
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
    # Cells carry two classes ("l xx"), so keep quotes — only single tokens unquote.
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    text = sys.argv[4] if len(sys.argv) > 4 else "WP"

    rng = random.Random(SEED)
    html = build_page(n, m, scale, text, rng)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f'hidden "{text}" in {n}x{m} mosaic ({n * m} cells), scale={scale}px')
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
