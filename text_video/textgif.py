#!/usr/bin/env python3
"""Text -> animated GIF: one letter at a time, centered in a fixed field.

Draws a fixed n x m field (default 50 x 50) and shows the message one letter at
a time in the middle of it: "hello" -> H, E, L, L, O, each on its own frame,
then loops. The letter is scaled up to fill the field.

Two colors only, so the GIF is tiny — and unlike CSS animation, an animated GIF
actually plays in every email client once images are shown.

Input: field size (n m) and the text. In the text, an underscore '_' means a
space (a blank frame). ASCII only — no Polish characters.

Writes:
  - text.gif

Requires Pillow (`pip install pillow`).

Usage:
    python textgif.py 6 50 50 hello
    python textgif.py 6 50 50 hello "#00ff88" "#101010"        # letter, bg
    python textgif.py 6 50 50 hello "#00ff88" "#101010" 500    # ms per letter
"""

import os
import sys

from PIL import Image

import font

OUTPUT = "text.gif"

LETTER_COLOR = "#00ff88"   # the "x": a letter pixel
BG_COLOR = "#101010"       # the "y": empty background

MARGIN = 3       # least blank cells kept around the letter when scaling to fit
STEP_MS = 500    # time each letter stays on screen


def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def centered_letter_grid(ch, n, m):
    """Return an n x m grid of 'X'/'.' with `ch` scaled up and centered."""
    g = font.glyph(ch)
    # Biggest whole-number scale that still leaves the margin on every side.
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
    return ["".join(row) for row in grid]


def grid_to_image(grid, cell_px, fg, bg):
    """Render an X/. grid to a 2-color PIL image scaled by cell_px."""
    h, w = len(grid), (len(grid[0]) if grid else 0)
    img = Image.new("RGB", (w, h), bg)
    for r, line in enumerate(grid):
        for c, ch in enumerate(line):
            if ch == "X":
                img.putpixel((c, r), fg)
    return img.resize((w * cell_px, h * cell_px), Image.NEAREST)


def build_frames(text, n, m, cell_px, fg, bg):
    """One frame per character (space -> blank frame). Returns (frames, ms)."""
    norm = text.replace("_", " ")
    frames = [grid_to_image(centered_letter_grid(ch, n, m), cell_px, fg, bg)
              for ch in norm]
    durations = [STEP_MS] * len(frames)
    return frames, durations


def main():
    args = sys.argv[1:]
    cell_px = int(args[0]) if len(args) > 0 else 6
    n = int(args[1]) if len(args) > 1 else 50
    m = int(args[2]) if len(args) > 2 else 50
    text = args[3] if len(args) > 3 else "hello"
    fg = hex_to_rgb(args[4] if len(args) > 4 else LETTER_COLOR)
    bg = hex_to_rgb(args[5] if len(args) > 5 else BG_COLOR)
    global STEP_MS
    STEP_MS = int(args[6]) if len(args) > 6 else STEP_MS

    frames, durations = build_frames(text, n, m, cell_px, fg, bg)
    frames[0].save(
        OUTPUT, save_all=True, append_images=frames[1:],
        duration=durations, loop=0, optimize=True,
    )

    size_kb = os.path.getsize(OUTPUT) / 1024
    gmail = "OK for Gmail" if size_kb < 100 else "TOO BIG (>100 KB)"
    print(f'"{text}" -> {OUTPUT}: {len(frames)} frames (one letter each), '
          f"field {n}x{m}, {frames[0].size[0]}x{frames[0].size[1]}px")
    print(f"  {size_kb:.1f} KB — {gmail}")


if __name__ == "__main__":
    main()
