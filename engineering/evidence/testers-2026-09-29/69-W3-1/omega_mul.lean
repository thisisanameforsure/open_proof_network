import Mathlib

open scoped ArithmeticFunction.omega

theorem erdos69_omega_mul (a n : ℕ) (ha : a ≠ 0) (hn : n ≠ 0) :
    ω (a * n) + (a.primeFactors.filter (· ∣ n)).card = ω a + ω n := by
  have hω : ∀ m : ℕ, ω m = m.primeFactors.card := fun m => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset]
    rfl
  have hf : a.primeFactors.filter (· ∣ n) = a.primeFactors ∩ n.primeFactors := by
    ext p
    simp only [Finset.mem_filter, Finset.mem_inter, Nat.mem_primeFactors]
    constructor
    · rintro ⟨⟨hp, hpa, _⟩, hpn⟩
      exact ⟨⟨hp, hpa, ha⟩, hp, hpn, hn⟩
    · rintro ⟨⟨hp, hpa, _⟩, _, hpn, _⟩
      exact ⟨⟨hp, hpa, ha⟩, hpn⟩
  rw [hω, hω, hω, hf, Nat.primeFactors_mul ha hn, Finset.card_union_add_card_inter]
