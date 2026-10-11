import json,re,pathlib,sys
sys.path.insert(0,'69b'); from chk import check,summ
root=pathlib.Path('lean-proofs/src/latest')
order=json.load(open('69b/order.json'))
def body(t): return re.sub(r'^import \S+\n','',t,flags=re.M)
def strip(t):
    # split into top-level chunks at lines starting in column 0 with a decl keyword
    lines=t.split('\n'); out=[]; i=0
    pat=re.compile(r'^(@\[[^\]]*\]\s*)?(private |protected )?(theorem|lemma) ')
    top=re.compile(r'^\S')
    while i<len(lines):
        if pat.match(lines[i]):
            j=i+1
            while j<len(lines) and not (top.match(lines[j]) and not lines[j].startswith(')')): j+=1
            decl='\n'.join(lines[i:j])
            m=re.search(r' :=( by)?\s*(\n|$)| := ',decl)
            if m: decl=decl[:m.start()]+' := sorry\n'
            out.append(decl); i=j
        else: out.append(lines[i]); i+=1
    return '\n'.join(out)
mods={}
for m in order: mods[m]=body((root/(m.replace('.','/')+'.lean')).read_text())
mods['BoundedGaps.Maynard.PrimeMertens']=body(pathlib.Path('FormalPantheon/BoundedGaps/BoundedGaps/Maynard/PrimeMertens.lean').read_text())
i0=order.index('ErdosProblems.Erdos697.Erdos697PrimeHarmonic'); order.insert(i0,'BoundedGaps.Maynard.PrimeMertens')
start=int(sys.argv[1]); out=open('69b/strip-results.txt','a')
def wrap(m,t): return f"-- ==== {m}\nsection\n{t}\nend\n"
for i in range(start,len(order)):
    acc="import Mathlib\n"+"".join(wrap(m,strip(mods[m])) for m in order[:i])+wrap(order[i],mods[order[i]])
    pathlib.Path('69b/last.lean').write_text(acc)
    r=summ(check(acc)); r['module']=order[i]; r['n']=i; r['bytes']=len(acc.encode())
    out.write(json.dumps(r,ensure_ascii=False)+"\n"); out.flush()
