import Mathlib
theorem T (hM : ∃ C : ℝ, ∀ n : ℕ, |∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) - Real.log n| ≤ C) :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C := by
  obtain ⟨C, hC⟩ := hM
  have hC0 : 0 ≤ C := (abs_nonneg _).trans (hC 0)
  have hl2 : 0 < Real.log 2 := Real.log_pos (by norm_num)
  have hL : ∀ n : ℕ, 2 ≤ n → Real.log 2 ≤ Real.log (n : ℝ) := fun n hn =>
    Real.log_le_log (by norm_num) (by exact_mod_cast hn)
  have htel : ∀ f : ℕ → ℝ, ∀ x : ℕ, 2 ≤ x →
      ∑ n ∈ Finset.Ico 2 x, (f (n + 1) - f n) = f x - f 2 := by
    intro f x hx
    induction x, hx using Nat.le_induction with
    | base => simp
    | succ x hx ih => rw [Finset.sum_Ico_succ_top hx, ih]; ring
  have htel' : ∀ f : ℕ → ℝ, ∀ x : ℕ, 2 ≤ x →
      ∑ n ∈ Finset.Ico 2 x, (f n - f (n + 1)) = f 2 - f x := by
    intro f x hx
    induction x, hx using Nat.le_induction with
    | base => simp
    | succ x hx ih => rw [Finset.sum_Ico_succ_top hx, ih]; ring
  have habel : ∀ x : ℕ, 2 ≤ x →
      ∑ p ∈ Nat.primesLE x, (1 : ℝ) / p
        = (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ)) / Real.log (x : ℝ)
          + ∑ n ∈ Finset.Ico 2 x, (∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
              * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ)) := by
    intro x hx
    induction x, hx using Nat.le_induction with
    | base =>
      have h2 : Nat.primesLE 2 = {2} := by decide
      have : Real.log 2 ≠ 0 := hl2.ne'
      simp [h2]
      field_simp
    | succ x hx ih =>
      have ha : Real.log (x : ℝ) ≠ 0 := (lt_of_lt_of_le hl2 (hL x hx)).ne'
      have hb : Real.log ((x + 1 : ℕ) : ℝ) ≠ 0 :=
        (lt_of_lt_of_le hl2 (hL (x + 1) (by omega))).ne'
      have hnot : x + 1 ∉ Nat.primesLE x := fun h => by
        have := (Nat.mem_primesLE.mp h).1
        omega
      have hx1 : ((x + 1 : ℕ) : ℝ) ≠ 0 := by positivity
      rw [Finset.sum_Ico_succ_top hx, Nat.primesLE_succ]
      split_ifs with hp
      · rw [Finset.sum_insert hnot, Finset.sum_insert hnot, ih]
        field_simp
        ring
      · rw [ih]
        field_simp
        ring
  have hreal : ∀ a b A : ℝ, 0 < a → a ≤ b → b - a ≤ 1 → |A - a| ≤ C →
      0 ≤ 1 / a - 1 / b ∧
        |A * (1 / a - 1 / b) - (Real.log b - Real.log a)| ≤ (C + 1) * (1 / a - 1 / b) := by
    intro a b A ha0 hab hba hA
    have hb0 : 0 < b := ha0.trans_le hab
    have hd0 : 0 ≤ 1 / a - 1 / b := by
      rw [sub_nonneg]
      exact one_div_le_one_div_of_le ha0 hab
    have hv : Real.log b - Real.log a = Real.log (b / a) :=
      (Real.log_div hb0.ne' ha0.ne').symm
    have hlow := Real.one_sub_inv_le_log_of_pos (show 0 < b / a by positivity)
    have hup := Real.log_le_sub_one_of_pos (show 0 < b / a by positivity)
    have hR := abs_le.mp hA
    have hu : a * (1 / a - 1 / b) = 1 - (b / a)⁻¹ := by
      field_simp
    have hw : b / a - 1 - (1 - (b / a)⁻¹) = (b - a) * (1 / a - 1 / b) := by
      field_simp
    have hw2 : (b - a) * (1 / a - 1 / b) ≤ 1 * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hba hd0
    have h1 : -C * (1 / a - 1 / b) ≤ (A - a) * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hR.1 hd0
    have h2 : (A - a) * (1 / a - 1 / b) ≤ C * (1 / a - 1 / b) :=
      mul_le_mul_of_nonneg_right hR.2 hd0
    have e : A * (1 / a - 1 / b) - (Real.log b - Real.log a)
        = (A - a) * (1 / a - 1 / b) + (a * (1 / a - 1 / b) - Real.log (b / a)) := by
      rw [hv]
      ring
    refine ⟨hd0, ?_⟩
    rw [e, abs_le]
    constructor <;> nlinarith
  have hpt : ∀ n : ℕ, 2 ≤ n →
      |(∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
            * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ))
          - (Real.log (Real.log ((n + 1 : ℕ) : ℝ)) - Real.log (Real.log (n : ℝ)))|
        ≤ (C + 1) * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ)) := by
    intro n hn
    have hn0 : (0 : ℝ) < n := by exact_mod_cast (by omega : 0 < n)
    have hn1 : (0 : ℝ) < ((n + 1 : ℕ) : ℝ) := by positivity
    have hab : Real.log (n : ℝ) ≤ Real.log ((n + 1 : ℕ) : ℝ) :=
      Real.log_le_log hn0 (by push_cast; linarith)
    have hba : Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ) ≤ 1 := by
      have h1 : Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ)
          = Real.log (((n + 1 : ℕ) : ℝ) / n) := (Real.log_div hn1.ne' hn0.ne').symm
      have h2 := Real.log_le_sub_one_of_pos (show 0 < ((n + 1 : ℕ) : ℝ) / n by positivity)
      have h3 : ((n + 1 : ℕ) : ℝ) / n - 1 = 1 / n := by
        push_cast
        field_simp
        ring
      have h4 : (1 : ℝ) / n ≤ 1 := by
        rw [div_le_one hn0]
        exact_mod_cast (by omega : 1 ≤ n)
      linarith
    exact (hreal _ _ _ (lt_of_lt_of_le hl2 (hL n hn)) hab hba (hC n)).2
  refine ⟨1 + C / Real.log 2 + |Real.log (Real.log 2)| + (C + 1) / Real.log 2, by positivity, ?_⟩
  intro x hx
  have hLx : Real.log 2 ≤ Real.log (x : ℝ) := hL x hx
  have hLx0 : 0 < Real.log (x : ℝ) := hl2.trans_le hLx
  have hv := htel (fun n => Real.log (Real.log (n : ℝ))) x hx
  have hd := htel' (fun n => 1 / Real.log (n : ℝ)) x hx
  simp only [Nat.cast_ofNat] at hv hd
  have hsum : |∑ n ∈ Finset.Ico 2 x, ((∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ))
            * (1 / Real.log (n : ℝ) - 1 / Real.log ((n + 1 : ℕ) : ℝ))
          - (Real.log (Real.log ((n + 1 : ℕ) : ℝ)) - Real.log (Real.log (n : ℝ))))|
        ≤ (C + 1) / Real.log 2 := by
    refine (Finset.abs_sum_le_sum_abs _ _).trans ?_
    refine (Finset.sum_le_sum (fun n hn => hpt n (Finset.mem_Ico.mp hn).1)).trans ?_
    rw [← Finset.mul_sum, hd, div_eq_mul_one_div (C + 1)]
    have : 0 ≤ 1 / Real.log (x : ℝ) := by positivity
    nlinarith
  rw [Finset.sum_sub_distrib, hv] at hsum
  have hq : |(∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ) - Real.log (x : ℝ)) / Real.log (x : ℝ)|
      ≤ C / Real.log 2 := by
    rw [abs_div, abs_of_pos hLx0]
    calc _ ≤ C / Real.log (x : ℝ) := by gcongr; exact hC x
      _ ≤ C / Real.log 2 := by gcongr
  have e1 : (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ)) / Real.log (x : ℝ)
      = 1 + (∑ p ∈ Nat.primesLE x, Real.log p / (p : ℝ) - Real.log (x : ℝ)) / Real.log (x : ℝ) := by
    rw [sub_div, div_self hLx0.ne']
    ring
  have hab := habel x hx
  have h3 := abs_le.mp hsum
  have h4 := abs_le.mp hq
  have h5 := neg_abs_le (Real.log (Real.log 2))
  have h6 := le_abs_self (Real.log (Real.log 2))
  rw [abs_le]
  constructor <;> linarith
