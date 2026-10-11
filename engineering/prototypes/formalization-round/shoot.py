"""Screenshots of the round's evidence page, plus the measurements the eye misses (no sideways
scroll at phone width). python shoot.py --out <dir>"""
import argparse, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
url = (Path(__file__).resolve().parent / "out" / "round.html").as_uri()
meas = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, w, scheme in (("desktop", 1360, "light"), ("desktop-dark", 1360, "dark"), ("phone", 390, "light")):
        pg = b.new_page(viewport={"width": w, "height": 900}, color_scheme=scheme)
        pg.goto(url)
        pg.screenshot(path=str(out / f"round-{name}-full.png"), full_page=True)
        meas[name] = pg.evaluate("({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
        for cj in ("goldbach", "legendre", "oppermann"):
            if name == "desktop":
                pg.locator(f"#{cj}").scroll_into_view_if_needed()
                pg.evaluate(f"document.getElementById('{cj}').scrollIntoView()")
                pg.screenshot(path=str(out / f"round-{cj}-top.png"))
        pg.close()
    b.close()
bad = {k: v for k, v in meas.items() if v["sw"] > v["cw"]}
print(json.dumps({"page_width": meas, "sideways_scroll": bad}, indent=1))
sys.exit(1 if bad else 0)
