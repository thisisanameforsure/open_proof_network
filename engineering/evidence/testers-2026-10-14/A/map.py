import json,glob,re
meta={m["chunk"]:m for m in json.load(open("meta.json"))}
rows=[]
for ci in sorted(meta):
    f=f"c{ci:02d}.lean.check.json"
    try: d=json.load(open(f))
    except Exception: rows.append((ci,meta[ci]["lines"],"not-run",[])); continue
    b=d.get("body",d)
    if d.get("status")!=200: rows.append((ci,meta[ci]["lines"],f"status {d.get('status')}",[])); continue
    r=b["result"]; content=r["content"].split("\n")
    bad={}
    for e in r["lean_messages"]["errors"]:
        m=re.match(r'-:(\d+):',e); ln=int(m.group(1))
        name="?"
        for j in range(ln-1,-1,-1):
            mm=re.match(r'^(theorem|lemma|def|noncomputable def)\s+(\S+)',content[j])
            if mm: name=mm.group(2); break
        bad.setdefault(name,[]).append(e.split("\n")[0][:140])
    rows.append((ci,meta[ci]["lines"],"ok" if not bad else "errors",bad))
for ci,lines,st,bad in rows:
    print(f"chunk {ci} (src lines {lines[0]}-{lines[1]}): {st}")
    if isinstance(bad,dict):
        for k,v in bad.items(): print(f"   {k}: {v[0]}" + (f" (+{len(v)-1} more)" if len(v)>1 else ""))
