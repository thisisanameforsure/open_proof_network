import json, sys
classes=json.load(open('classes13.json'))
S=sorted(v for c in classes for v in c)
dec = sys.argv[1] if len(sys.argv)>1 else "decide"
Slit="["+", ".join(map(str,S))+"]"
Clit="["+", ".join("["+", ".join(map(str,c))+"]" for c in classes)+"]"
stmt=open('Statement13.lean').read()
stmt=stmt.replace("import Mathlib\n","import Mathlib\nimport Nodes.«variant-9724698e».Context\n",1)
body=f"""  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  obtain ⟨M, hMdef⟩ : ∃ M, M = A.max' hne := ⟨_, rfl⟩
  have hM : M ∈ A := by rw [hMdef]; exact Finset.max'_mem A hne
  have hle : ∀ x ∈ A, x ≤ M := by
    intro x hx
    rw [hMdef]
    exact Finset.le_max' A x hx
  have hMpos : 0 < M := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, M.gcd x * 13 ≤ M
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨M, hM, x, hx, key M x (by rw [hn]; exact h)⟩
  push Not at hw
  obtain ⟨S, hS⟩ : ∃ S : List ℕ, S = {Slit} := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C : List (List ℕ), C = {Clit} := ⟨_, rfl⟩
  have P1 : ∀ k, k < 13 → ∀ j, j < k → 0 < j → k ∣ 27720 ∧ 27720 / k * j ∈ S := by
    subst hS
    {dec}
  have P3 : ∀ a ∈ S, C.findIdx (fun l => l.contains a) < 11 ∧
      a ∈ C.getD (C.findIdx (fun l => l.contains a)) [] := by
    subst hS hC
    {dec}
  have P2 : ∀ i, i < 11 → ∀ a ∈ C.getD i [], ∀ b ∈ C.getD i [], a ≠ b →
      13 * a.gcd b ≤ a ∨ 13 * a.gcd b ≤ b := by
    subst hC
    {dec}
  have forms : ∀ x ∈ A.erase M, ∃ a ∈ S, 27720 * x = a * M := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < M := lt_of_le_of_ne (hle x hx.2) hx.1
    have hg := hw x hx.2
    have hd1 := Nat.gcd_dvd_left M x
    have hd2 := Nat.gcd_dvd_right M x
    have hgpos : 0 < M.gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    generalize M.gcd x = g at hg hd1 hd2 hgpos
    obtain ⟨k, hk⟩ := hd1
    obtain ⟨j, hj⟩ := hd2
    have hk13 : k < 13 := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hjk : j < k := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hj1 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    obtain ⟨hdvd, hmem⟩ := P1 k hk13 j hjk hj1
    refine ⟨27720 / k * j, hmem, ?_⟩
    obtain ⟨q, hq⟩ := hdvd
    have hkpos : 0 < k := by omega
    rw [hq, Nat.mul_div_cancel_left q hkpos, hk, hj]
    ring
  have hcard : (A.erase M).card = 12 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase M, C.findIdx (fun l => l.contains (27720 * x / M)) ∈ Finset.range 11 := by
    intro x hx
    obtain ⟨a, ha, hax⟩ := forms x hx
    rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
    exact (P3 a ha).1
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨a, ha, hax⟩ := forms x hx
  obtain ⟨b, hb, hby⟩ := forms y hy
  simp only [hax, hby, Nat.mul_div_cancel _ hMpos] at hc
  have hab : a ≠ b := by
    intro h
    subst h
    apply hxy
    omega
  obtain ⟨hi, hai⟩ := P3 a ha
  obtain ⟨_, hbi⟩ := P3 b hb
  rw [← hc] at hbi
  have hgcd : a.gcd b * M = 27720 * x.gcd y := by
    have h1 : Nat.gcd (27720 * x) (27720 * y) = 27720 * x.gcd y := Nat.gcd_mul_left 27720 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases P2 _ hi a hai b hbi hab with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 13 * 27720 ≤ x * 27720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 13 * 27720 ≤ y * 27720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
"""
assert stmt.count("  sorry\n")==1
print(stmt.replace("  sorry\n", body), end="")
