import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
pages = ["erdos-1094/erdos-1094--h1", "erdos-1094/erdos-1094--h3", "erdos-1094/erdos-1094"]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/Users/mikehiggins/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell")
    for w, h in ((1440, 900), (390, 844)):
        pg = b.new_page(viewport={"width": w, "height": h})
        for path in pages:
            name = path.split("/")[1]
            pg.goto(f"http://localhost:8791/nodes/{path}/", wait_until="networkidle")
            sw = pg.evaluate("document.documentElement.scrollWidth")
            print(name, w, "scrollWidth", sw, "height", pg.evaluate("document.body.scrollHeight"))
            pg.screenshot(path=f"{out}/task-50-{name}-{w}.png", full_page=True)
        pg.close()
    b.close()
