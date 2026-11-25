"""Visible text carrying internal codes: decision numbers, attestation numbers, motion ids."""
import re, sys, collections
from html.parser import HTMLParser
from pathlib import Path
CODE = re.compile(r"\bD-\d+\b|\battestation \d{3,}|\bmotion:\d+|\bF\d\d-[TRQ]\d+")
SKIP = {"code", "pre", "script", "style", "title", "textarea"}
VOID = {"br","img","input","meta","link","hr","wbr","path","circle","rect","line","use","source"}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack=[]; s.hits=[]
    def handle_starttag(s, tag, attrs):
        if tag in VOID: return
        cls=(dict(attrs).get("class") or "")
        s.stack.append((tag, cls, tag in SKIP or "term-card" in cls or "page-source" in cls))
    def handle_endtag(s, tag):
        for i in range(len(s.stack)-1,-1,-1):
            if s.stack[i][0]==tag: del s.stack[i:]; break
    def handle_data(s, d):
        if any(x[2] for x in s.stack): return
        for m in CODE.finditer(d):
            near=next((f"{t}.{c.split()[0]}" for t,c,_ in reversed(s.stack) if c), s.stack[-1][0] if s.stack else "")
            s.hits.append((m.group(0).split()[0].split(":")[0].split("-")[0], near, d.strip()[:100]))
root=Path(sys.argv[1]); by=collections.Counter(); pages=collections.defaultdict(set); ex={}
for f in root.rglob("index.html"):
    rel=str(f.relative_to(root)); kind=rel.split("/")[0] if "/" in rel else "home"
    if kind in ("nodes",) : kind="nodes"
    p=P(); p.feed(f.read_text(encoding="utf-8"))
    for code,near,txt in p.hits:
        k=(kind,near); by[k]+=1; pages[k].add(rel); ex.setdefault(k,txt)
print("total hits", sum(by.values()), "pages", len(set().union(*pages.values())) if pages else 0)
for k,n in by.most_common(45): print(n, len(pages[k]), k, "|", ex[k][:90])
