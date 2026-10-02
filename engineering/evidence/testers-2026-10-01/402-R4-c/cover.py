# greedy prime cover: blocks [lo,hi] with a prime p such that every n in the block has n<p<2n, (2n-p)^2<=n
# (certified conservatively by (2hi-p)^2 <= lo). Emits Lean for a sample block range.
from math import isqrt
import sys
M=int(sys.argv[1]) if len(sys.argv)>1 else 200000
sv=bytearray([1])*(2*M+2); sv[0]=sv[1]=0
for i in range(2,isqrt(2*M+1)+1):
    if sv[i]: sv[i*i::i]=bytearray(len(sv[i*i::i]))
def cover(lo0,M):
    out=[];lo=lo0
    while lo<=M:
        p=2*lo-1
        while not sv[p]: p-=1
        assert (2*lo-p)**2<=lo,(lo,p)
        hi=(p+isqrt(lo))//2
        assert p<2*lo and hi<p and (2*hi-p)**2<=lo
        out.append((lo,hi,p)); lo=hi+1
    return out
c=cover(681,M)
print("blocks for 681..%d:"%M,len(c)," first",c[:3]," last",c[-1])
for a,b in [(681,1000),(1000,7000),(7000,50000),(50000,200000)]:
    print("  blocks with lo in [%d,%d): %d"%(a,b,sum(1 for x in c if a<=x[0]<b)))
def lean(blocks,name):
    lo=blocks[0][0];hi=blocks[-1][1]
    L=["import Mathlib","",
       "/-- 402-R4-c. Window primes for %d ≤ n ≤ %d: %d primality certificates by `norm_num`, no `native_decide`. -/"%(lo,hi,len(blocks)),
       "theorem %s : ∀ n : ℕ, %d ≤ n → n ≤ %d →"%(name,lo,hi),
       "    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by",
       "  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →",
       "      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by",
       "    intro p lo hi k hp h1 h2 h3 h4 n hl hh",
       "    refine ⟨p, hp, by omega, by omega, ?_⟩",
       "    have : 2 * n - p ≤ k := by omega",
       "    exact le_trans (Nat.mul_le_mul this this) (by omega)",
       "  intro n hl hh"]
    for (a,b,p) in blocks:
        k=2*b-p
        L.append("  by_cases h%d : n ≤ %d"%(b,b))
        L.append("  · exact blk %d %d %d %d (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h%d"%(p,a,b,k,b))
    L.append("  omega")
    return "\n".join(L)+"\n"
i=int(sys.argv[2]) if len(sys.argv)>2 else 0
m=int(sys.argv[3]) if len(sys.argv)>3 else 40
open("Window_sample.lean","w").write(lean(c[i:i+m],"r4c_window_%d_%d"%(c[i][0],c[i+m-1][1])))
