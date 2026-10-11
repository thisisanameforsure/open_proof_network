import sys,json
from chk import check
r=check(open(sys.argv[1]).read())
res=r.get('result') or {}
lm=res.get('lean_messages') or {}
print('okay',r.get('okay'),'secs',round(r.get('secs',0),1),'lint',[w.get('code') for w in r.get('lint',[])], r.get('http'), r.get('body'))
for k in ('errors','warnings','infos'):
    for m in lm.get(k,[]): print(k[:-1].upper(), m)
