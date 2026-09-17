#!/usr/bin/env python3
"""Text -> animated HTML table: one letter at a time in a fixed field.

Same idea as the GIF version, but pure CSS instead of an image. Draws a fixed
n x m field (default 50 x 50) as one table and shows the message one letter at a
time in the middle: "hello" -> H, E, L, L, O, hard cut between letters, looping.

Each cell is on (letter color) or off (background) in each frame. A cell's whole
on/off sequence across the frames is its pattern; cells with the same pattern
share one class and one @keyframes rule. Hard cuts use `step-end` timing.

Two colors only, so it stays small. NOTE: CSS animation is ignored by email
clients — this file is for viewing in a browser (use textgif.py for email).

Input: field size (n m) and the text. In the text, an underscore '_' means a
space (a blank frame). ASCII only — no Polish characters.

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python textanim.py 6 50 50 hello
    python textanim.py 6 50 50 hello "#00ff88" "#101010"       # letter, bg
    python textanim.py 6 50 50 hello "#00ff88" "#101010" 0.5   # seconds/letter
"""

import re
import sys

import font

READABLE = "index.html"
OPTIMAL = "optimal.html"

LETTER_COLOR = "#00ff88"   # the "x": a letter pixel
BG_COLOR = "#101010"       # the "y": empty background

MARGIN = 3            # least blank cells around the letter when scaling to fit
SECONDS_PER_LETTER = 0.5

BLINK = True          # insert a blank frame between letters (each letter blinks in)
END_PAUSE = 2         # blank frames held at the end before the loop restarts

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


def centered_letter_grid(ch, n, m):
    """Return an n x m grid of 'X'/'.' with `ch` scaled up and centered."""
    g = font.glyph(ch)
    scale = max(1, min((m - 2 * MARGIN) // font.GLYPH_W,
                       (n - 2 * MARGIN) // font.GLYPH_H))
    gw, gh = font.GLYPH_W * scale, font.GLYPH_H * scale
    off_x = (m - gw) // 2
    off_y = (n - gh) // 2

    grid = [["."] * m for _ in range(n)]
    for gr in range(font.GLYPH_H):
        for gc in range(font.GLYPH_W):
            if g[gr][gc] == "X":
                for dy in range(scale):
                    for dx in range(scale):
                        grid[off_y + gr * scale + dy][off_x + gc * scale + dx] = "X"
    return grid


def build_page(text, n, m, cell_px, letter_color, bg_color, sec_per_letter):
    """Build one table where each cell cycles through the letters. Returns html."""
    norm = text.replace("_", " ")
    blank = [["."] * m for _ in range(n)]
    frames = []
    for ch in norm:
        frames.append(centered_letter_grid(ch, n, m))
        if BLINK:
            frames.append(blank)          # blink off between letters
    frames.extend(blank for _ in range(END_PAUSE))   # pause before looping
    n_frames = len(frames)
    duration = n_frames * sec_per_letter

    def color(on):
        return letter_color if on else bg_color

    # Each cell's pattern = its on/off state across every frame.
    pattern_to_class = {}   # pattern tuple -> class name
    rows = ["<table>", "  <tbody>"]
    for r in range(n):
        cells = []
        for c in range(m):
            pattern = tuple(frames[f][r][c] == "X" for f in range(n_frames))
            if pattern not in pattern_to_class:
                pattern_to_class[pattern] = class_name(len(pattern_to_class))
            cells.append(f'<td class="{pattern_to_class[pattern]}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css_lines = [
        "table { border-collapse: collapse; }",
        f"td {{ width: {cell_px}px; height: {cell_px}px; padding: 0; }}",
    ]
    # One rule per pattern. step-end holds each frame's color then jumps (hard
    # cut). A pattern that never changes is just a static background — no anim.
    for pattern, cls in pattern_to_class.items():
        if len(set(pattern)) == 1:
            css_lines.append(f".{cls} {{ background: {color(pattern[0])}; }}")
            continue
        stops = " ".join(
            f"{round(f / n_frames * 100, 2)}% {{ background: {color(on)}; }}"
            for f, on in enumerate(pattern)
        )
        css_lines.append(
            f".{cls} {{ animation: {cls} {duration}s step-end infinite; }}")
        css_lines.append(f"@keyframes {cls} {{ {stops} }}")
    style_css = "\n".join(css_lines)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{class_name((n * 131 + m) & 0xFFFF)}</title>
<style>
{style_css}
</style>
</head>
<body>
{table_html}
</body>
</html>
"""
    return html, len(pattern_to_class), n_frames


def minify(html):
    """Shrink the HTML: drop whitespace + optional </td>, unquote class, keep </tr>."""
    html = re.sub(r"\n\s*", "", html)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    args = sys.argv[1:]
    cell_px = int(args[0]) if len(args) > 0 else 6
    n = int(args[1]) if len(args) > 1 else 50
    m = int(args[2]) if len(args) > 2 else 50
    text = args[3] if len(args) > 3 else "hello"
    letter_color = args[4] if len(args) > 4 else LETTER_COLOR
    bg_color = args[5] if len(args) > 5 else BG_COLOR
    sec = float(args[6]) if len(args) > 6 else SECONDS_PER_LETTER

    html, n_classes, n_frames = build_page(
        text, n, m, cell_px, letter_color, bg_color, sec)

    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f'"{text}" -> field {n}x{m}, {n_frames} frames (blink={BLINK}), '
          f"{n_classes} unique cell patterns, {n_frames * sec:.1f}s loop")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
