#!/usr/bin/env python3
"""Text -> HTML table, drawn from the 5x7 letter base in font.py.

Lays the text out as a pixel grid (X = letter, . = background), then paints
X with the letter color and . with the background color. Only two colors, so
the output is tiny — small enough for email.

Input: a cell size and the text. In the text, an underscore '_' means a space
("spacja to podloga"). ASCII only — no Polish characters.

Writes:
  - index.html    readable
  - optimal.html  minified (two classes only, very small)

Usage:
    python textgen.py 12 hello_world
    python textgen.py 12 hello_world "#00ff88" "#101010"   # letter, background
"""

import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Two colors — both changeable (constants here, or CLI args 3 and 4).
LETTER_COLOR = "#00ff88"   # the "x": where a letter pixel is
BG_COLOR = "#101010"       # the "y": empty background

# Layout, in font pixels.
LETTER_GAP = 1   # blank columns between letters
MARGIN = 1       # blank border of background around the whole text


def text_grid(text):
    """Turn text into a grid of 'X'/'.' rows using the letter base.

    '_' becomes a space. Letters are placed side by side with LETTER_GAP blank
    columns between them, then a MARGIN background border is added all around.
    """
    text = text.replace("_", " ")

    # Build the 7 core rows by concatenating each glyph's rows with a gap.
    core = ["" for _ in range(font.GLYPH_H)]
    gap = "." * LETTER_GAP
    for i, ch in enumerate(text):
        g = font.glyph(ch)
        for row in range(font.GLYPH_H):
            core[row] += g[row]
            if i != len(text) - 1:
                core[row] += gap

    width = len(core[0]) if core else 0

    # Add the background margin.
    grid = []
    blank = "." * (width + 2 * MARGIN)
    for _ in range(MARGIN):
        grid.append(blank)
    for row in core:
        grid.append("." * MARGIN + row + "." * MARGIN)
    for _ in range(MARGIN):
        grid.append(blank)
    return grid


def build_page(grid, cell_px, letter_color, bg_color):
    """Render an X/. grid to an HTML table. X -> class x, . -> class y."""
    rows = ["<table>", "  <tbody>"]
    for line in grid:
        cells = "".join(
            '<td class="x"></td>' if ch == "X" else '<td class="y"></td>'
            for ch in line
        )
        rows.append("    <tr>" + cells + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    style_css = "\n".join([
        "table { border-collapse: collapse; }",
        f"td {{ width: {cell_px}px; height: {cell_px}px; padding: 0; }}",
        f".x {{ background: {letter_color}; }}",
        f".y {{ background: {bg_color}; }}",
    ])

    n, m = len(grid), (len(grid[0]) if grid else 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>text — {n}x{m}</title>
<style>
{style_css}
</style>
</head>
<body>
{table_html}
</body>
</html>
"""
    return html


def minify(html):
    """Shrink the HTML: drop whitespace + optional </td>, unquote class, keep </tr>."""
    html = re.sub(r"\n\s*", "", html)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    args = sys.argv[1:]
    cell_px = int(args[0]) if len(args) > 0 else 12
    text = args[1] if len(args) > 1 else "hello_world"
    letter_color = args[2] if len(args) > 2 else LETTER_COLOR
    bg_color = args[3] if len(args) > 3 else BG_COLOR

    grid = text_grid(text)
    html = build_page(grid, cell_px, letter_color, bg_color)

    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    n, m = len(grid), (len(grid[0]) if grid else 0)
    print(f'"{text}" -> {n}x{m} ({n * m} cells), {cell_px}px cells, '
          f"letter={letter_color} bg={bg_color}")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
