# general4: classes are given as lists of reduced pairs (k, j), the kernel computes the values L / k * j;
# the colour table tbl[k][j] names each value's class. The proof of `general` is 402-P2's general2 verbatim;
# only the statement gains `cls = C.map (fun c => c.map (fun p => L / p.1 * p.2))` (unused in the proof).
import json,sys
from math import lcm,gcd
from functools import reduce
P2='/home/user/open_proof_network/engineering/evidence/testers-2026-09-29/402-P2/general2.txt'
g=open(P2).read()
old="  have general : ∀ (n L : ℕ) (cls tbl : List (List ℕ)), 2 ≤ n → 0 < L →\n"
assert old in g
g4=g.replace(old,"  have general : ∀ (n L : ℕ) (cls : List (List ℕ)) (C : List (List (ℕ × ℕ))) (tbl : List (List ℕ)),\n      cls = C.map (fun c => c.map (fun p => L / p.1 * p.2)) → 2 ≤ n → 0 < L →\n")
o2="    intro n L cls tbl hn2 hLpos hL H1 H2 A hA hn\n"
assert o2 in g4
g4=g4.replace(o2,"    intro n L cls _C tbl _hcls hn2 hLpos hL H1 H2 A hA hn\n")
GENERAL=g4
def cert(n,tbl):
    L=reduce(lcm,range(1,n),1)
    C=[[] for _ in range(n-2)]; seen=set()
    for k in range(1,n):
        for j in range(1,k):
            if gcd(j,k)!=1: continue
            C[tbl[k][j]].append((k,j))
    # sanity: python re-check of class property on values and of table consistency
    for k in range(1,n):
        for j in range(1,k):
            i=tbl[k][j]; v=L//k*j
            assert i<n-2 and any(L//a*b==v for a,b in C[i])
    for c in C:
        vs=[L//a*b for a,b in c]
        for v in vs:
            for w in vs:
                if v!=w: assert n*gcd(v,w)<=v or n*gcd(v,w)<=w
    Cs='['+','.join('['+','.join(f'({a},{b})' for a,b in c)+']' for c in C)+']'
    T=json.dumps(tbl,separators=(',',':'))
    return L,Cs,T
def call(n,tbl,indent='  · '):
    L,Cs,T=cert(n,tbl)
    return f"{indent}exact general {n} {L} _ {Cs} {T} rfl (by norm_num) (by norm_num) (by decide +kernel)\n      (by decide +kernel) (by decide +kernel) B hB hn\n"
if __name__=='__main__':
    tbls=json.load(open(sys.argv[1])); n=sys.argv[2]
    hdr=f"""import Mathlib

theorem card_test : ∀ (B : Finset ℕ), 0 ∉ B → B.card = {n} → ∃ a ∈ B, ∃ b ∈ B, a.gcd b ≤ (a / B.card : ℚ) := by
"""
    body=hdr+GENERAL+"  intro B hB hn\n"+call(int(n),tbls[n],indent='  ')
    open(sys.argv[3],'w').write(body); print(len(body), 'cert bytes', len(call(int(n),tbls[n])))
