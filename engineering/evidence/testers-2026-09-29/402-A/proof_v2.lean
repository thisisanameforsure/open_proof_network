import Mathlib
import Nodes.«variant-892f5809».Context

/-! Graham's gcd conjecture (Erdős problem 402) for 9-element sets: with M the largest element,
if every b had gcd(M, b) > M/9 then every other element would be (j/k)M with j < k < 9, and a
colouring of those values into 7 classes, each a set of pairwise "good" values, shows the
8 other elements cannot all avoid a pair x, y with 9 * gcd(x, y) ≤ max(x, y). -/

theorem Opn.erdos_402_card_nine :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 9 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  have toQ : ∀ a b : ℕ, 9 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b hab
    have h9 : ((A.card : ℕ) : ℚ) = 9 := by rw [hcard]; norm_num
    rw [h9, le_div_iff₀ (by norm_num : (0 : ℚ) < 9)]
    exact_mod_cast (by omega : a.gcd b * 9 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  have hMA : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero fun h => h0 (h ▸ hMA)
  by_cases hdirect : ∃ x ∈ A, 9 * (A.max' hne).gcd x ≤ A.max' hne
  · obtain ⟨x, hxA, hx⟩ := hdirect
    exact ⟨A.max' hne, hMA, x, hxA, toQ _ x hx⟩
  simp only [not_exists, not_and, not_le] at hdirect
  -- every other element x satisfies 840 x = c M with c = 840 j / k, 1 ≤ j < k ≤ 8
  have hval : ∀ x ∈ A.erase (A.max' hne), ∃ c ∈ [105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735], 840 * x = c * A.max' hne := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero fun h => h0 (h ▸ hxA)
    have hxlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
    have hbig : A.max' hne < 9 * (A.max' hne).gcd x := hdirect x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hk9 : k < 9 := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hjk : j < k := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj
        omega
      · exact h
    refine ⟨840 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  -- a colouring of the 21 values into 7 classes, each class pairwise good
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → List ℕ, cls = fun i => [[420, 600], [210, 360, 672, 700],
      [120, 560, 630], [105, 240, 504], [280, 315, 480], [168, 525, 720], [140, 336, 735]].getD i [] :=
    ⟨_, rfl⟩
  obtain ⟨col, hcol⟩ : ∃ col : ℕ → ℕ, col = fun c => [[420, 600], [210, 360, 672, 700],
      [120, 560, 630], [105, 240, 504], [280, 315, 480], [168, 525, 720], [140, 336, 735]].findIdx
      (fun C => C.contains c) := ⟨_, rfl⟩
  have hcover : ∀ c ∈ ([105, 120, 140, 168, 210, 240, 280, 315, 336, 360, 420, 480, 504, 525, 560,
      600, 630, 672, 700, 720, 735] : List ℕ), col c < 7 ∧ c ∈ cls (col c) := by
    subst hcol hcls
    decide
  have hgood : ∀ i < 7, ∀ c ∈ cls i, ∀ d ∈ cls i, c = d ∨ 9 * c.gcd d ≤ c ∨ 9 * c.gcd d ≤ d := by
    subst hcls
    decide
  -- pigeonhole: eight other elements, seven classes
  have hmaps : ∀ x ∈ A.erase (A.max' hne), col (840 * x / A.max' hne) ∈ Finset.range 7 := by
    intro x hx
    obtain ⟨c, hc, hxc⟩ := hval x hx
    rw [Finset.mem_range, hxc, Nat.mul_div_cancel _ hMpos]
    exact (hcover c hc).1
  have hcard8 : (Finset.range 7).card < (A.erase (A.max' hne)).card := by
    rw [Finset.card_erase_of_mem hMA, hcard, Finset.card_range]
    norm_num
  obtain ⟨x, hx, y, hy, hxy, hxycol⟩ := Finset.exists_ne_map_eq_of_card_lt_of_maps_to hcard8 hmaps
  obtain ⟨c, hc, hxc⟩ := hval x hx
  obtain ⟨d, hd, hyd⟩ := hval y hy
  rw [hxc, hyd, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hxycol
  have hcd : c ≠ d := by
    rintro rfl
    exact hxy (by omega)
  have hcmem := (hcover c hc).2
  have hdmem := (hcover d hd).2
  rw [← hxycol] at hdmem
  -- transfer the good pair of values back to x and y
  have hg : c.gcd d * A.max' hne = 840 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxc, ← hyd, Nat.gcd_mul_left]
  have hxA : x ∈ A := (Finset.mem_erase.mp hx).2
  have hyA : y ∈ A := (Finset.mem_erase.mp hy).2
  rcases hgood (col c) (hcover c hc).1 c hcmem d hdmem with h | h | h
  · exact absurd h hcd
  · refine ⟨x, hxA, y, hyA, toQ x y ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hxc] at h2
    omega
  · refine ⟨y, hyA, x, hxA, toQ y x ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hyd] at h2
    rw [Nat.gcd_comm]
    omega
