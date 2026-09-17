#!/usr/bin/env python3
"""Two images -> one hover-reveal HTML table (the mouse paints image 2).

Standalone program. Takes two images, squashes both to the same n x m grid, and
builds ONE table showing image 1. Every cell also knows its image-2 color: when
the pointer hovers a cell it snaps to that color, and when the pointer leaves it
fades slowly back to image 1. So the reader "paints" image 2 with their cursor
and it dissolves back — no JavaScript, no animation timeline (the hand is the
clock), no image loading (it's just table cells).

Each cell is a pair (color1, color2). Cells that share a pair share one class and
one :hover rule, so nothing identical is repeated.

Writes:
  - index.html    readable
  - optimal.html  minified

Note on email: :hover survives in Apple Mail and some webmail, but Gmail/Outlook
strip it — there the table simply shows image 1 as a still. It never breaks.

Requires Pillow (`pip install pillow`).

Usage:
    python reveal.py                                   # diddy + tomek, 80x80
    python reveal.py a.png b.jpg 100 100               # custom images and size
    python reveal.py a.png b.jpg 100 100 16            # ...and 16px cells
"""

import re
import sys

from PIL import Image

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Per-cell size in pixels (bigger = bigger picture). Overridable via CLI arg 5.
CELL_PX = 12

# How long a cell takes to fade back to image 1 after the pointer leaves.
FADE_BACK = "25s"
# How fast a cell snaps to image 2 when hovered (small = crisp paint).
PAINT_IN = "0.00s"

# Brush shape — how many cells one hover reveals at once:
#   "cell"  a single cell (precise, but tedious pixel-by-pixel)
#   "row"   the whole row under the pointer (a horizontal squeegee)
#   "band"  the row plus the ones above and below (a thick 3-row band)
# "row"/"band" use each cell's own image-2 color via a CSS variable, so one
# hover reveals many cells at once. "band" needs the modern :has() selector.
BRUSH = "row"

# Palette size per image for quantization (keeps the CSS small). 0 = all colors.
COLORS = 32

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def class_name(index):
    """Turn an integer index into a short, CSS-safe class name (a, b, ..., aa)."""
    base = len(_ALPHABET)
    name = ""
    index += 1  # shift so index 0 -> "a", not ""
    while index > 0:
        index, rem = divmod(index - 1, base)
        name = _ALPHABET[rem] + name
    return name


def image_grid(path, n, m, colors=COLORS):
    """Load `path`, squash to m x n, return an n x m grid of '#rrggbb'."""
    img = Image.open(path).convert("RGB")
    small = img.resize((m, n), Image.LANCZOS)
    if colors and colors > 0:
        small = small.quantize(colors=colors, method=Image.FASTOCTREE).convert("RGB")
    return [
        [f"#{small.getpixel((c, r))[0]:02x}"
         f"{small.getpixel((c, r))[1]:02x}"
         f"{small.getpixel((c, r))[2]:02x}"
         for c in range(m)]
        for r in range(n)
    ]


def build_reveal(grid1, grid2, cell_px):
    """Build one table where hovering a cell reveals its image-2 color.

    Returns (html, n_pairs). Each distinct (color1, color2) pair gets one class
    (base color1, slow fade-back) and one :hover rule (snap to color2).
    """
    pair_to_class = {}    # (color1, color2) -> class name
    rows = ["<table>", "  <tbody>"]
    for row1, row2 in zip(grid1, grid2):
        cells = []
        for c1, c2 in zip(row1, row2):
            pair = (c1, c2)
            if pair not in pair_to_class:
                pair_to_class[pair] = class_name(len(pair_to_class))
            cells.append(f'<td class="{pair_to_class[pair]}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    # The reveal selector decides how many cells one hover lights up. Each cell
    # carries its image-2 color in the CSS variable --x, so a single rule can
    # paint many cells at once, each with its own target color.
    reveal_selectors = {
        "cell": "td:hover",
        "row": "tr:hover td",
        "band": "tr:hover td, tr:hover + tr td, tr:has(+ tr:hover) td",
    }
    reveal = reveal_selectors.get(BRUSH, reveal_selectors["band"])

    css_lines = [
        "table { border-collapse: collapse; }",
        f"td {{ width: {cell_px}px; height: {cell_px}px; padding: 0; "
        f"transition: background {FADE_BACK} ease-out; }}",
        # Reveal rule: the brush shape snaps its cells to their image-2 color.
        f"{reveal} {{ background: var(--x); "
        f"transition: background {PAINT_IN}; }}",
    ]
    # One line per pair: base = image-1 color; --x = image-2 color to reveal.
    for (c1, c2), cls in pair_to_class.items():
        css_lines.append(f".{cls} {{ background: {c1}; --x: {c2}; }}")
    style_css = "\n".join(css_lines)

    n, m = len(grid1), (len(grid1[0]) if grid1 else 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>reveal — {n}x{m}</title>
<style>
{style_css}
</style>
</head>
<body>
{table_html}
</body>
</html>
"""
    return html, len(pair_to_class)


def minify(html):
    """Shrink the HTML: drop whitespace + optional </td>, unquote class, keep </tr>."""
    html = re.sub(r"\n\s*", "", html)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    args = sys.argv[1:]
    img1 = args[0] if len(args) > 0 else "../image_to_html/diddy.png"
    img2 = args[1] if len(args) > 1 else "../image_to_html/tomek.jpg"
    n = int(args[2]) if len(args) > 2 else 80
    m = int(args[3]) if len(args) > 3 else 80
    cell_px = int(args[4]) if len(args) > 4 else CELL_PX

    grid1 = image_grid(img1, n, m)
    grid2 = image_grid(img2, n, m)
    html, n_pairs = build_reveal(grid1, grid2, cell_px)

    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f"{img1} + {img2} -> {n}x{m} ({n * m} cells), {cell_px}px cells, "
          f"brush={BRUSH}, {n_pairs} unique color-pairs")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
