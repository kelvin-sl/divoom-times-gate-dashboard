"""Build docs/preview.png: the demo tiles inside a lamp frame (tools/preview.html).

  python3 dash.py --demo && python3 tools/build_preview.py

Needs Playwright (`pip install playwright`) and Google Chrome or `playwright install chromium`.
"""
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
    except Exception:
        browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1600, "height": 520}, device_scale_factor=2)
    page.goto((ROOT / "tools" / "preview.html").as_uri())
    page.wait_for_load_state("load")
    page.locator(".stage").screenshot(path=str(ROOT / "docs" / "preview.png"), omit_background=True)
    browser.close()
print("wrote docs/preview.png")
