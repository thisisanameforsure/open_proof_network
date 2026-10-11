import json,sys,urllib.request,re
defs=open('Defs.lean').read()
sk=open(sys.argv[1]).read().replace('import Mathlib\nimport Defs.Construction\n','')
content=defs+"\n"+sk
req=urllib.request.Request('https://api.openproofnetwork.org/check',data=json.dumps({"target_id":"erdos-69","mode":"check","content":content}).encode(),headers={'Content-Type':'application/json'})
try:
    r=json.load(urllib.request.urlopen(req,timeout=300))
except urllib.error.HTTPError as e:
    print(e.code,e.read()[:2000]); sys.exit()
print('okay',r.get('okay'),'log',r.get('log_id'),'lint',r.get('lint'))
res=r.get('result') or {}
for k in ('lean_messages','tool_messages'):
    m=res.get(k) or {}
    for kk in ('errors','warnings'):
        for e in (m.get(kk) or [])[:12]: print(k,kk,str(e)[:900])
