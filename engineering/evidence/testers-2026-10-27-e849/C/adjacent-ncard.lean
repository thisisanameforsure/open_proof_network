import Mathlib

open Nat

/-! For B's --h2 assembly (agent C, 2026-10-27): a set of naturals whose members are pairwise
adjacent has at most two members, and a set inside `S ∪ T` with `S` an explicit finset has
`ncard ≤ S.card + ncard T`. Self-contained; paste as `private` helpers. -/

private theorem e849_ncard_pair_le (a b : ℕ) : ({a, b} : Set ℕ).ncard ≤ 2 :=
  (Set.ncard_insert_le a {b}).trans (by simp)

/-- Pairwise adjacent naturals lie in `{x, x+1}` or `{x-1, x}` for any member `x`. -/
theorem e849_pairwise_adjacent_subset (R : Set ℕ)
    (h : ∀ x ∈ R, ∀ y ∈ R, x ≠ y → x + 1 = y ∨ y + 1 = x) (x : ℕ) (hx : x ∈ R) :
    R ⊆ {x, x + 1} ∨ R ⊆ {x - 1, x} := by
  by_cases hhi : x + 1 ∈ R
  · left
    intro y hy
    by_cases hxy : y = x
    · simp [hxy]
    rcases h x hx y hy (Ne.symm hxy) with h1 | h1
    · simp [← h1]
    · exfalso
      -- y + 1 = x and x + 1 ∈ R: y and x + 1 differ by 2
      rcases h y hy (x + 1) hhi (by omega) with h2 | h2 <;> omega
  · right
    intro y hy
    by_cases hxy : y = x
    · simp [hxy]
    rcases h x hx y hy (Ne.symm hxy) with h1 | h1
    · exact absurd (h1 ▸ hy) hhi
    · have : y = x - 1 := by omega
      simp [this]

/-- Pairwise adjacent naturals form a finite set. -/
theorem e849_pairwise_adjacent_finite (R : Set ℕ)
    (h : ∀ x ∈ R, ∀ y ∈ R, x ≠ y → x + 1 = y ∨ y + 1 = x) : R.Finite := by
  by_cases hR : R = ∅
  · simp [hR]
  obtain ⟨x, hx⟩ := Set.nonempty_iff_ne_empty.mpr hR
  rcases e849_pairwise_adjacent_subset R h x hx with hs | hs
  · exact (Set.toFinite _).subset hs
  · exact (Set.toFinite _).subset hs

/-- Pairwise adjacent naturals: at most two of them. -/
theorem e849_pairwise_adjacent_ncard_le_two (R : Set ℕ)
    (h : ∀ x ∈ R, ∀ y ∈ R, x ≠ y → x + 1 = y ∨ y + 1 = x) : R.ncard ≤ 2 := by
  by_cases hR : R = ∅
  · simp [hR]
  obtain ⟨x, hx⟩ := Set.nonempty_iff_ne_empty.mpr hR
  rcases e849_pairwise_adjacent_subset R h x hx with hs | hs
  · exact (Set.ncard_le_ncard hs (Set.toFinite _)).trans (e849_ncard_pair_le _ _)
  · exact (Set.ncard_le_ncard hs (Set.toFinite _)).trans (e849_ncard_pair_le _ _)

/-- A set inside an explicit finset `S` union a set `T` of `ncard ≤ b` has `ncard ≤ S.card + b`. -/
theorem e849_ncard_le_of_subset_union (R T : Set ℕ) (S : Finset ℕ) (b : ℕ)
    (hsub : R ⊆ (S : Set ℕ) ∪ T) (hT : T.Finite) (hb : T.ncard ≤ b) : R.ncard ≤ S.card + b := by
  calc R.ncard ≤ ((S : Set ℕ) ∪ T).ncard := Set.ncard_le_ncard hsub (S.finite_toSet.union hT)
    _ ≤ (S : Set ℕ).ncard + T.ncard := Set.ncard_union_le _ _
    _ ≤ S.card + b := by rw [Set.ncard_coe_finset]; omega

-- The shape B's assembly wants: rows of a middle value are sporadic (14 row numbers) or pairwise adjacent.
example (R : Set ℕ)
    (hR : ∀ n ∈ R, n ∈ ({16, 10, 21, 56, 22, 120, 36, 153, 19, 221, 17, 78, 15, 14} : Finset ℕ) ∨
      ∀ n' ∈ R, n' ≠ n → n' ∉ ({16, 10, 21, 56, 22, 120, 36, 153, 19, 221, 17, 78, 15, 14} : Finset ℕ) →
        n + 1 = n' ∨ n' + 1 = n) :
    R.ncard ≤ 16 := by
  classical
  set S : Finset ℕ := {16, 10, 21, 56, 22, 120, 36, 153, 19, 221, 17, 78, 15, 14} with hS
  have hcard : S.card = 14 := by rw [hS]; rfl
  have hsub : R ⊆ (S : Set ℕ) ∪ (R \ (S : Set ℕ)) := by
    intro n hn; by_cases h : n ∈ S
    · exact Or.inl h
    · exact Or.inr ⟨hn, h⟩
  have hadj : ∀ x ∈ R \ (S : Set ℕ), ∀ y ∈ R \ (S : Set ℕ), x ≠ y → x + 1 = y ∨ y + 1 = x := by
    rintro x ⟨hxR, hxS⟩ y ⟨hyR, hyS⟩ hne
    rcases hR x hxR with h | h
    · exact absurd h hxS
    · exact h y hyR (Ne.symm hne) hyS
  have h2 := e849_pairwise_adjacent_ncard_le_two _ hadj
  have hfin : (R \ (S : Set ℕ)).Finite := e849_pairwise_adjacent_finite _ hadj
  have := e849_ncard_le_of_subset_union R (R \ (S : Set ℕ)) S 2 hsub hfin h2
  omega
