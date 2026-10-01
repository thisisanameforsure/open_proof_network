import Mathlib
import Nodes.«spec-ffd3137a».Context

/-- erdos-1050, hole `hpint` of the skeleton on erdos-1050--h1-v2--h3 (graph PR #253): a closed form
for the Padé numerator coefficient p_k = ∑_{j<k} Qc n j / (2^(k-j) - 1), k ≤ n (the j = k term is
0 in ℚ). It is the regular part at z = 2^k of the rational function ∑_j Qc n j / (z/2^j - 1), whose
product form is spec-f2b55478's, corrected for the terms j > k that p_k leaves out. Every term on the
right has 2-adic valuation at least k(k-1)/2, which is the 2-adic half of `hpint`. Checked exactly
(Python fractions) for 1 ≤ n ≤ 13 and every k ≤ n, and with 2 replaced by 3 and 5. -/
theorem erdos_1050_pade_numerator_closed_form : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
    ∀ n k : ℕ, k ≤ n →
      ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
        Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
            ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
            ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
          ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
  have lag_test : ∀ (n j : ℕ), j ≤ n →
        (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
          ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
        (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
        ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) := by
    intro n j hj
    have hpos : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
      intro s
      have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
        calc (2 : ℚ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    -- (b) the nodes below j
    have hb : ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) =
        (2 : ℚ) ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
      have h1 : ∀ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) = 2 ^ l * ((2 : ℚ) ^ (j - l) - 1) := by
        intro l hl
        have hl' := Finset.mem_range.mp hl
        have : (2 : ℚ) ^ j = 2 ^ l * 2 ^ (j - l) := by rw [← pow_add]; congr 1; omega
        rw [this]; ring
      rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
        Finset.sum_range_id]
      congr 1
      rw [← Finset.prod_range_reflect]
      refine Finset.prod_congr rfl (fun s hs => ?_)
      have hs' := Finset.mem_range.mp hs
      congr 2
      omega
    -- (c) the nodes above j
    have hc : ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
        (-(2 : ℚ) ^ j) ^ (n - j) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
      calc ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s))
          = ∏ s ∈ Finset.range (n - j), ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (s + 1) - 1)) := by
            refine Finset.prod_congr rfl (fun s _ => ?_)
            rw [show j + 1 + s = j + (s + 1) by omega, pow_add]
            ring
        _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
    -- (d) the right side
    have hd : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) =
        (-(2 : ℚ) ^ j) ^ n * ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
      calc ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i))
          = ∏ i ∈ Finset.range n, ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (n + 1 + i - j) - 1)) := by
            refine Finset.prod_congr rfl (fun i _ => ?_)
            rw [show n + 1 + i = j + (n + 1 + i - j) by omega, pow_add, Nat.add_sub_cancel_left]
            ring
        _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
    -- (e) the q-factorial splits at j
    have he : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) *
        ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
        ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
      have hn : n = (n - j) + j := by omega
      conv_rhs => rw [hn]
      rw [Finset.prod_range_add, mul_comm]
      congr 1
      rw [← Finset.prod_range_reflect]
      refine Finset.prod_congr rfl (fun t ht => ?_)
      have ht' := Finset.mem_range.mp ht
      congr 2
      omega
    -- (f) reflect the second Gaussian binomial's numerator
    have hf : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) =
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
      rw [← Finset.prod_range_reflect]
      refine Finset.prod_congr rfl (fun i hi => ?_)
      have hi' := Finset.mem_range.mp hi
      congr 2
      omega
    have hF : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
      Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
    have hB : ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
      Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
    have hjj : j * j = j * (j - 1) / 2 + j * (j - 1) / 2 + j := by
      have h2 := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self j)
      rcases j with _ | j
      · simp
      · simp only [Nat.add_sub_cancel] at h2 ⊢
        linarith
    have hpow : (-(2 : ℚ) ^ j) ^ n = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j *
        (-(2 : ℚ) ^ j) ^ (n - j) := by
      rw [show n = j + (n - j) by omega, pow_add, Nat.add_sub_cancel_left, neg_pow, ← pow_mul, hjj,
        pow_add, pow_add]
      ring
    rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hb, hc, hd, hf, hpow]
    field_simp
    rw [← he]
    ring
  open Polynomial in
  have pf_test : ∀ (n : ℕ) (x y w : ℕ → ℚ), (∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b) →
        (∀ j ∈ Finset.range (n + 1),
          w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) →
        (∑ j ∈ Finset.range (n + 1), Polynomial.C (w j) * ∏ l ∈ (Finset.range (n + 1)).erase j, (X - Polynomial.C (x l))) =
        ∏ i ∈ Finset.range n, (X - Polynomial.C (y i)) := by
    intro n x y w hx hw
    set s := Finset.range (n + 1) with hs
    have hL : (∑ j ∈ s, Polynomial.C (w j) * ∏ l ∈ s.erase j, (X - Polynomial.C (x l))).natDegree ≤ n := by
      refine natDegree_sum_le_of_forall_le _ _ (fun j hj => ?_)
      refine (natDegree_C_mul_le _ _).trans ((natDegree_prod_le _ _).trans ?_)
      simp only [natDegree_X_sub_C, Finset.sum_const, smul_eq_mul, mul_one]
      rw [Finset.card_erase_of_mem hj, hs, Finset.card_range]
      omega
    have hE : (∏ i ∈ Finset.range n, (X - Polynomial.C (y i))).natDegree ≤ n := by
      refine (natDegree_prod_le _ _).trans ?_
      simp [natDegree_X_sub_C]
    apply Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq (s.image x)
    · rw [Finset.card_image_of_injOn (fun a ha b hb h => hx a ha b hb h), hs, Finset.card_range]
      refine lt_of_le_of_lt (degree_sub_le _ _) (max_lt ?_ ?_)
      · exact lt_of_le_of_lt (degree_le_of_natDegree_le hL) (by exact_mod_cast Nat.lt_succ_self n)
      · exact lt_of_le_of_lt (degree_le_of_natDegree_le hE) (by exact_mod_cast Nat.lt_succ_self n)
    · intro z hz
      obtain ⟨j, hj, rfl⟩ := Finset.mem_image.mp hz
      simp only [eval_finset_sum, eval_mul, eval_C, eval_prod, eval_sub, eval_X]
      rw [Finset.sum_eq_single j]
      · exact hw j hj
      · intro i hi hij
        rw [Finset.prod_eq_zero (i := j) (Finset.mem_erase.mpr ⟨Ne.symm hij, hj⟩) (sub_self _), mul_zero]
      · intro hj'; exact absurd hj hj'
  open Polynomial in
  have pf2_test : ∀ (n k : ℕ), k ∈ Finset.range (n + 1) → ∀ (x y w : ℕ → ℚ),
        (∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b) →
        (∀ i ∈ Finset.range n, x k - y i ≠ 0) →
        (∀ j ∈ Finset.range (n + 1),
          w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) →
        ∑ j ∈ (Finset.range (n + 1)).erase k, w j / (x k - x j) =
        w k * (∑ i ∈ Finset.range n, 1 / (x k - y i) -
          ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / (x k - x l)) := by
    intro n k hk x y w hx hxy hw
    have hLE := pf_test n x y w hx hw
    set s := Finset.range (n + 1) with hs
    have hne : ∀ j ∈ s, j ≠ k → x k - x j ≠ 0 := by
      intro j hj hjk h
      exact hjk (hx j hj k hk (sub_eq_zero.mp h).symm)
    set P := ∏ l ∈ s.erase k, (x k - x l) with hP
    have hP0 : P ≠ 0 := Finset.prod_ne_zero_iff.mpr (fun l hl =>
      hne l (Finset.mem_of_mem_erase hl) (Finset.ne_of_mem_erase hl))
    have hd := congrArg (fun p => (derivative p).eval (x k)) hLE
    simp only [derivative_sum, derivative_mul, derivative_C, zero_mul, zero_add, derivative_prod_finset,
      derivative_sub, derivative_X, sub_zero, mul_one, eval_finset_sum, eval_mul, eval_C, eval_prod,
      eval_sub, eval_X] at hd
    -- the terms j ≠ k
    have h1 : ∀ j ∈ s.erase k, (∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l)) =
        P * (1 / (x k - x j)) := by
      intro j hj
      have hjs := Finset.mem_of_mem_erase hj
      have hjk := Finset.ne_of_mem_erase hj
      have hks : k ∈ s.erase j := Finset.mem_erase.mpr ⟨Ne.symm hjk, hk⟩
      rw [Finset.sum_eq_single k]
      · have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hj
        rw [Finset.erase_right_comm]
        field_simp [hne j hjs hjk]
        rw [hP, ← this]
        ring
      · intro m hm hmk
        exact Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hmk, hks⟩) (sub_self _)
      · intro h; exact absurd hks h
    -- the term j = k
    have h2 : (∑ m ∈ s.erase k, ∏ l ∈ (s.erase k).erase m, (x k - x l)) =
        P * ∑ m ∈ s.erase k, 1 / (x k - x m) := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun m hm => ?_)
      have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hm
      field_simp [hne m (Finset.mem_of_mem_erase hm) (Finset.ne_of_mem_erase hm)]
      rw [hP, ← this]
      ring
    -- the right side
    have h3 : (∑ i ∈ Finset.range n, ∏ i' ∈ (Finset.range n).erase i, (x k - y i')) =
        (w k * P) * ∑ i ∈ Finset.range n, 1 / (x k - y i) := by
      rw [hw k hk, Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i hi => ?_)
      have := Finset.mul_prod_erase (Finset.range n) (fun i' => x k - y i') hi
      field_simp [hxy i hi]
      rw [← this]
      ring
    rw [← Finset.add_sum_erase s _ hk, h2, h3] at hd
    have h1' : ∑ j ∈ s.erase k, w j * ∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l) =
        P * ∑ j ∈ s.erase k, w j / (x k - x j) := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun j hj => ?_)
      rw [h1 j hj]
      ring
    rw [h1'] at hd
    apply mul_left_cancel₀ hP0
    linear_combination hd
  intro Qc hQc n k hk
  have hc : ∀ j, Qc n j = ((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
        ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
    intro j; rw [hQc]
  have hk1 : k ∈ Finset.range (n + 1) := Finset.mem_range.mpr (by omega)
  have h2 : ∀ m : ℕ, (2 : ℚ) ^ m ≠ 0 := fun m => by positivity
  have hs1 : ∀ b : ℕ, (2 : ℚ) ^ (b + 1) - 1 ≠ 0 := by
    intro b
    have : (2 : ℚ) ≤ 2 ^ (b + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (b + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  have hs1' : ∀ b : ℕ, (1 : ℚ) - 2 ^ (b + 1) ≠ 0 := fun b h => hs1 b (by linarith)
  have hinj : ∀ a b : ℕ, (2 : ℚ) ^ a = 2 ^ b → a = b := by
    intro a b h
    have : (2 : ℕ) ^ a = 2 ^ b := by exact_mod_cast h
    exact Nat.pow_right_injective (le_refl 2) this
  have hx : ∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1),
      (fun l : ℕ => (2 : ℚ) ^ l) a = (fun l : ℕ => (2 : ℚ) ^ l) b → a = b :=
    fun a _ b _ h => hinj a b h
  have hxy : ∀ i ∈ Finset.range n,
      (fun l : ℕ => (2 : ℚ) ^ l) k - (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i)) i ≠ 0 := by
    intro i _ h
    have := hinj _ _ (sub_eq_zero.mp h)
    omega
  have hw : ∀ j ∈ Finset.range (n + 1),
      (fun j => Qc n j * (2 : ℚ) ^ j) j *
        ∏ l ∈ (Finset.range (n + 1)).erase j, ((fun l : ℕ => (2 : ℚ) ^ l) j - (fun l : ℕ => (2 : ℚ) ^ l) l) =
      ∏ i ∈ Finset.range n, ((fun l : ℕ => (2 : ℚ) ^ l) j - (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i)) i) := by
    intro j hj
    have hjn : j ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hj)
    simp only []
    let g : ℕ → ℚ := fun l => if l = j then 1 else (2 : ℚ) ^ j - 2 ^ l
    have e1 : ∏ l ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ l) =
        ∏ l ∈ (Finset.range (n + 1)).erase j, g l :=
      Finset.prod_congr rfl (fun l hl => by simp only [g, if_neg (Finset.ne_of_mem_erase hl)])
    have e2 : ∏ l ∈ (Finset.range (n + 1)).erase j, g l = ∏ l ∈ Finset.range (n + 1), g l :=
      Finset.prod_erase _ (if_pos rfl)
    have e3 : ∏ l ∈ Finset.range (n + 1), g l =
        (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
          ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) := by
      rw [show n + 1 = (j + 1) + (n - j) by omega, Finset.prod_range_add, Finset.prod_range_succ]
      have ga : ∏ l ∈ Finset.range j, g l = ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) :=
        Finset.prod_congr rfl (fun l hl => by
          have := Finset.mem_range.mp hl
          simp only [g, if_neg (show l ≠ j by omega)])
      have gb : ∏ s ∈ Finset.range (n - j), g (j + 1 + s) =
          ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) :=
        Finset.prod_congr rfl (fun s _ => by simp only [g, if_neg (show j + 1 + s ≠ j by omega)])
      rw [ga, gb, show g j = 1 from if_pos rfl, mul_one]
    rw [e1, e2, e3, ← lag_test n j hjn, hc j]
    ring
  have hpf := pf2_test n k hk1 (fun l : ℕ => (2 : ℚ) ^ l) (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i))
    (fun j => Qc n j * (2 : ℚ) ^ j) hx hxy hw
  beta_reduce at hpf
  have hpk : ∀ j, j < k → (2 : ℚ) ^ (k - j) - 1 ≠ 0 := by
    intro j hj
    rw [show k - j = (k - j - 1) + 1 by omega]
    exact hs1 _
  -- T0: the j = k term of the statement's sum is 0
  have T0 : ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
      ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
    rw [Finset.sum_range_succ, Nat.sub_self, pow_zero, sub_self, div_zero, add_zero]
  -- T1: the left side of hpf
  have T1 : ∑ j ∈ (Finset.range (n + 1)).erase k, Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
      ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) -
        ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    let G : ℕ → ℚ := fun j => if j = k then 0 else Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j)
    have e1 : ∑ j ∈ (Finset.range (n + 1)).erase k, Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
        ∑ j ∈ (Finset.range (n + 1)).erase k, G j :=
      Finset.sum_congr rfl (fun j hj => by simp only [G, if_neg (Finset.ne_of_mem_erase hj)])
    rw [e1, Finset.sum_erase _ (show G k = 0 from if_pos rfl),
      show n + 1 = (k + 1) + (n - k) by omega, Finset.sum_range_add, Finset.sum_range_succ]
    have ga : ∑ j ∈ Finset.range k, G j = ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
      refine Finset.sum_congr rfl (fun j hj => ?_)
      have hjk := Finset.mem_range.mp hj
      simp only [G, show j ≠ k by omega, if_false]
      rw [show (2 : ℚ) ^ k = 2 ^ j * 2 ^ (k - j) by rw [← pow_add]; congr 1; omega]
      field_simp [h2 j, hpk j hjk]
    have gb : ∑ b ∈ Finset.range (n - k), G (k + 1 + b) =
        -∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
      rw [← Finset.sum_neg_distrib]
      refine Finset.sum_congr rfl (fun b _ => ?_)
      simp only [G]
      rw [if_neg (by omega : k + 1 + b ≠ k), show k + 1 + b = k + b + 1 by omega]
      rw [show (2 : ℚ) ^ (k + b + 1) = 2 ^ k * 2 ^ (b + 1) by
        rw [show k + b + 1 = k + (b + 1) by omega, pow_add]]
      have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (b + 1) = -(2 ^ k * (2 ^ (b + 1) - 1)) := by ring
      rw [this]
      field_simp [h2 k, hs1 b]
    rw [ga, gb, show G k = 0 from if_pos rfl, add_zero]
    ring
  -- T2: the nodes 2^(n+1+i)
  have T2 : Qc n k * (2 : ℚ) ^ k * ∑ i ∈ Finset.range n, 1 / ((2 : ℚ) ^ k - 2 ^ (n + 1 + i)) =
      Qc n k * ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) := by
    rw [mul_assoc, Finset.mul_sum, Finset.mul_sum, Finset.mul_sum]
    refine Finset.sum_congr rfl (fun i _ => ?_)
    have e : n + 1 + i - k = (n - k + i) + 1 := by omega
    rw [show (2 : ℚ) ^ (n + 1 + i) = 2 ^ k * 2 ^ (n + 1 + i - k) by rw [← pow_add]; congr 1; omega, e]
    have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (n - k + i + 1) = 2 ^ k * (1 - 2 ^ (n - k + i + 1)) := by ring
    rw [this]
    field_simp [h2 k, hs1' (n - k + i)] <;> ring
  -- T3: the other nodes 2^l, l ≠ k
  have T3a : ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
      ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) +
        ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) := by
    let H : ℕ → ℚ := fun l => if l = k then 0 else 1 / ((2 : ℚ) ^ k - 2 ^ l)
    have e1 : ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
        ∑ l ∈ (Finset.range (n + 1)).erase k, H l :=
      Finset.sum_congr rfl (fun l hl => by simp only [H, if_neg (Finset.ne_of_mem_erase hl)])
    rw [e1, Finset.sum_erase _ (show H k = 0 from if_pos rfl),
      show n + 1 = (k + 1) + (n - k) by omega, Finset.sum_range_add, Finset.sum_range_succ]
    have ha : ∑ l ∈ Finset.range k, H l = ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) :=
      Finset.sum_congr rfl (fun l hl => by
        have := Finset.mem_range.mp hl
        simp only [H, if_neg (show l ≠ k by omega)])
    have hb : ∑ b ∈ Finset.range (n - k), H (k + 1 + b) =
        ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) :=
      Finset.sum_congr rfl (fun b _ => by simp only [H, if_neg (show k + 1 + b ≠ k by omega)])
    rw [ha, hb, show H k = 0 from if_pos rfl, add_zero]
  have T3b : (2 : ℚ) ^ k * ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
      ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    rw [Finset.mul_sum]
    have e1 : ∀ l ∈ Finset.range k, (2 : ℚ) ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ l)) =
        (2 : ℚ) ^ (k - l) / ((2 : ℚ) ^ (k - l) - 1) := by
      intro l hl
      have hlk := Finset.mem_range.mp hl
      rw [show (2 : ℚ) ^ k = 2 ^ l * 2 ^ (k - l) by rw [← pow_add]; congr 1; omega]
      field_simp [h2 l, hpk l hlk] <;> ring
    rw [Finset.sum_congr rfl e1, ← Finset.sum_range_reflect]
    refine Finset.sum_congr rfl (fun b hb => ?_)
    have := Finset.mem_range.mp hb
    rw [show k - (k - 1 - b) = b + 1 by omega]
  have T3c : (2 : ℚ) ^ k * ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) =
      ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) := by
    rw [Finset.mul_sum]
    refine Finset.sum_congr rfl (fun b _ => ?_)
    rw [show (2 : ℚ) ^ (k + 1 + b) = 2 ^ k * 2 ^ (b + 1) by
      rw [show k + 1 + b = k + (b + 1) by omega, pow_add]]
    have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (b + 1) = 2 ^ k * (1 - 2 ^ (b + 1)) := by ring
    rw [this]
    field_simp [h2 k, hs1' b] <;> ring
  have T3 : Qc n k * (2 : ℚ) ^ k * ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
      Qc n k * (∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) +
        ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) := by
    rw [T3a]
    linear_combination (Qc n k) * T3b + (Qc n k) * T3c
  rw [T0]
  linear_combination hpf - T1 + T2 - T3
