# usage: genN.py N word  -> writes StatementN.lean, ProofN.lean (no Nodes import), classesN.json
import json, sys, itertools
from math import gcd, lcm
sys.path.insert(0,'.')
N=int(sys.argv[1]); word=sys.argv[2]
L=1
for k in range(1,N): L=lcm(L,k)
S=sorted({L//k*j for k in range(2,N) for j in range(1,k)})
conflict=lambda a,b: N*gcd(a,b) > max(a,b)
adj={a:{b for b in S if b!=a and conflict(a,b)} for a in S}
K=N-2; col={}
def pick():
    best=None;bk=None
    for a in S:
        if a in col: continue
        key=(len({col[b] for b in adj[a] if b in col}),len(adj[a]))
        if bk is None or key>bk: bk=key;best=a
    return best
def rec():
    if len(col)==len(S): return True
    a=pick(); used={col[b] for b in adj[a] if b in col}
    for c in range(K):
        if c not in used:
            col[a]=c
            if rec(): return True
            del col[a]
    return False
assert rec()
classes=[sorted(a for a in S if col[a]==i) for i in range(K)]
assert all(not conflict(a,b) for c in classes for a,b in itertools.combinations(c,2))
json.dump(classes,open(f'gclasses{N}.json','w'))
Slit="["+", ".join(map(str,S))+"]"
Clit="["+", ".join("["+", ".join(map(str,c))+"]" for c in classes)+"]"
stmt=f"""import Mathlib

theorem Opn.erdos_402_card_{word} :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = {N} → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
"""
src=open('gen13.py').read()
body=src[src.index('body=f"""')+9:src.index('"""\nassert')]
body=body.replace('27720','@L@').replace('13','@N@').replace('12','@M@').replace('11','@K@').replace('@L@',str(L)).replace('@N@',str(N)).replace('@M@',str(N-1)).replace('@K@',str(K))
# careful: 'k < 13' etc handled; check literal list placeholders remain
body=body.replace('{Slit}',Slit).replace('{Clit}',Clit).replace('{dec}','decide')
open(f'gStatement{N}.lean','w').write(stmt)
open(f'gProof{N}.lean','w').write(stmt.replace("  sorry\n",body))
print(N,L,len(S),K)
