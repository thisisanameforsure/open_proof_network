import json,sys,urllib.request
D='/home/claude/open_proof_network/engineering/evidence/testers-2026-10-01/69-R4-b/'
defs=open(D+(sys.argv[2] if len(sys.argv)>2 else 'Defs-v2.lean')).read()
sk='\n'.join(l for l in open(sys.argv[1]).read().split('\n') if not l.startswith('import '))
content=defs+"\n"+sk
req=urllib.request.Request('https://api.openproofnetwork.org/check',data=json.dumps({"target_id":"erdos-69","mode":"check","content":content}).encode(),headers={'Content-Type':'application/json'})
try:
    r=json.load(urllib.request.urlopen(req,timeout=300))
except urllib.error.HTTPError as e:
    print(e.code,e.read()[:2000]); sys.exit()
print('okay',r.get('okay'),'log',r.get('log_id'),'lint',r.get('lint'),'defs_lines',defs.count('\n')+1)
res=r.get('result') or {}
for k in ('lean_messages','tool_messages'):
    m=res.get(k) or {}
    for kk in ('errors','warnings'):
        for e in (m.get(kk) or [])[:12]:
            e=str(e)
            if 'naming conventions' in e: continue
            print(k,kk,e[:300]+' ... '+e[-900:] if len(e)>1300 else e)
