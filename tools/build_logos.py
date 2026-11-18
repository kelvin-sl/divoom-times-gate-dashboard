#!/usr/bin/env python3
"""Rasterise assets/logos/src/*.svg into 128px transparent PNGs in assets/logos/.

The platform marks are Simple Icons 16.36.0 (CC0, single-colour paths) filled with the platform
colour. Threads and X are black marks, so they are drawn in near-white for a dark lamp.
Add your own logo as src/<name>.svg (kept as drawn) and use it as a theme "mark".
Needs: pip install playwright, then `playwright install chromium` (or an installed Google Chrome)
"""
import os, re
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, "assets/logos/src"), os.path.join(ROOT, "assets/logos")
FILL = {"youtube": "#FF0000", "threads": "#E8EDF2", "x": "#E8EDF2", "claude": "#D97757"}

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True)
    except Exception:  # no bundled browser: fall back to an installed Google Chrome
        browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 128, "height": 128})
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".svg"):
            continue
        name, svg = f[:-4], open(os.path.join(SRC, f)).read()
        head, body = svg.split(">", 1)
        head = re.sub(r'\s(width|height)="[^"]*"', "", head)
        if name in FILL:
            head = head.replace("<svg ", f'<svg fill="{FILL[name]}" ', 1)
        svg = head.replace("<svg ", '<svg width="128" height="128" ', 1) + ">" + body
        page.set_content('<body style="margin:0;background:transparent"><div style="width:128px;height:128px">'
                         + svg + "</div></body>")
        page.locator("div").screenshot(path=os.path.join(OUT, f"{name}.png"), omit_background=True)
        print("built", name)
    browser.close()
