#!/usr/bin/env python3
"""Random colored-square generator -> HTML table.

Standalone program. Builds an n x m table of randomly colored cells and writes:
  - index.html    readable, with newlines and indentation (for you to read)
  - optimal.html  the same HTML run through minify() (compact, for email)

Every unique color is defined once as a short CSS class in <style>; each cell
only references that class (<td class="xx">), which keeps the file small.

Usage:
    python generate.py            # default size, current COLOR_MODE
    python generate.py 10 16      # n=10 rows, m=16 cols
"""

import colorsys
import random
import re
import sys

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Per-cell size in pixels. CELL_X = width, CELL_Y = height.
CELL_X = 100
CELL_Y = 100
BORDER_PX = 0

# Random palette:
#   "rainbow" -> fully random colors
#   "mono"    -> random shades within one hue family (BASE_HUE)
COLOR_MODE = "mono"
# Base hue in degrees (0=red, 120=green, 240=blue). None = fresh random each run.
BASE_HUE = 210

# Alphabet for short class names: a, b, ..., z, A, ..., Z, aa, ab, ...
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


def rgb_to_hex(r, g, b):
    """(r, g, b) floats in 0..1 -> '#rrggbb'."""
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def rainbow_color():
    """Return a fully random #rrggbb hex color."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def mono_color(base_hue):
    """Return a random shade within a single hue family."""
    h = (base_hue % 360) / 360.0
    s = random.uniform(0.45, 0.95)
    l = random.uniform(0.20, 0.80)
    return rgb_to_hex(*colorsys.hls_to_rgb(h, l, s))


def random_grid(n, m):
    """Build an n x m grid of colors according to COLOR_MODE."""
    hue = BASE_HUE if BASE_HUE is not None else random.uniform(0, 360)
    return [
        [mono_color(hue) if COLOR_MODE == "mono" else rainbow_color()
         for _ in range(m)]
        for _ in range(n)
    ]


def complement(hex_color):
    """Return the complementary color: the hue rotated 180° on the wheel."""
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + 0.5) % 1.0
    return rgb_to_hex(*colorsys.hls_to_rgb(h, l, s))


def build_table(grid):
    """Render a color grid to (style_css, table_html, n_colors)."""
    color_to_class = {}   # color hex -> class name
    rows = ["<table>", "  <tbody>"]
    for grid_row in grid:
        cells = []
        for color in grid_row:
            if color not in color_to_class:
                color_to_class[color] = class_name(len(color_to_class))
            cells.append(f'<td class="{color_to_class[color]}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css_lines = [
        "table { border-collapse: collapse; }",
        f"td {{ width: {CELL_X}px; height: {CELL_Y}px; padding: 0; "
        f"border: {BORDER_PX}px solid #e5e7eb; position: relative; "
        "transition: background 0.18s ease, transform 0.12s ease; }",
        "td:hover { transform: scale(1.6); z-index: 2; "
        "box-shadow: 0 0 8px rgba(0,0,0,0.45); cursor: crosshair; }",
        "td:active { transform: scale(5); z-index: 4; "
        "filter: brightness(1.5) saturate(1.6); "
        "box-shadow: 0 0 18px 4px rgba(0,0,0,0.55); "
        "transition: transform 0.06s ease, filter 0.06s ease; }",
    ]
    for color, cls in color_to_class.items():
        css_lines.append(f".{cls} {{ background: {color}; }}")
        css_lines.append(f".{cls}:hover {{ background: {complement(color)}; }}")
    style_css = "\n".join(css_lines)

    return style_css, table_html, len(color_to_class)


def build_page_from_grid(grid):
    """Build a readable HTML document from a color grid. Returns (html, n_colors)."""
    n, m = len(grid), (len(grid[0]) if grid else 0)
    style_css, table, n_colors = build_table(grid)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Random Squares — {n}x{m}</title>
<style>
{style_css}
</style>
</head>
<body>
{table}
</body>
</html>
"""
    return html, n_colors


def minify(html):
    """Strip readability-only whitespace (safe: cells are empty, CSS unaffected)."""
    html = re.sub(r"\n\s*", "", html)      # drop newlines + following indentation
    html = re.sub(r">\s+<", "><", html)    # collapse whitespace between tags
    return html


def write_pages(grid):
    """Write index.html (readable) and optimal.html (minified) from a grid."""
    html, n_colors = build_page_from_grid(grid)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)
    return html, optimal_html, n_colors


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 88
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 88
    if n < 1 or m < 1:
        sys.exit("n and m must both be >= 1")

    grid = random_grid(n, m)
    html, optimal_html, n_colors = write_pages(grid)

    print(f"{n} rows x {m} cols ({n * m} cells), {n_colors} unique colors, "
          f"mode={COLOR_MODE}")
    print(f"  {READABLE}: {len(html)} bytes (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html)} bytes (minified)")


if __name__ == "__main__":
    main()
