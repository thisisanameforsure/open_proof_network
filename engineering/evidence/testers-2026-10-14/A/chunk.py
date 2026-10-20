import re,sys,json
src=open(sys.argv[1]).read().split("\n")
outdir=sys.argv[2]
decl=re.compile(r'^(theorem|lemma|axiom|def|noncomputable def|abbrev|instance|end|section|namespace|noncomputable section|open|/--|#print)')
# blocks
starts=[i for i,l in enumerate(src) if re.match(r'^(theorem|lemma|def|noncomputable def|axiom|abbrev)\b',l)]
first=starts[0]
# include doc comments preceding: find start of block as line after previous block's end... simple: header = src[:first] minus docstring lines handled by being in prev block
blocks=[]
for a,b in zip(starts, starts[1:]+[len(src)]):
    blocks.append((a,b))
header="\n".join(src[:first])
def sorried(a,b):
    text="\n".join(src[a:b])
    kw=src[a].split()[0]
    if kw in("def","noncomputable","abbrev","axiom"): return text
    m=None
    for mm in re.finditer(r':=',text):
        pre=text[:mm.start()]
        bal=sum(pre.count(c) for c in "([{⟨")-sum(pre.count(c) for c in ")]}⟩")
        line=pre[pre.rfind("\n")+1:]
        if bal==0 and not re.search(r'\b(let|set|have)\b[^:]*:?[^=]*$',line):
            m=mm; break
    if not m: return text
    # keep trailing doc comment of next decl: find last '/--' after cut
    tail=text[m.end():]
    k=tail.rfind("\n/--")
    doc = tail[k:] if k>=0 else ""
    return text[:m.start()]+":= by sorry"+doc
budget=int(sys.argv[3])  # lines of real proof per chunk
chunks=[]; cur=[]; curlen=0
for idx,(a,b) in enumerate(blocks):
    cur.append(idx); curlen+=b-a
    if curlen>=budget: chunks.append(cur); cur=[]; curlen=0
if cur: chunks.append(cur)
meta=[]
for ci,ch in enumerate(chunks):
    parts=[header]
    for idx in range(ch[0]): parts.append(sorried(*blocks[idx]))
    for idx in ch: parts.append("\n".join(src[blocks[idx][0]:blocks[idx][1]]))
    txt="\n".join(parts)
    open(f"{outdir}/c{ci:02d}.lean","w").write(txt)
    meta.append({"chunk":ci,"lines":[blocks[ch[0]][0]+1,blocks[ch[-1]][1]],"first":src[blocks[ch[0]][0]][:60],"bytes":len(txt.encode())})
json.dump(meta,open(f"{outdir}/meta.json","w"),indent=1)
for m in meta: print(m)
