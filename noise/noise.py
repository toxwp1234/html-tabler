#!/usr/bin/env python3
"""N-color animated noise field (optimized, deterministic).

Fills an n x m table with fast flickering "static". The randomness is seeded, so
it is fully reproducible/computable, and it is structured so the output stays
small: instead of storing every cell for every frame, we build a fixed pool of
K random color-sequences (as @keyframes) and D phase-delays, then give each cell
one sequence + one delay. So the CSS is a few dozen rules, not thousands, while
the field still looks random because sequence+delay combos rarely repeat.

The page <title> is intentionally nondescript: it does not reveal the method.

Colors: pass as many hex colors as you like — that many appear in the noise.
The FIRST color is the background color.

Input: n m scale then the hex colors.
    scale = cell size in pixels.

Writes:
  - index.html    readable
  - optimal.html  minified

Usage:
    python noise.py 50 50 7 "#101010" "#ff2d55" "#00e0ff" "#ffe600"
    python noise.py 40 60 6 "#000000" "#39ff14" "#00b3ff"
"""

import random
import re
import sys

READABLE = "index.html"
OPTIMAL = "optimal.html"

# Deterministic seed -> the exact same noise every run (so it is "computable").
SEED = 1

# Turbo speed: FRAMES flips over DURATION seconds.
FRAMES = 10
DURATION = "0.5s"

# Optimization knobs: pool of distinct color-sequences and of phase-delays.
# Cells pick one of each, so the field varies with only SEQS + DELAYS rules.
SEQS = 24
DELAYS = 16

# Page title — deliberately says nothing about how the page is built.
# None -> a random meaningless token is generated (also nondescript).
TITLE = None

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def class_name(index, prefix=""):
    """Short CSS-safe class name (a, b, ..., aa), optionally prefixed."""
    base = len(_ALPHABET)
    name = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, base)
        name = _ALPHABET[rem] + name
    return prefix + name


def build_page(n, m, scale, colors, rng):
    """Build the noise table. Returns html."""
    bg = colors[0]

    # Pool of K random color-sequences, each FRAMES long, drawn from the palette.
    seqs = [[rng.choice(colors) for _ in range(FRAMES)] for _ in range(SEQS)]
    seq_classes = [class_name(i, "s") for i in range(SEQS)]

    # Pool of D phase-delays: negative offsets spread across one cycle so cells
    # using the same sequence still flicker out of step.
    dur_s = float(DURATION.rstrip("s"))
    delay_classes = [class_name(i, "d") for i in range(DELAYS)]
    delays = [-round(dur_s * i / DELAYS, 4) for i in range(DELAYS)]

    # Every cell = one sequence class + one delay class, both chosen by the seed.
    rows = ["<table>", "  <tbody>"]
    for _r in range(n):
        cells = []
        for _c in range(m):
            s = seq_classes[rng.randrange(SEQS)]
            d = delay_classes[rng.randrange(DELAYS)]
            cells.append(f'<td class="{s} {d}"></td>')
        rows.append("    <tr>" + "".join(cells) + "</tr>")
    rows.append("  </tbody>")
    rows.append("</table>")
    table_html = "\n".join(rows)

    css_lines = [
        f"body {{ background: {bg}; }}",
        "table { border-collapse: collapse; }",
        f"td {{ width: {scale}px; height: {scale}px; padding: 0; "
        f"background: {bg}; }}",
    ]
    # Sequence rules first (each starts an animation via the shorthand)...
    for seq, cls in zip(seqs, seq_classes):
        stops = " ".join(
            f"{round(i / FRAMES * 100, 2)}% {{ background: {col}; }}"
            for i, col in enumerate(seq)
        )
        css_lines.append(
            f".{cls} {{ animation: {cls} {DURATION} step-end infinite; }}")
        css_lines.append(f"@keyframes {cls} {{ {stops} }}")
    # ...then delay rules, which override only animation-delay (later wins).
    for delay, cls in zip(delays, delay_classes):
        css_lines.append(f".{cls} {{ animation-delay: {delay}s; }}")
    style_css = "\n".join(css_lines)

    title = TITLE if TITLE is not None else class_name(rng.randrange(1 << 20))
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
{table_html}
</body>
</html>
"""
    return html


def minify(html):
    """Shrink: drop whitespace + optional </td>, unquote single-word class, keep </tr>."""
    html = re.sub(r"\n\s*", "", html)
    html = re.sub(r">\s+<", "><", html)
    # Only unquote when the class is a single letter-token (our delay/seq combo
    # has a space, so those keep their quotes — which is correct).
    html = re.sub(r'class="([A-Za-z]+)"', r"class=\1", html)
    html = html.replace("</td>", "")
    return html


def main():
    args = sys.argv[1:]
    if len(args) < 4:
        sys.exit("usage: python noise.py n m scale hex1 [hex2 ...]  "
                 "(first hex = background)")
    n = int(args[0])
    m = int(args[1])
    scale = int(args[2])
    colors = [c if c.startswith("#") else "#" + c for c in args[3:]]

    rng = random.Random(SEED)
    html = build_page(n, m, scale, colors, rng)

    with open(READABLE, "w", encoding="utf-8") as f:
        f.write(html)
    optimal_html = minify(html)
    with open(OPTIMAL, "w", encoding="utf-8") as f:
        f.write(optimal_html)

    print(f"noise {n}x{m} ({n * m} cells), scale={scale}px, "
          f"{len(colors)} colors (bg={colors[0]}), "
          f"{SEQS} seqs x {DELAYS} delays, seed={SEED}")
    print(f"  {READABLE}: {len(html.encode('utf-8')) / 1024:.1f} KB (readable)")
    print(f"  {OPTIMAL}: {len(optimal_html.encode('utf-8')) / 1024:.1f} KB (minified)")


if __name__ == "__main__":
    main()
