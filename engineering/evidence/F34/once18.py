"""F34-T18 on the live graph: every statement of every problem placed exactly once."""
import json, re, sys
from collections import Counter
from pathlib import Path
from opn_site import model, render
root = Path(sys.argv[1]); commit = sys.argv[2]
site = model.load_site(root, commit)
r = render.Renderer(site, repo_url="https://github.com/example/graph")
bad, with_section, total = [], 0, 0
for tid, tv in site.targets.items():
    page = r.target(tv)
    m = re.search(r'id="graph-layouts">(.*?)</script>', page, re.S)
    lays = json.loads(m.group(1).replace("<\\/", "</"))
    drawn = {n for n in lays["routes"]["nodes"] if "@" not in n}
    sec = re.search(r'<section class="off-route">(.*?)</section>', page, re.S)
    here = Counter(re.findall(r'<li data-node="([^"]+)"', sec.group(1) if sec else ""))
    with_section += bool(sec); total += 1
    if sec: print(tid, dict(Counter(re.findall(r"<h3>([^<]*)", sec.group(1)))), file=sys.stderr)
    every = set(tv.nodes)
    if any(v != 1 for v in here.values()) or drawn & set(here) or (drawn | set(here)) != every:
        bad.append({"target": tid, "twice": [k for k, v in here.items() if v != 1], "both": sorted(drawn & set(here)), "missing": sorted(every - drawn - set(here)), "extra": sorted((drawn | set(here)) - every)})
print(json.dumps({"targets": total, "with_section": with_section, "bad": bad}, indent=1))
