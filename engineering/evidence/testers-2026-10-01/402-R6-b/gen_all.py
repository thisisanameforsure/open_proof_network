# 402-R6-b: ONE declaration: for every n in [LO, HI] a prime with the hypotheses of r5b_gen_criterion exists.
import sys, math
from gen import sieve, chain, primorial, STMT_SIMPLE
R5="../402-R5-b/"
EXC=[14,18,48,61,62,63,74,105,111,153,165,270,677,678,679,680]
GEN=("∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2 ∧\n"
     "      ∀ α : ℕ, α < n → p < α + n →\n"
     "        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨\n"
     "        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y)")
def as_have(path):
    s=open(path).read()
    s=s[s.index("theorem "):].replace("theorem ","have ",1)
    return "\n".join(("  "+l if l.strip() else l) for l in s.rstrip().splitlines())+"\n"
def build(name,LO,HI,count=False,header=None,intro=True):
    S=sieve(2*HI+10)
    exc=[e for e in EXC if LO<=e<=HI]
    segs=[]; a=LO
    for e in exc+[HI+1]:
        if a<=e-1: segs.append((a,e-1))
        a=e+1
    chains=[chain(a,b,S) for a,b in segs]
    nprimes=sum(len(c) for c in chains)
    B=math.isqrt(max(p for c in chains for p,_ in c))+2; P=primorial(B,S); bound=B*B
    L=[]
    if header is None:
        L+=["import Mathlib","",("#count_heartbeats in\n" if count else "")+
        f"/-- 402-R6-b. For every size {LO} ≤ n ≤ {HI} there is a prime p satisfying the hypotheses of the generalised",
        f"criterion r5b_gen_criterion. {nprimes} window primes in {len(segs)} chains, each chain checked by one kernel",
        f"evaluation (`decide +kernel`; primality of p < {B}² is `Nat.gcd p P = 1`, P the product of the primes below {B}),",
        f"the bridge from the simple window, and one divisor-gap certificate for each of the {len(exc)} exceptional n. -/",
        f"theorem {name} : ∀ n : ℕ, {LO} ≤ n → n ≤ {HI} →\n    "+GEN+" := by"]
    else: L+=[header]
    Q2=primorial(30,S)
    assert all(p>=11 for c in chains for p,_ in c)
    TEST=f"(decide (1 < p) && (decide (p < 49) && decide (Nat.gcd p 30 = 1) || decide (p < 900) && decide (Nat.gcd p {Q2} = 1) || decide (p < {bound}) && decide (Nat.gcd p {P} = 1)))"
    L.append(f"""  have lvl : ∀ B Q : ℕ, (∀ q : ℕ, q < B → 2 ≤ q → Nat.gcd q Q ≠ 1) →
      ∀ p : ℕ, 1 < p → p < B * B → Nat.gcd p Q = 1 → p.Prime := by
    intro B Q small p h1 h2 hg
    by_contra hnp
    have hq : p.minFac.Prime := Nat.minFac_prime (by omega)
    have hsq : p.minFac ^ 2 ≤ p := Nat.minFac_sq_le_self (by omega) hnp
    have hlt : p.minFac < B := by nlinarith
    apply small _ hlt hq.two_le
    have hd := Nat.gcd_dvd_gcd_of_dvd_left Q (Nat.minFac_dvd p)
    rw [hg] at hd
    exact Nat.eq_one_of_dvd_one hd
  have hP : ∀ p : ℕ, {TEST} = true → p.Prime := by
    intro p h
    simp only [Bool.and_eq_true, Bool.or_eq_true, decide_eq_true_eq] at h
    obtain ⟨h1, (⟨h2, h3⟩ | ⟨h2, h3⟩) | ⟨h2, h3⟩⟩ := h
    · exact lvl 7 30 (by decide +kernel) p h1 h2 h3
    · exact lvl 30 {Q2} (by decide +kernel) p h1 h2 h3
    · exact lvl {B} {P} (by decide +kernel) p h1 h2 h3
  have key : ∀ t : ℕ → Bool, (∀ p : ℕ, t p = true → p.Prime) →
      ∀ (b : ℕ) (L : List (ℕ × ℕ)) (a : ℕ),
      List.foldr (fun (x : ℕ × ℕ) (f : ℕ → Bool) (lo : ℕ) =>
        (t x.1 && decide (x.2 < x.1) &&
          decide (x.1 < 2 * lo) && decide ((2 * x.2 - x.1) * (2 * x.2 - x.1) ≤ lo)) && f (x.2 + 1))
        (fun lo => decide (b < lo)) L a = true →
      ∀ n : ℕ, a ≤ n → n ≤ b → {STMT_SIMPLE} := by
    intro t ht b L
    induction L with
    | nil =>
      intro a h n h1 h2
      simp only [List.foldr_nil, decide_eq_true_eq] at h
      omega
    | cons x L ih =>
      intro a h n h1 h2
      simp only [List.foldr_cons, Bool.and_eq_true, decide_eq_true_eq] at h
      obtain ⟨⟨⟨⟨c1, c4⟩, c5⟩, c6⟩, c7⟩ := h
      by_cases hn : n ≤ x.2
      · refine ⟨x.1, ht x.1 c1, by omega, by omega, ?_⟩
        have h3 : 2 * n - x.1 ≤ 2 * x.2 - x.1 := by omega
        exact le_trans (Nat.mul_le_mul h3 h3) (le_trans c6 h1)
      · exact ih (x.2 + 1) c7 n (by omega) h2""")
    L.append(as_have(R5+"Bridge.lean").rstrip())
    L.append("""  have fin : ∀ n : ℕ, (%s) →
      %s := by
    intro n hw
    obtain ⟨p, hp, a, b, c⟩ := hw
    have br := r5b_bridge n p a b c
    exact ⟨p, hp, a, b, br.1, br.2⟩"""%(STMT_SIMPLE,GEN.replace("\n","\n  ")))
    for e in exc: L.append(as_have(R5+"Cert/r5b_cert_%d.lean"%e).rstrip())
    if intro: L.append("  intro n hl hh")
    for e in exc:
        L+=["  by_cases e%d : n = %d"%(e,e),"  · subst e%d"%e,"    exact r5b_cert_%d"%e]
    for (a,b),c in zip(segs,chains):
        lst=", ".join("(%d, %d)"%x for x in c)
        L+=["  by_cases s%d : n ≤ %d"%(b,b),
            "  · exact fin n (key (fun p => %s) hP %d [%s] %d (by decide +kernel) n (by omega) s%d)"%(TEST,b,lst,a,b)]
    L.append("  omega")
    return "\n".join(L)+"\n", nprimes, len(segs), len(exc)
if __name__=="__main__":
    lo,hi=int(sys.argv[1]),int(sys.argv[2]); c=len(sys.argv)>3
    out,npr,ns,ne=build("r6b_gen_%d_%d"%(lo,hi),lo,hi,count=c)
    fn="r6b_gen_%d_%d%s.lean"%(lo,hi,"_hb" if c else "")
    open(fn,"w").write(out); print(fn,npr,"primes",ns,"chains",ne,"certs",len(out),"bytes")
