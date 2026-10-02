# 402-R5-b: simple-window certificates (402-R4-c's W(n)) for the non-exceptional n in [10, 676].
from math import isqrt
from num2 import isp
LO,HI=10,676
blocks=[];exc=[];lo=LO
while lo<=HI:
    p=2*lo-1
    while not isp(p): p-=1
    if (2*lo-p)**2>lo: exc.append(lo); lo+=1; continue
    hi=min((p+isqrt(lo))//2,HI)
    assert lo<p and hi<p and p<2*lo and (2*hi-p)**2<=lo
    blocks.append((lo,hi,p)); lo=hi+1
print("blocks",len(blocks),"exceptions",exc)
def lean(bl,exc,name):
    lo=bl[0][0];hi=bl[-1][1]
    ex=[e for e in exc if lo<=e<=hi]
    hyp="".join(" n ≠ %d →"%e for e in ex)
    L=["import Mathlib","",
       "/-- 402-R5-b (generator after 402-R4-c's cover.py). Window primes for %d ≤ n ≤ %d except n ∈ {%s}:"%(lo,hi,", ".join(map(str,ex))),
       "%d primality certificates by `norm_num`, no `native_decide`. -/"%len(bl),
       "theorem %s : ∀ n : ℕ, %d ≤ n → n ≤ %d →%s"%(name,lo,hi,hyp),
       "    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by",
       "  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →",
       "      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by",
       "    intro p lo hi k hp h1 h2 h3 h4 n hl hh",
       "    refine ⟨p, hp, by omega, by omega, ?_⟩",
       "    have : 2 * n - p ≤ k := by omega",
       "    exact le_trans (Nat.mul_le_mul this this) (by omega)",
       "  intro n hl hh"+"".join(" e%d"%e for e in ex)]
    for (a,b,p) in bl:
        L.append("  by_cases h%d : n ≤ %d"%(b,b))
        L.append("  · exact blk %d %d %d %d (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h%d"%(p,a,b,2*b-p,b))
    L.append("  omega")
    return "\n".join(L)+"\n"
import os
os.makedirs("Window",exist_ok=True)
h=len(blocks)//2
for part in (blocks[:h],blocks[h:]):
    nm="r5b_window_%d_%d"%(part[0][0],part[-1][1])
    open("Window/%s.lean"%nm,"w").write(lean(part,exc,nm)); print(nm,len(part))
# python cross-check of the claim itself
ex=set(exc)
for n in range(LO,HI+1):
    ok=any(isp(p) and (2*n-p)**2<=n for p in range(n+1,2*n))
    assert ok==(n not in ex),n
print("claim cross-checked in Python for every n in [%d,%d]"%(LO,HI))
