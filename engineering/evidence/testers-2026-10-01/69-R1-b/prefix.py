import json,re,pathlib,sys
sys.path.insert(0,'69b'); from chk import check,summ
root=pathlib.Path('lean-proofs/src/latest')
order=json.load(open('69b/order.json'))
def body(t): return re.sub(r'^import \S+\n','',t,flags=re.M)
mert=body(pathlib.Path('FormalPantheon/BoundedGaps/BoundedGaps/Maynard/PrimeMertens.lean').read_text())
acc="import Mathlib\n"; out=open('69b/prefix-results.txt','a')
i0=order.index('ErdosProblems.Erdos697.Erdos697PrimeHarmonic')
for i,m in enumerate(order):
    if i==i0: acc+="-- ==== BoundedGaps.Maynard.PrimeMertens\n"+mert+"\n"
    acc+=f"-- ==== {m}\n"+body((root/(m.replace('.','/')+'.lean')).read_text())+"\n"
    if i%4==3 or i==len(order)-1:
        r=summ(check(acc)); r['upto']=m; r['n']=i+1; r['bytes']=len(acc.encode())
        out.write(json.dumps(r,ensure_ascii=False)+"\n"); out.flush()
        if 'http' in r or not r.get('okay'): break
