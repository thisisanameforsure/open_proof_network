import Mathlib

open Polynomial in
theorem lag_test : ∀ (s : Finset ℕ) (p : ℕ → ℝ) (Q : ℝ[X]), (∀ k ∈ s, p k ≠ 0) → Set.InjOn p s →
    Q.degree < s.card → ∀ x : ℝ, (∀ k ∈ s, 1 - p k * x ≠ 0) →
    Q.eval x * ∏ k ∈ s, (1 - p k * x)⁻¹ =
      ∑ k ∈ s, Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (1 - p j / p k))⁻¹ * (1 - p k * x)⁻¹ := by
  intro s p Q hp hinj hdeg x hx
  have hinj' : Set.InjOn (fun k => (p k)⁻¹) s := by
    intro a ha b hb hab
    exact hinj ha hb (inv_injective hab)
  have hxv : ∀ k ∈ s, x ≠ (p k)⁻¹ := by
    intro k hk hxk
    apply hx k hk
    rw [hxk, mul_inv_cancel₀ (hp k hk), sub_self]
  have hQ := Lagrange.eq_interpolate hinj' hdeg
  have hev := Lagrange.eval_interpolate_not_at_node (s := s) (v := fun k => (p k)⁻¹) (fun i => Q.eval (p i)⁻¹) hxv
  rw [← hQ, Lagrange.eval_nodal] at hev
  have hfac : ∀ k ∈ s, (1 - p k * x)⁻¹ = (x - (p k)⁻¹)⁻¹ * (-(p k)⁻¹) := by
    intro k hk
    have h1 := hp k hk
    have h3 : (x - (p k)⁻¹) * (-(p k)) = 1 - p k * x := by
      rw [sub_mul, mul_neg, mul_neg, inv_mul_cancel₀ h1]; ring
    rw [← h3, mul_inv, inv_neg]
  rw [Finset.prod_congr rfl hfac, Finset.prod_mul_distrib, hev]
  have hne : ∏ i ∈ s, (x - (p i)⁻¹) ≠ 0 := Finset.prod_ne_zero_iff.mpr (fun i hi => sub_ne_zero.mpr (hxv i hi))
  rw [Finset.prod_inv_distrib, mul_assoc, ← mul_assoc (∑ i ∈ s, _), mul_comm (∑ i ∈ s, _), ← mul_assoc, ← mul_assoc,
    mul_inv_cancel₀ hne, one_mul, Finset.sum_mul]
  refine Finset.sum_congr rfl (fun k hk => ?_)
  rw [Lagrange.nodalWeight, ← Finset.mul_prod_erase s (fun i => -(p i)⁻¹) hk]
  have hj : ∀ j ∈ s.erase k, ((p k)⁻¹ - (p j)⁻¹)⁻¹ * -(p j)⁻¹ = (1 - p j / p k)⁻¹ := by
    intro j hj
    have hjs := Finset.mem_of_mem_erase hj
    have hjk := Finset.ne_of_mem_erase hj
    have hpj := hp j hjs
    have hpk := hp k hk
    have hne : p j ≠ p k := fun h => hjk (hinj hjs hk h)
    have hsub : p k - p j ≠ 0 := sub_ne_zero.mpr (Ne.symm hne)
    field_simp
    ring
  calc (∏ j ∈ s.erase k, ((p k)⁻¹ - (p j)⁻¹)⁻¹) * (x - (p k)⁻¹)⁻¹ * Q.eval (p k)⁻¹ *
        (-(p k)⁻¹ * ∏ j ∈ s.erase k, -(p j)⁻¹)
      = Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (((p k)⁻¹ - (p j)⁻¹)⁻¹ * -(p j)⁻¹)) * ((x - (p k)⁻¹)⁻¹ * -(p k)⁻¹) := by
        rw [Finset.prod_mul_distrib]; ring
    _ = Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (1 - p j / p k))⁻¹ * (1 - p k * x)⁻¹ := by
        rw [Finset.prod_congr rfl hj, ← Finset.prod_inv_distrib, hfac k hk]
