#!/usr/bin/env python3
"""Combine your email text with a generated decoration into one HTML file.

Flow:
  1. You write your email in mail.txt (plain text, blank line = new paragraph).
  2. You copy the decoration you like into optimal.html in this main folder
     (whatever any generator produced — noise, playground, image, text, ...).
  3. Run this. It merges them into email.html:

        <div class="mail">   ... your text ...   </div>
        <div class="deco">   ... the decoration ...   </div>

     The decoration's own <style> is pulled up into the page head, so its colors
     and animations keep working. Paste email.html into your email.

Usage:
    python build_email.py
    python build_email.py mail.txt optimal.html email.html
"""

import html as html_lib
import re
import sys


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def mail_to_html(text):
    """Plain text -> paragraphs with INLINE styling (email strips <style>)."""
    p_style = ("margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;"
               "font-size:15px;line-height:1.55;color:#1a1f26")
    blocks = re.split(r"\n\s*\n", text.strip())
    paras = []
    for block in blocks:
        safe = html_lib.escape(block.strip()).replace("\n", "<br>")
        paras.append(f'    <p style="{p_style}">{safe}</p>')
    return "\n".join(paras)


def extract(deco_html):
    """Pull the <style> body and the <body> inner content out of a full page."""
    style = re.search(r"<style>(.*?)</style>", deco_html, re.S)
    body = re.search(r"<body>(.*?)</body>", deco_html, re.S)
    style_css = style.group(1).strip() if style else ""
    body_html = body.group(1).strip() if body else deco_html.strip()
    return style_css, body_html


def build(mail_text, deco_html):
    """Combine mail + decoration with NO <style> block, so it survives email.

    Everything is inline. If the decoration still carries its own <style>
    (an animated/hover one, which email strips anyway), we keep that block in
    the head too so it at least previews in a browser — but for a real email use
    an inline decoration (see signature/email_safe.py).
    """
    mail_html = mail_to_html(mail_text)
    deco_css, deco_body = extract(deco_html)

    head_style = f"<style>\n{deco_css}\n</style>\n" if deco_css else ""
    return (
        "<!DOCTYPE html>\n<html lang=\"pl\">\n<head>\n<meta charset=\"UTF-8\">\n"
        f"{head_style}</head>\n<body>\n"
        f"<div>\n{mail_html}\n</div>\n"
        f"<div style=\"margin-top:22px\">{deco_body}</div>\n"
        "</body>\n</html>\n"
    )


def main():
    mail_file = sys.argv[1] if len(sys.argv) > 1 else "mail.txt"
    deco_file = sys.argv[2] if len(sys.argv) > 2 else "optimal.html"
    out_file = sys.argv[3] if len(sys.argv) > 3 else "email.html"

    mail_text = read_text(mail_file)
    deco_html = read_text(deco_file)
    combined = build(mail_text, deco_html)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(combined)

    kb = len(combined.encode("utf-8")) / 1024
    gmail = "OK for Gmail" if kb < 100 else "TOO BIG — Gmail will clip (>100 KB)"
    print(f"{mail_file} + {deco_file} -> {out_file}")
    print(f"  {kb:.1f} KB — {gmail}")


if __name__ == "__main__":
    main()
