# 402-R5-b: builds GenCriterion.lean from 402-R4-c/CriterionSingle.lean by explicit, asserted replacements.
s=open('../402-R4-c/CriterionSingle.lean').read()
def rep(old,new,cnt=1):
    global s
    assert s.count(old)==cnt,(old,s.count(old))
    s=s.replace(old,new)
GAP="(∀ x y : ℕ, x < y → x * y ∣ %s → n * x ≤ %s * y)"
# 1. header
i=s.index('theorem r4c_criterion_single'); j=s.index('  obtain ⟨cls, hcls⟩')
s=s[:i]+'''theorem r5b_gen_criterion : ∀ (A : Finset ℕ), 0 ∉ A → ∀ p : ℕ, p.Prime → A.card < p →
    p < 2 * A.card → 2 * (2 * A.card - p) ≤ A.card + 2 →
    (∀ α : ℕ, α < A.card → p < α + A.card →
      (∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → A.card * x ≤ α * y)) →
    (∃ a ∈ A, ∃ b ∈ A, (a.gcd b : ℚ) ≤ (a : ℚ) / (A.card : ℚ)) ∨
      ∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ ∃ a ∈ A, q ∣ a := by
'''+s[j:]
i=s.index('/-- 402-R4-c. The prime criterion'); j=s.index('theorem r5b_gen_criterion')
s=s[:i]+'''/-- 402-R5-b. Generalised prime criterion for Graham's gcd problem (one declaration). The window
condition (2n − p)² ≤ n of 402-R4-c's r4c_criterion_single is replaced by what the rectangle lemma
actually uses: every α in the window (p − n, n) either lies in a shape {α, p − α} that carries a prime
q ≥ n/3 (second disjunct of the conclusion) or has no divisor pair x < y, x·y ∣ α, with α·y < n·x. -/
'''+s[j:]
# 2. arith
i=s.index('  -- 402-R4-c. Arithmetic heart'); j=s.index('  -- 402-R4-c. Rectangle lemma, coprime core')
s=s[:i]+'''  -- 402-R5-b. Arithmetic heart, generalised: the divisor-gap hypothesis on α is exactly what is needed.
  have r4c_arith (n α e1 e2 : ℕ) (hg : ∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y)
      (he : e1 * e2 ∣ α) (h1 : α * e1 < n * e2) (h4 : α * e2 < n * e1) : e1 = e2 := by
    rcases Nat.lt_trichotomy e1 e2 with h | h | h
    · have := hg e1 e2 h he
      omega
    · exact h
    · have := hg e2 e1 h (by rwa [Nat.mul_comm])
      omega

'''+s[j:]
# 3. rect core
rep("have r4c_rect_core (n k α β d1 d2 : ℕ) (hk : k * k ≤ n) (hα : n < α + k) (hβ : n < β + k)",
    "have r4c_rect_core (n α β d1 d2 : ℕ) (gα : %s) (gβ : %s)\n      (tα : n ≤ 2 * α)"%(GAP%('α','α'),GAP%('β','β')))
rep("""    have mα : Nat.gcd α d1 * Nat.gcd α d2 ≤ α := Nat.le_of_dvd α0
      (Nat.Coprime.mul_dvd_of_dvd_of_dvd ce (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _))
    have mβ : Nat.gcd β d1 * Nat.gcd β d2 ≤ β := Nat.le_of_dvd β0
      (Nat.Coprime.mul_dvd_of_dvd_of_dvd cf (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _))""",
"""    have mα : Nat.gcd α d1 * Nat.gcd α d2 ∣ α :=
      Nat.Coprime.mul_dvd_of_dvd_of_dvd ce (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _)
    have mβ : Nat.gcd β d1 * Nat.gcd β d2 ∣ β :=
      Nat.Coprime.mul_dvd_of_dvd_of_dvd cf (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _)""")
rep("r4c_arith n k α e1 e2 hk hα mα i1 i4","r4c_arith n α e1 e2 gα mα i1 i4")
rep("r4c_arith n k β f1 f2 hk hβ mβ i3 i2","r4c_arith n β f1 f2 gβ mβ i3 i2")
rep("""    have kα : k ≤ α := by
      by_contra hc
      have : (α + 1) * k ≤ k * k := Nat.mul_le_mul_right _ (by omega)
      nlinarith
""","")
# 4. rect
rep("have r4c_rect (n k α β u w : ℕ) (hk : k * k ≤ n) (hα : n < α + k) (hβ : n < β + k)",
    "have r4c_rect (n α β u w : ℕ) (gα : %s) (gβ : %s)\n      (tα : n ≤ 2 * α)"%(GAP%('α','α'),GAP%('β','β')))
