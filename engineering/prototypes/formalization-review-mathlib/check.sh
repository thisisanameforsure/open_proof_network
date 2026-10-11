#!/bin/sh
# usage: ./check.sh <target_id> <file.lean>   — compiles the file with Mathlib on the live network's fast check
python3 -c "
import json,sys,urllib.request
b=json.dumps({'target_id':sys.argv[1],'content':open(sys.argv[2]).read()}).encode()
r=urllib.request.urlopen(urllib.request.Request('https://api.openproofnetwork.org/check',data=b,headers={'content-type':'application/json'}),timeout=60)
o=json.loads(r.read()); lm=(o.get('result') or {}).get('lean_messages') or {}
print('okay:',o.get('okay')); [print('ERROR',e) for e in lm.get('errors',[])]; [print('info',e) for e in lm.get('infos',[])]
" "$1" "$2"
