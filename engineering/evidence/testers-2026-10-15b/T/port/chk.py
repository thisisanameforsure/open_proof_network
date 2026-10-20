import json,sys,os,subprocess,concurrent.futures as cf,time
D=json.load(open('decls.json'))
H="import Mathlib\nnoncomputable section\nopen scoped BigOperators Nat MatrixOrder\nopen Finset Filter\n\n"
def full(i):
    p=f"fixes/{D[i]['name']}.lean"
    return open(p).read() if os.path.exists(p) else D[i]['full']
MCP="/Users/mikehiggins/Desktop/repos/open_proof_network/engineering/evidence/testers-2026-10-15b/T/mcp.py"
def run(i):
    pre='\n'.join(D[j]['stub'] for j in range(i))
    content=H+pre+'\n\n'+full(i)+'\n'
    nm=D[i]['name']
    open(f'res/{nm}.content.lean','w').write(content)
    off=content[:len(H+pre)+2].count('\n')
    args=json.dumps({"target_id":"erdos-1094","mode":"check","content":content})
    t0=time.time()
    try:
        r=subprocess.run(["python3",MCP,"check_lean",args,f"res/{nm}.json"],capture_output=True,text=True,timeout=280)
    except Exception as e:
        return nm,f"EXC {e}"
    try:
        d=json.load(open(f'res/{nm}.json')); b=d.get('body',d)
    except Exception as e:
        return nm,f"bad {r.stderr[-300:]}"
    if not isinstance(b,dict) or 'result' not in b:
        return nm, f"{time.time()-t0:.0f}s status {d.get('status')} {str(b)[:200]}"
    errs=b['result'].get('lean_messages',{}).get('errors',[])
    errs=[e for e in errs]
    return nm, f"{time.time()-t0:.0f}s okay={b.get('okay')} nerr={len(errs)} off={off}\n" + "\n".join("   "+e[:600] for e in errs)
idx=[int(x) for x in sys.argv[1:]] if sys.argv[1:] else range(len(D))
with cf.ThreadPoolExecutor(int(os.environ.get('PAR','6'))) as ex:
    for nm,msg in ex.map(run, idx):
        print(f"== {nm}: {msg}", flush=True)
