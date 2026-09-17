#!/usr/bin/env python3
"""Image -> HTML table converter.

Standalone program. Loads an image, squashes it to an n x m grid of colors, and
writes an HTML table where each cell is one pixel:
  - index.html    readable, with newlines and indentation (for you to read)
  - optimal.html  the same HTML run through minify() (compact, for email)

Every unique color is defined once as a short CSS class in <style>; each cell
only references that class (<td class="xx">), which keeps the file small when
colors repeat.

Requires Pillow (`pip install pillow`).

Usage:
    python transform.py                    # image.jpg -> 88 x 88
    python transform.py image.png 40 60    # custom file, n=40 rows, m=60 cols
"""

import os
import re
import sys

from PIL import Image

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Per-cell size in pixels — small, so the picture reads as pixels, not a grid.
CELL_X = 8
CELL_Y = 8
BORDER_PX = 0

# Palette size for color quantization. Fewer colors -> fewer CSS rules and more
# cells share a class -> much smaller file. 0 = keep all original colors.
# Gmail clips messages over ~102 KB, so keep optimal.html under that.
COLORS = 64

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


def transform_image(path, n, m, colors=COLORS):
    """Load `path`, squash it to m x n, return an n x m grid of '#rrggbb'.

    n = rows (height in cells), m = cols (width in cells). Aspect ratio is not
    preserved — the image is stretched to fill the grid exactly, so pick n and m
    close to the picture's proportions to avoid distortion.

    colors: if > 0, reduce the image to that many colors (quantization) so the
    output HTML is much smaller. 0 keeps every original color.
    """
    img = Image.open(path).convert("RGB")
    # Resize to (width=m, height=n). LANCZOS averages the source region each
    # output pixel covers, giving one representative color per cell.
    small = img.resize((m, n), Image.LANCZOS)
    if colors and colors > 0:
        # Collapse the palette; convert back to RGB so getpixel yields tuples.
        small = small.quantize(colors=colors, method=Image.FASTOCTREE).convert("RGB")

    grid = []
    for row in range(n):
        cells = []
        for col in range(m):
            r, g, b = small.getpixel((col, row))
            cells.append(f"#{r:02x}{g:02x}{b:02x}")
        grid.append(cells)
    return grid


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
        f"border: {BORDER_PX}px solid #e5e7eb; }}",
    ]
    for color, cls in color_to_class.items():
        css_lines.append(f".{cls} {{ background: {color}; }}")
    style_css = "\n".join(css_lines)

    return style_css, table_html, len(color_to_class)


def build_page_from_grid(grid, title):
    """Build a readable HTML document from a color grid. Returns (html, n_colors)."""
    style_css, table, n_colors = build_table(grid)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
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
    """Shrink the HTML as far as still renders correctly, for small emails.

    Beyond stripping whitespace, this drops the optional </td> tag (the big win:
    one per cell) and unquotes letter-only class values, so <td class="a"></td>
    becomes <td class=a>. It KEEPS </tr>: email clients rely on it to break rows,
    and without it every cell collapses onto a single line. Dropping </tr> would
    only save a few bytes per row anyway, so it is never worth the risk.
    """
    html = re.sub(r"\n\s*", "", html)             # drop newlines + indentation
    html = re.sub(r">\s+<", "><", html)           # collapse whitespace between tags
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)  # unquote class
    html = html.replace("</td>", "")              # drop optional per-cell close
    return html


def write_pages(grid, title):
    """Write index.html (readable) and optimal.html (minified) from a grid."""
    html, n_colors = build_page_from_grid(grid, title)
    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)
    return html, optimal_html, n_colors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "diddy.png"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 88
    m = int(sys.argv[3]) if len(sys.argv) > 3 else 88

    grid = transform_image(path, n, m)
    # Page title = the image's name without its extension (e.g. diddy.png -> diddy).
    title = os.path.splitext(os.path.basename(path))[0]
    html, optimal_html, n_colors = write_pages(grid, title)

    opt_kb = len(optimal_html.encode("utf-8")) / 1024
    gmail = "OK for Gmail" if opt_kb < 100 else "TOO BIG — Gmail will clip (>100 KB)"
    print(f"{path} -> {n} rows x {m} cols ({n * m} cells), "
          f"{n_colors} unique colors (COLORS={COLORS})")
    print(f"  {READABLE}: {len(html)} bytes (readable)")
    print(f"  {OPTIMAL}: {opt_kb:.1f} KB (minified) — {gmail}")


if __name__ == "__main__":
    main()
