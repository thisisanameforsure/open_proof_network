# 402-R6-b: chain of window primes checked by ONE kernel evaluation (decide +kernel), primality by gcd with a primorial.
import sys, math
def sieve(N):
    s=bytearray([1])*(N+1); s[0]=s[1]=0
    for i in range(2,int(N**.5)+1):
        if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
    return s
def chain(lo0,hi0,S):
    L=[]; lo=lo0
    while lo<=hi0:
        p=2*lo-1
        while not S[p]: p-=1
        s=math.isqrt(lo)
        assert 2*lo-p<=s, ("no window prime at",lo)
        hi=min(p-1,(p+s)//2)
        L.append((p,hi)); lo=hi+1
    return L
def primorial(B,S): 
    P=1
    for q in range(2,B):
        if S[q]: P*=q
    return P
STMT_SIMPLE="∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n"
def lean(name,lo0,hi0,count=False):
    S=sieve(2*hi0+10); L=chain(lo0,hi0,S); B=math.isqrt(max(p for p,_ in L))+2; P=primorial(B,S); bound=B*B
    assert all(p<bound for p,_ in L)
    lst=", ".join("(%d, %d)"%x for x in L)
    out=f"""import Mathlib

{"#count_heartbeats in" if count else ""}
/-- 402-R6-b. Window primes for {lo0} ≤ n ≤ {hi0}: a chain of {len(L)} primes (p, hi), each serving the sizes from the
previous hi + 1 up to its own hi. Primality of each p < {B}² is `Nat.gcd p P = 1`, P the product of the primes
below {B}; the whole chain is checked by one kernel evaluation (`decide +kernel`, no `native_decide`). -/
theorem {name} : ∀ n : ℕ, {lo0} ≤ n → n ≤ {hi0} →
    {STMT_SIMPLE} := by
  have small : ∀ q : ℕ, q < {B} → 2 ≤ q → Nat.gcd q {P} ≠ 1 := by
    decide +kernel
  have hP : ∀ p : ℕ, 1 < p → p < {bound} → Nat.gcd p {P} = 1 → p.Prime := by
    intro p h1 h2 hg
    by_contra hnp
    have hq : p.minFac.Prime := Nat.minFac_prime (by omega)
    have hsq : p.minFac ^ 2 ≤ p := Nat.minFac_sq_le_self (by omega) hnp
    have hlt : p.minFac < {B} := by nlinarith
    apply small _ hlt hq.two_le
    have hd := Nat.gcd_dvd_gcd_of_dvd_left {P} (Nat.minFac_dvd p)
    rw [hg] at hd
    exact Nat.eq_one_of_dvd_one hd
  have key : ∀ Q : ℕ, (∀ p : ℕ, 1 < p → p < {bound} → Nat.gcd p Q = 1 → p.Prime) →
      ∀ (L : List (ℕ × ℕ)) (a : ℕ),
      List.foldr (fun (x : ℕ × ℕ) (f : ℕ → Bool) (lo : ℕ) =>
        (decide (1 < x.1) && decide (x.1 < {bound}) && decide (Nat.gcd x.1 Q = 1) && decide (x.2 < x.1) &&
          decide (x.1 < 2 * lo) && decide ((2 * x.2 - x.1) * (2 * x.2 - x.1) ≤ lo)) && f (x.2 + 1))
        (fun lo => decide ({hi0} < lo)) L a = true →
      ∀ n : ℕ, a ≤ n → n ≤ {hi0} → {STMT_SIMPLE} := by
    intro Q hQ L
    induction L with
    | nil =>
      intro a h n h1 h2
      simp only [List.foldr_nil, decide_eq_true_eq] at h
      omega
    | cons x L ih =>
      intro a h n h1 h2
      simp only [List.foldr_cons, Bool.and_eq_true, decide_eq_true_eq] at h
      obtain ⟨⟨⟨⟨⟨⟨c1, c2⟩, c3⟩, c4⟩, c5⟩, c6⟩, c7⟩ := h
      by_cases hn : n ≤ x.2
      · refine ⟨x.1, hQ x.1 c1 c2 c3, by omega, by omega, ?_⟩
        have h3 : 2 * n - x.1 ≤ 2 * x.2 - x.1 := by omega
        exact le_trans (Nat.mul_le_mul h3 h3) (le_trans c6 h1)
      · exact ih (x.2 + 1) c7 n (by omega) h2
  intro n hl hh
  exact key _ hP [{lst}] {lo0} (by decide +kernel) n hl hh
"""
    return out,L
if __name__=="__main__":
    lo,hi=int(sys.argv[1]),int(sys.argv[2])
    out,L=lean("r6b_window_%d_%d"%(lo,hi),lo,hi,count=len(sys.argv)>3)
    open("r6b_window_%d_%d%s.lean"%(lo,hi,"_hb" if len(sys.argv)>3 else ""),"w").write(out)
    print(len(L),"primes",len(out),"bytes")
