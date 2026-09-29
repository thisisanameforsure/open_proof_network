import Mathlib

theorem cauchy_fin (n : ℕ) (q a : ℕ → ℝ) (x A : ℝ) (hA : HasSum (fun s => a s * x ^ (s + 1)) A) :
    HasSum (fun K => ∑ j ∈ Finset.range (n + 1), if j < K then q j * a (K - j - 1) * x ^ K else 0)
      ((∑ j ∈ Finset.range (n + 1), q j * x ^ j) * A) := by
  rw [Finset.sum_mul]
  apply hasSum_sum
  intro j _
  have h := hA.mul_left (q j * x ^ j)
  rw [← hasSum_nat_add_iff' (j + 1)]
  have hz : ∑ i ∈ Finset.range (j + 1), (if j < i then q j * a (i - j - 1) * x ^ i else 0) = 0 :=
    Finset.sum_eq_zero (fun i hi => by
      have := Finset.mem_range.mp hi
      rw [if_neg (by omega)])
  rw [hz, sub_zero]
  have hfun : (fun s => if j < s + (j + 1) then q j * a (s + (j + 1) - j - 1) * x ^ (s + (j + 1)) else 0) =
      fun s => q j * x ^ j * (a s * x ^ (s + 1)) := by
    funext s
    rw [if_pos (by omega), show s + (j + 1) - j - 1 = s by omega, show s + (j + 1) = j + (s + 1) by ring, pow_add]
    ring
  rw [hfun]
  exact h
