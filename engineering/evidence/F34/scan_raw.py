"""List visible text runs (outside .math, code, pre, script, style, title) that carry raw TeX or *emphasis*."""
import re, sys, collections
from html.parser import HTMLParser
from pathlib import Path
TEX = re.compile(r"\$[^$\s][^$]*\\[A-Za-z]|\$\$|\\(?:mathbb|subseteq|binom|le|ge|frac|in|cdot|sum)\b")
EMPH = re.compile(r"(?<![\w*])\*[A-Za-z][^*\n]{0,40}\*(?![\w*])")
SKIP = {"code", "pre", "script", "style", "title", "textarea"}
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.stack=[]; s.hits=[]; s.ctx=[]
    def handle_starttag(s, tag, attrs):
        if tag in ("br","img","input","meta","link","hr","wbr","source","area","col","embed","param","track","path","circle","rect","line","polyline","use"): return
        a=dict(attrs); cls=(a.get("class") or "").split()
        s.stack.append((tag, "math" in cls or tag in SKIP, " ".join(cls)))
    def handle_endtag(s, tag):
        for i in range(len(s.stack)-1,-1,-1):
            if s.stack[i][0]==tag: del s.stack[i:]; break
    def handle_data(s, d):
        if any(x[1] for x in s.stack): return
        if TEX.search(d) or EMPH.search(d):
            s.hits.append((s.stack[-1][2] if s.stack else "", d.strip()[:110]))
root=Path(sys.argv[1]); by=collections.Counter(); ex={}
for f in root.rglob("*.html"):
    p=P(); p.feed(f.read_text(encoding="utf-8"))
    for cls,txt in p.hits:
        kind=str(f.relative_to(root)).split("/")[0]
        key=(kind,cls); by[key]+=1; ex.setdefault(key,(str(f.relative_to(root)),txt))
for k,n in by.most_common(40): print(n,k,ex[k])
