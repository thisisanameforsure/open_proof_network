import Mathlib

theorem Opn.erdos_69_prime_term_geometric :
    ∀ p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) = ∑' k : ℕ, (1 / 2 : ℝ) ^ ((p : ℕ) * (k + 1)) := by
  intro p
  set r : ℝ := (1 / 2 : ℝ) ^ (p : ℕ) with hr
  have hr0 : 0 ≤ r := by positivity
  have hp : 1 ≤ (p : ℕ) := p.2.one_lt.le
  have hr1 : r < 1 := pow_lt_one₀ (by norm_num) (by norm_num) (by omega)
  have h2 : (1 : ℝ) < 2 ^ (p : ℕ) := one_lt_pow₀ (by norm_num) (by omega)
  have hterm : ∀ k : ℕ, (1 / 2 : ℝ) ^ ((p : ℕ) * (k + 1)) = r * r ^ k := by
    intro k
    rw [hr, ← pow_succ', ← pow_mul]
  simp_rw [hterm]
  rw [tsum_mul_left, tsum_geometric_of_lt_one hr0 hr1, hr, one_div_pow]
  have hne : (2 : ℝ) ^ (p : ℕ) - 1 ≠ 0 := by linarith
  have hne' : (2 : ℝ) ^ (p : ℕ) ≠ 0 := by positivity
  field_simp
