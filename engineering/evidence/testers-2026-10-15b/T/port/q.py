import json,sys,os,subprocess,time
# usage: q.py <decl-index> [extra lean text appended after]
D=json.load(open('decls.json'))
H="import Mathlib\n\nopen scoped Nat\n\n"
i=int(sys.argv[1]); nm=D[i]['name']
p=f"fixes/{nm}.lean"
body=open(p).read() if os.path.exists(p) else D[i]['full']
pre='\n'.join(D[j]['stub'] for j in range(i))
content=H+pre+'\n\n'+body+'\n'
off=(H+pre+'\n\n').count('\n')
MCP="/Users/mikehiggins/Desktop/repos/open_proof_network/engineering/evidence/testers-2026-10-15b/T/mcp.py"
args=json.dumps({"target_id":"erdos-1094","mode":"check","content":content})
t0=time.time()
subprocess.run(["python3",MCP,"check_lean",args,f"res/{nm}.q.json"],capture_output=True,text=True,timeout=280)
d=json.load(open(f'res/{nm}.q.json')); b=d.get('body',d)
if 'result' not in b: print(d); sys.exit()
import re
errs=b['result'].get('lean_messages',{}).get('errors',[])
print(f"{nm} {time.time()-t0:.0f}s nerr={len(errs)} (decl line = content line - {off})")
for e in errs:
    m=re.match(r'-:(\d+):(\d+)',e)
    print(f"--- decl line {int(m.group(1))-off}:" if m else "---", e[:int(os.environ.get('W','1500'))])
