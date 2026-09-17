#!/usr/bin/env python3
"""Email-SAFE static wordmark: your name, colors INLINE on every cell.

Why this exists: email clients (Zimbra, Gmail, Outlook) strip the whole <style>
block out of a message body. All our other generators keep cell size, colors and
animation in <style> via classes — so in a real email those cells lose their
background AND their size and the decoration simply vanishes.

This version puts everything inline on each <td> (width/height as attributes,
background in a style attribute) and uses NO <style> block and NO classes. It is
a plain static gradient wordmark that survives being pasted into an email. No
animation, no hover — those cannot work in email at all.

The whole thing sits on an explicit white card so it shows regardless of the
email's background.

Uses the 5x7 base in font.py.

Input: scale [text] [colorA] [colorB]
    scale = cell px; '_' = space.

Writes:
  - optimal.html   (paste THIS into the email)

Usage:
    python email_safe.py 8 WIKTOR_PAWLAK
    python email_safe.py 8 WIKTOR_PAWLAK "#6366f1" "#22d3ee"
"""

import sys

import font

OUTPUT = "optimal.html"

MARGIN = 1
COLOR_A = "#6366f1"
COLOR_B = "#22d3ee"
CARD_BG = "#ffffff"     # white card behind the wordmark


def lerp_hex(a, b, t):
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return f"#{round(ar+(br-ar)*t):02x}{round(ag+(bg-ag)*t):02x}{round(ab+(bb-ab)*t):02x}"


def text_grid(text):
    text = text.replace("_", " ")
    core = ["" for _ in range(font.GLYPH_H)]
    for i, ch in enumerate(text):
        g = font.glyph(ch)
        for r in range(font.GLYPH_H):
            core[r] += g[r]
            if i != len(text) - 1:
                core[r] += "."
    width = len(core[0]) if core else 0
    blank = "." * (width + 2 * MARGIN)
    grid = [blank] * MARGIN
    grid += ["." * MARGIN + row + "." * MARGIN for row in core]
    grid += [blank] * MARGIN
    return grid


def build(scale, text, color_a, color_b):
    grid = text_grid(text)
    m = len(grid[0]) if grid else 0
    col_colors = [lerp_hex(color_a, color_b, c / max(1, m - 1)) for c in range(m)]

    # Everything inline. Cell size via width/height attributes (very email-safe);
    # letter color via a style attribute. Empty cells stay transparent (the white
    # card shows through). line-height/font-size 0 stops phantom cell height.
    base = f'height={scale} width={scale} style="line-height:0;font-size:0'
    rows = []
    for r in range(len(grid)):
        cells = []
        for c in range(m):
            if grid[r][c] == "X":
                cells.append(f'<td {base};background:{col_colors[c]}"></td>')
            else:
                cells.append(f'<td {base}"></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    table = ('<table cellspacing="0" cellpadding="0" '
             'style="border-collapse:collapse">' + "".join(rows) + "</table>")

    # White card wrapper (inline) so the wordmark shows on any email background.
    card = (f'<div style="display:inline-block;background:{CARD_BG};'
            f'padding:10px;border-radius:10px">{table}</div>')

    return (
        "<!DOCTYPE html><html lang=\"pl\"><head><meta charset=\"UTF-8\">"
        "</head><body>" + card + "</body></html>"
    )


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    text = sys.argv[2] if len(sys.argv) > 2 else "WIKTOR_PAWLAK"
    color_a = sys.argv[3] if len(sys.argv) > 3 else COLOR_A
    color_b = sys.argv[4] if len(sys.argv) > 4 else COLOR_B

    html = build(scale, text, color_a, color_b)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f'email-safe wordmark "{text}" scale={scale}px (inline, no <style>)')
    print(f"  {OUTPUT}: {len(html.encode('utf-8')) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
