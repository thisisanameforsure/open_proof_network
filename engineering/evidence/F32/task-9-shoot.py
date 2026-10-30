"""F32-T9 screenshots: the live page of the first hole born proved on the record,
variant-93e79cb5--h3 (graph #1239), at 1440 and 390 px, with the page's width checked.

    uv run --frozen --with playwright python engineering/evidence/F32/task-9-shoot.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
URL = "https://openproofnetwork.org/nodes/tutorial/variant-93e79cb5--h3/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (1440, 390):
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(URL, wait_until="networkidle")
        scroll = page.evaluate("document.documentElement.scrollWidth")
        proof = page.locator("text=carried by a partial").first.inner_text()
        print(f"{width}px scrollWidth={scroll} proof row: {proof!r}")
        page.screenshot(path=str(OUT / f"task-9-live-{width}.png"), full_page=True)
    browser.close()