rep("r4c_rect_core n k α β d1 d2 hk hα hβ α0","r4c_rect_core n α β d1 d2 gα gβ tα α0")
# 5. criterion
rep("""      (h2 : p < 2 * A.card) (h3 : (2 * A.card - p) * (2 * A.card - p) ≤ A.card) :
      ∃ a ∈ A, ∃ b ∈ A, A.card * Nat.gcd a b ≤ a := by
    by_contra hne
    push Not at hne
""","""      (h2 : p < 2 * A.card) (h3 : 2 * (2 * A.card - p) ≤ A.card + 2)
      (H : ∀ α : ℕ, α < A.card → p < α + A.card →
        (∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → A.card * x ≤ α * y)) :
      (∃ a ∈ A, ∃ b ∈ A, A.card * Nat.gcd a b ≤ a) ∨
        ∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ ∃ a ∈ A, q ∣ a := by
    by_contra hcon
    have hne : ∀ a ∈ A, ∀ b ∈ A, a < A.card * Nat.gcd a b := by
      intro a ha b hb
      by_contra h
      exact hcon (Or.inl ⟨a, ha, b, hb, by omega⟩)
    have hnq : ∀ q : ℕ, q.Prime → A.card ≤ 3 * q → ∀ a ∈ A, ¬ q ∣ a :=
      fun q hq h a ha hd => hcon (Or.inr ⟨q, hq, h, a, ha, hd⟩)
    clear hcon
""")
rep("      exact r4c_rect n (2 * n - p) α β u w h3 (by omega) (by omega) α0 β0 hco u0 w0 q1 q2 q3 q4\n",
"""      have tα : n ≤ 2 * α := by omega
      have Hα := H α αn (by omega)
      have Hβ := H β βn (by omega)
      have pα : p - α = β := by omega
      have pβ : p - β = α := by omega
      rw [pα] at Hα
      rw [pβ] at Hβ
      have excl : ∀ q : ℕ, q.Prime → n ≤ 3 * q → q ∣ α * β → False := by
        intro q hq hq3 hd
        rcases (Nat.Prime.dvd_mul hq).mp hd with h | h
        · exact hnq q hq hq3 (α * u) ha (Dvd.dvd.mul_right h u)
        · exact hnq q hq hq3 (β * u) ha' (Dvd.dvd.mul_right h u)
      have gα : ∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y := by
        rcases Hα with ⟨q, hq, h3q, hd⟩ | h
        · exact (excl q hq h3q hd).elim
        · exact h
      have gβ : ∀ x y : ℕ, x < y → x * y ∣ β → n * x ≤ β * y := by
        rcases Hβ with ⟨q, hq, h3q, hd⟩ | h
        · exact (excl q hq h3q (by rwa [Nat.mul_comm])).elim
        · exact h
      exact r4c_rect n α β u w gα gβ tα α0 β0 hco u0 w0 q1 q2 q3 q4
""")
# 6. tail
i=s.index("  intro A h0 p hp h1 h2 h3\n  obtain")
s=s[:i]+'''  intro A h0 p hp h1 h2 h3 H
  rcases r4c_criterion A h0 p hp h1 h2 h3 H with ⟨a, ha, b, hb, h⟩ | h
  · left
    refine ⟨a, ha, b, hb, ?_⟩
    have n0 : (0 : ℚ) < (A.card : ℚ) := by
      have : 0 < A.card := Finset.card_pos.mpr ⟨a, ha⟩
      exact_mod_cast this
    rw [le_div_iff₀ n0]
    have : a.gcd b * A.card ≤ a := by rw [Nat.mul_comm]; exact h
    exact_mod_cast this
  · exact Or.inr h
'''
s=s.replace("402-R4-c. THE CRITERION (Zaharescu's Proposition 1 in strict form)","402-R5-b (from 402-R4-c). THE GENERALISED CRITERION")
open('GenCriterion.lean','w').write(s)
