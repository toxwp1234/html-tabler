#!/usr/bin/env python3
"""Two images -> one animated HTML table (per-cell color animation "video").

Standalone program. Takes two images, squashes both to the same n x m grid, and
builds ONE table where every cell animates its own background color with pure-CSS
@keyframes, cycling between its image-1 color and its image-2 color:

    0-40%   image 1 color
    40-50%  fade  1 -> 2
    50-92%  image 2 color
    92-100% fade  2 -> 1   (then loops)

Each cell is described by a pair (color1, color2). Cells that share the same pair
share one class + one @keyframes rule, so identical animations are not repeated.

No JavaScript. This is NOT built to fit in an email (CSS animation is ignored by
mail clients) — it is for viewing in a browser.

Both images are scaled to exactly n x m, so any two sizes work; pick n and m
near the images' shared proportions to avoid distortion.

Requires Pillow (`pip install pillow`).

Usage:
    python animate.py                                  # diddy + tomek, 80 x 80
    python animate.py a.png b.jpg 100 100              # custom images and size
    python animate.py a.png b.jpg 100 100 6            # ...and a 6s cycle
"""

import re
import sys

from PIL import Image

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Per-cell size in pixels.
CELL_X = 6
CELL_Y = 6

# Default seconds for one full cycle (image1 -> image2 -> image1).
DURATION = 8

# Palette size per image for quantization (keeps the CSS small). 0 = all colors.
COLORS = 96

# Hard cut, no fade: image 1 fills 0..SWITCH% of the cycle, image 2 the rest.
# The switch is a near-instant jump (SWITCH_EDGE% wide) and the loop wraps
# image 2 -> image 1 instantly, so neither direction shows a transition.
SWITCH = 50
SWITCH_EDGE = 0.1

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


def build_animation(grid1, grid2, duration):
    """Build one table where each cell animates color1 -> color2 -> color1.

    Returns (html, n_pairs). Each distinct (color1, color2) pair gets one class
    and one @keyframes rule; every cell with that pair reuses them.
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

    css_lines = [
        "table { border-collapse: collapse; }",
        f"td {{ width: {CELL_X}px; height: {CELL_Y}px; padding: 0; }}",
    ]
    # One animation + one keyframes rule per unique color pair. The class name
    # doubles as the keyframes name (they live in separate namespaces).
    # Hard cut: hold c1 flat to SWITCH%, jump to c2 across SWITCH_EDGE%, hold c2
    # to 100%; the loop wraps 100% -> 0% (c2 -> c1) as an instant jump too.
    for (c1, c2), cls in pair_to_class.items():
        stops = (
            f"0% {{ background: {c1}; }} "
            f"{SWITCH}% {{ background: {c1}; }} "
            f"{SWITCH + SWITCH_EDGE}% {{ background: {c2}; }} "
            f"100% {{ background: {c2}; }}"
        )
        css_lines.append(
            f".{cls} {{ animation: {cls} {duration}s linear infinite; }}")
        css_lines.append(f"@keyframes {cls} {{ {stops} }}")
    style_css = "\n".join(css_lines)

    n, m = len(grid1), (len(grid1[0]) if grid1 else 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>video — {n}x{m}</title>
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
    """Shrink the HTML for a compact optimal.html (same rules as the other tools).

    Drops readability whitespace and the optional </td> tag, and unquotes
    letter-only class values. Keeps </tr> so rows still break. Note: CSS
    animation is ignored by email clients, so this file is small but not
    actually email-usable — it mirrors the other projects' optimal.html output.
    """
    html = re.sub(r"\n\s*", "", html)             # drop newlines + indentation
    html = re.sub(r">\s+<", "><", html)           # collapse whitespace between tags
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)  # unquote class
    html = html.replace("</td>", "")              # drop optional per-cell close
    return html


def main():
    args = sys.argv[1:]
    img1 = args[0] if len(args) > 0 else "../image_to_html/diddy.png"
    img2 = args[1] if len(args) > 1 else "../image_to_html/tomek.jpg"
    n = int(args[2]) if len(args) > 2 else 80
    m = int(args[3]) if len(args) > 3 else 80
    duration = float(args[4]) if len(args) > 4 else DURATION

    grid1 = image_grid(img1, n, m)
    grid2 = image_grid(img2, n, m)
    html, n_pairs = build_animation(grid1, grid2, duration)

    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f"{img1} + {img2} -> {n}x{m} ({n * m} cells), "
          f"{n_pairs} unique color-pairs, cycle={duration}s")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
