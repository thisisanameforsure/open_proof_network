import json,sys,os,subprocess,time,re
# qi.py <idx> <variantfile> : check decl idx with body from variantfile
D=json.load(open('decls.json'))
H="import Mathlib\n\nopen scoped Nat\n\n"
i=int(sys.argv[1]); vf=sys.argv[2]
pre='\n'.join(D[j]['stub'] for j in range(i))
content=H+pre+'\n\n'+open(vf).read()+'\n'
off=(H+pre+'\n\n').count('\n')
MCP="/Users/mikehiggins/Desktop/repos/open_proof_network/engineering/evidence/testers-2026-10-15b/T/mcp.py"
args=json.dumps({"target_id":"erdos-1094","mode":"check","content":content})
t0=time.time(); out=vf+'.res.json'
subprocess.run(["python3",MCP,"check_lean",args,out],capture_output=True,text=True,timeout=280)
d=json.load(open(out)); b=d.get('body',d)
if 'result' not in b: print(vf, str(d)[:200]); sys.exit()
errs=b['result'].get('lean_messages',{}).get('errors',[])
print(f"{vf} {time.time()-t0:.0f}s nerr={len(errs)}")
for e in errs:
    m=re.match(r'-:(\d+):(\d+)',e)
    print(f"--- decl line {int(m.group(1))-off}:" if m else "---", e[:int(os.environ.get('W','1200'))])
