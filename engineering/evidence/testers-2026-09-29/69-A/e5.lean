import Mathlib

theorem closed_form_probe : ∀ (p m : ℕ), 0 < p →
    ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
      = 2 ^ (m % p) / (2 ^ p - 1) := by
  intro p m hp
  obtain ⟨s, hs⟩ : ∃ s, s = m % p := ⟨_, rfl⟩
  obtain ⟨Q, hQ⟩ : ∃ Q, Q = m / p := ⟨_, rfl⟩
  have hsp : s < p := hs ▸ Nat.mod_lt _ hp
  have hm : m = s + p * Q := by rw [hs, hQ]; exact (Nat.mod_add_div m p).symm
  rw [← hs]
  obtain ⟨k0, hk0⟩ : ∃ k0, k0 = p - 1 - s := ⟨_, rfl⟩
  have hdiv : ∀ k : ℕ, p ∣ m + (k + 1) ↔ ∃ t, k0 + p * t = k := by
    intro k
    constructor
    · rintro ⟨c, hc⟩
      have hcQ : Q < c := by
        have : p * Q < p * c := by omega
        exact Nat.lt_of_mul_lt_mul_left this
      obtain ⟨e, he⟩ : ∃ e, c = Q + 1 + e := ⟨c - Q - 1, by omega⟩
      refine ⟨e, ?_⟩
      rw [he, mul_add, mul_add, mul_one] at hc
      omega
    · rintro ⟨t, rfl⟩
      exact ⟨Q + 1 + t, by rw [mul_add, mul_add, mul_one]; omega⟩
  let f : ℕ → ℝ := fun k => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
  let g : ℕ → ℕ := fun t => k0 + p * t
  have hg : Function.Injective g := by
    intro t t' h
    have : p * t = p * t' := by simp only [g] at h; omega
    exact Nat.eq_of_mul_eq_mul_left hp this
  have hzero : ∀ x ∉ Set.range g, f x = 0 := by
    intro x hx
    have : ¬ p ∣ m + (x + 1) := fun h => hx ((hdiv x).1 h)
    simp only [f, if_neg this, zero_div]
  have hcomp : f ∘ g = fun t : ℕ => (1 / 2 : ℝ) ^ (k0 + 1) * ((1 / 2 : ℝ) ^ p) ^ t := by
    funext t
    have h1 : p ∣ m + (g t + 1) := (hdiv (g t)).2 ⟨t, rfl⟩
    simp only [Function.comp, f, if_pos h1, g]
    rw [← pow_mul, ← pow_add, one_div_pow, one_div]
    congr 2
    ring
  have hr0 : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ p := by positivity
  have hr1 : (1 / 2 : ℝ) ^ p < 1 := pow_lt_one₀ (by norm_num) (by norm_num) hp.ne'
  have hgeo := (hasSum_geometric_of_lt_one hr0 hr1).mul_left ((1 / 2 : ℝ) ^ (k0 + 1))
  rw [← hcomp] at hgeo
  have hH := (hg.hasSum_iff hzero).1 hgeo
  change ∑' k : ℕ, f k = _
  rw [hH.tsum_eq]
  have hk : k0 + 1 = p - s := by omega
  rw [hk]
  have h2 : (2 : ℝ) ^ p = 2 ^ (p - s) * 2 ^ s := by rw [← pow_add, Nat.sub_add_cancel hsp.le]
  have h3 : (1 : ℝ) < 2 ^ p := one_lt_pow₀ (by norm_num) hp.ne'
  have h4 : (2 : ℝ) ^ p - 1 ≠ 0 := by linarith
  have h5 : (0 : ℝ) < 2 ^ (p - s) := by positivity
  rw [one_div_pow, one_div_pow]
  field_simp
  rw [h2]
