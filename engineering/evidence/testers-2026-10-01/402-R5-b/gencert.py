# 402-R5-b: certificate generator for the generalised criterion at a fixed size n.
from math import isqrt
import sys
from num2 import bad, isp
GAPT="(∀ x y : ℕ, x < y → x * y ∣ α → %d * x ≤ α * y)"
def stmt(n,pv="p"):
    return ("∃ p : ℕ, p.Prime ∧ %d < p ∧ p < 2 * %d ∧ 2 * (2 * %d - p) ≤ %d + 2 ∧\n"
            "    ∀ α : ℕ, α < %d → p < α + %d →\n"
            "      (∃ q : ℕ, q.Prime ∧ %d ≤ 3 * q ∧ q ∣ α * (p - α)) ∨\n      "%(n,n,n,n,n,n,n))+GAPT%n
def bigprime(n,m):
    for q in range(m,1,-1):
        if m%q==0 and isp(q) and 3*q>=n: return q
def choose(n):
    for p in range(2*n-1,n,-1):
        if not isp(p): continue
        k=2*n-p
        if 2*k>n+2: return None
        ex={}
        ok=True
        for (al,x,y) in bad(n,k):
            q=bigprime(n,al) or bigprime(n,p-al)
            if q is None: ok=False;break
            ex[al]=q
        if ok: return p,ex
def cert(n,name=None):
    r=choose(n)
    if r is None: return None
    p,ex=r; k=2*n-p; lo=n-k+1
    L=["theorem %s : %s := by"%(name or "r5b_cert_%d"%n, stmt(n)),
       "  refine ⟨%d, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩"%p,
       "  intro α h1 h2"]
    for al,q in sorted(ex.items()):
        L+=["  by_cases e%d : α = %d"%(al,al),
            "  · left",
            "    exact ⟨%d, by norm_num, by norm_num, by subst e%d; norm_num⟩"%(q,al)]
    xL=lo//(n-lo)+1; xU=isqrt(n)
    while xU*xU+xU>n-1: xU-=1
    L+=["  right",
        "  intro x y hxy hd",
        "  obtain ⟨m, hm⟩ := hd",
        "  by_contra hc",
        "  have hc' : α * y < %d * x := by omega"%n,
        "  have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)",
        "  have b1 : %d * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)"%lo,
        "  have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy",
        "  have b2' : α * (x + 1) = α * x + α := by ring",
        "  have b3 : %d * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)"%lo,
        "  have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy",
        "  have b4' : x * (x + 1) = x * x + x := by ring",
        "  have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0",
        "  have x1 : %d ≤ x := by omega"%xL,
        "  have x2 : x ≤ %d := by"%xU,
        "    by_contra h",
        "    have : %d * %d ≤ x * x := Nat.mul_le_mul (by omega) (by omega)"%(xU+1,xU+1),
        "    omega"]
    if xL>xU:
        L+=["  omega"]
    else:
        L+=["  interval_cases x"]
        for x in range(xL,xU+1):
            ymax=(n*x-1)//lo
            if ymax<=x: L+=["  · omega"]
            else:
                L+=["  · have y2 : y ≤ %d := by omega"%ymax,
                    "    interval_cases y <;> omega"]
    return p,ex,"\n".join(L)+"\n"
if __name__=="__main__":
    for n in [int(a) for a in sys.argv[1:]]:
        p,ex,src=cert(n)
        open("Cert/r5b_cert_%d.lean"%n,"w").write("import Mathlib\n\n/-- 402-R5-b. Generalised-criterion certificate for n = %d: window prime %d%s. -/\n"%(n,p,"" if not ex else ", excluded α "+", ".join("%d (prime %d ≥ n/3 divides α·(p−α))"%(a,q) for a,q in ex.items()))+src)
        print(n,p,ex)
