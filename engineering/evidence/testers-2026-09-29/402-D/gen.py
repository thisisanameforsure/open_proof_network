import json
cls = json.load(open('classes.json'))
C = "[" + ", ".join("[" + ", ".join(map(str,c)) + "]" for c in cls) + "]"
stmt = open('graph/targets/erdos-402/nodes/variant-b89de5c4/Statement.lean').read()
body = r'''  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * 18 ≤ A.max' hne
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have hL : ∀ k < 18, 0 < k → 12252240 / k * k = 12252240 := by decide +kernel
  have H1 : ∀ k < 18, ∀ j < k, 0 < j →
      (CLS).findIdx (fun l => decide (12252240 / k * j ∈ l)) < 16 ∧
      12252240 / k * j ∈ (CLS).getD ((CLS).findIdx (fun l => decide (12252240 / k * j ∈ l))) [] := by
    decide +kernel
  have H2 : ∀ i < 16, ∀ v ∈ (CLS).getD i [], ∀ w ∈ (CLS).getD i [], v ≠ w →
      18 * v.gcd w ≤ v ∨ 18 * v.gcd w ≤ w := by
    decide +kernel
  have forms : ∀ x ∈ A.erase (A.max' hne), ∃ k j, k < 18 ∧ j < k ∧ 0 < j ∧
      12252240 * x = 12252240 / k * j * A.max' hne := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 18 := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hjk : j < k := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hj1 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    refine ⟨k, j, hkN, hjk, hj1, ?_⟩
    have hLk := hL k hkN (by omega)
    obtain ⟨g, hgd⟩ : ∃ g, (A.max' hne).gcd x = g := ⟨_, rfl⟩
    rw [hgd] at hk hj
    rw [hj, hk]
    calc 12252240 * (g * j) = (12252240 / k * k) * (g * j) := by rw [hLk]
      _ = 12252240 / k * j * (g * k) := by ring
  have hcard : (A.erase (A.max' hne)).card = 17 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase (A.max' hne),
      (CLS).findIdx (fun l => decide (12252240 * x / A.max' hne ∈ l)) ∈ Finset.range 16 := by
    intro x hx
    obtain ⟨k, j, hk, hj, hj0, he⟩ := forms x hx
    rw [Finset.mem_range, he, Nat.mul_div_cancel _ hMpos]
    exact (H1 k hk j hj hj0).1
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨k, j, hk, hj, hj0, hex⟩ := forms x hx
  obtain ⟨k', j', hk', hj', hj0', hey⟩ := forms y hy
  have ex' : 12252240 * x / A.max' hne = 12252240 / k * j := by
    rw [hex, Nat.mul_div_cancel _ hMpos]
  have ey' : 12252240 * y / A.max' hne = 12252240 / k' * j' := by
    rw [hey, Nat.mul_div_cancel _ hMpos]
  simp only [ex', ey'] at hc
  have h1 := (H1 k hk j hj hj0).2
  have h2 := (H1 k' hk' j' hj' hj0').2
  rw [hc] at h1
  have hvw : 12252240 / k * j ≠ 12252240 / k' * j' := by
    intro h
    apply hxy
    rw [h] at hex
    omega
  have hgcd : (12252240 / k * j).gcd (12252240 / k' * j') * A.max' hne = 12252240 * x.gcd y := by
    have h := Nat.gcd_mul_left 12252240 x y
    rw [hex, hey, Nat.gcd_mul_right] at h
    exact h
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases H2 _ (H1 k' hk' j' hj' hj0').1 _ h1 _ h2 hvw with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h3 := Nat.mul_le_mul_right (A.max' hne) h
    have h4 : x.gcd y * 18 * 12252240 ≤ x * 12252240 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h4 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h3 := Nat.mul_le_mul_right (A.max' hne) h
    have h4 : x.gcd y * 18 * 12252240 ≤ y * 12252240 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h4 (by norm_num)
'''.replace("(CLS)", "("+C+" : List (List ℕ))")
proof = stmt.replace("  sorry\n", body)
assert proof != stmt
open('Proof.lean','w').write(proof)
print(len(proof))
