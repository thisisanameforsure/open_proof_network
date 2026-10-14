import sys, urllib.request
from pathlib import Path
sys.path.insert(0, "site/tests")
from panel_text import word_count
out = Path(sys.argv[1])
def main_of(p):
    s = p.index("<main"); return p[p.index(">", s) + 1 : p.rindex("</main>")]
print(f"{'node':32} {'live':>6} {'new':>6}")
for n in sys.argv[2:]:
    t, node = n.split("/")
    new = main_of((out / "nodes" / t / node / "index.html").read_text())
    live = main_of(urllib.request.urlopen(f"https://openproofnetwork.org/nodes/{t}/{node}/").read().decode())
    print(f"{node:32} {word_count(live):>6} {word_count(new):>6}")
