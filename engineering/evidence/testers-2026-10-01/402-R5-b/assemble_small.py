# 402-R5-b: one declaration: for every n in [10,680] the hypotheses of r5b_gen_criterion hold for some prime p.
import re
from gencert import stmt
def as_have(path):
    s=open(path).read()
    s=s[s.index("theorem "):].replace("theorem ","have ",1)
    return "\n".join(("  "+l if l.strip() else l) for l in s.rstrip().splitlines())+"\n"
exc1=[14,18,48,61,62,63,74,105,111,153,165]; exc2=[270]; top=[677,678,679,680]
gen=stmt(0).replace("∃ p : ℕ, p.Prime ∧ 0 < p ∧ p < 2 * 0 ∧ 2 * (2 * 0 - p) ≤ 0 + 2","∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2").replace("α < 0 → p < α + 0","α < n → p < α + n").replace("0 ≤ 3 * q","n ≤ 3 * q").replace("0 * x","n * x")
assert " 0 " not in gen and "0 *" not in gen, gen

def build(name,lo,hi,win,winhi,ex_in,ex_top):
    L=["import Mathlib","",
    "/-- 402-R5-b. For every size %d ≤ n ≤ %d there is a prime p satisfying the hypotheses of the generalised"%(lo,hi),
    "criterion r5b_gen_criterion (window certificates + bridge for the non-exceptional n, one divisor-gap",
    "certificate for each exceptional n: %s). -/"%", ".join(map(str,ex_in+ex_top)),
    "theorem %s : ∀ n : ℕ, %d ≤ n → n ≤ %d →\n    "%(name,lo,hi)+gen.replace("\n","\n  ")+" := by"]
    L+=[as_have("Bridge.lean"),as_have("Window/%s.lean"%win)]
    for e in ex_in+ex_top: L.append(as_have("Cert/r5b_cert_%d.lean"%e))
    L.append("  intro n hl hh")
    for e in ex_in+ex_top:
        L+=["  by_cases e%d : n = %d"%(e,e),"  · subst e%d"%e,"    exact r5b_cert_%d"%e]
    L+=["  obtain ⟨p, hp, a, b, c⟩ := %s n hl (by omega) "%win+" ".join("e%d"%e for e in ex_in),
        "  have br := r5b_bridge n p a b c",
        "  exact ⟨p, hp, a, b, br.1, br.2⟩"]
    open(name[4:]+".lean","w").write("\n".join(L)+"\n")
build("r5b_small_10_228",10,228,"r5b_window_10_228",228,exc1,[])
build("r5b_small_229_680",229,680,"r5b_window_229_676",676,exc2,top)
