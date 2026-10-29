import Mathlib
import Nodes.«variant-3969f1f7».Context

/-! Singmaster's conjecture (1971) in the row form of Erdős 849: there is an absolute bound
`B` on the number of rows `n` of Pascal's half triangle `1 ≤ k ≤ n/2` holding any given value
`a`. Proved, it refutes the affirmative root `Opn.erdos_849` (take `t = B + 1`). -/

open Nat

theorem Opn.erdos_849_singmaster_bounded :
    ∃ B : ℕ, ∀ a : ℕ,
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard ≤ B := by
  -- approach: split the rows holding a by k: k = 1, bounded k, middle k, and the interior k ≥ exp((log n)^(5/6)) of Matomäki–Radziwiłł–Shao–Tao–Teräväinen
  -- licence: CC-BY-4.0
  have hall :
      (∀ K a : ℕ, {n : ℕ | ∃ k : ℕ, 2 ≤ k ∧ k ≤ K ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ K) ∧
      (∃ K B : ℕ, ∀ a : ℕ, {n : ℕ | ∃ k : ℕ, K < k ∧
          (k : ℝ) < Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ B) ∧
      (∃ a₀ : ℕ, ∀ a ≥ a₀, {n : ℕ | ∃ k : ℕ, 1 ≤ k ∧
          Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ 2) := by
    refine ⟨?_, ?_, ?_⟩
    ·
      -- label: rows with bounded k
      -- claim: $\#\{n : \binom{n}{k} = a,\ 2 \le k \le K,\ 2k \le n\} \le K$ for all $K, a$
      -- Elementary: two rows holding the same value have different k, since C(n, k) increases in n.
      have h_fixed : ∀ K a : ℕ,
          {n : ℕ | ∃ k : ℕ, 2 ≤ k ∧ k ≤ K ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ K := by
        sorry
      exact h_fixed
    ·
      -- label: rows with middle k (the open core)
      -- claim: $\exists K, B\ \forall a:\ \#\{n : \binom{n}{k} = a,\ K < k < e^{(\log n)^{5/6}},\ 2k \le n\} \le B$
      -- Open: this is Singmaster's conjecture restricted to k growing slower than exp((log n)^(5/6)).
      have h_middle : ∃ K B : ℕ, ∀ a : ℕ, {n : ℕ | ∃ k : ℕ, K < k ∧
          (k : ℝ) < Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ B := by
        sorry
      exact h_middle
    ·
      -- label: rows in the interior (MRSTT 2022)
      -- claim: $\exists a_0\ \forall a \ge a_0:\ \#\{n : \binom{n}{k} = a,\ e^{(\log n)^{5/6}} \le k \le n/2\} \le 2$
      -- Known: Matomäki, Radziwiłł, Shao, Tao, Teräväinen, Quart. J. Math. 73 (2022), Theorem 1.3,
      -- with ε = 1/6: for a large, at most two solutions of C(n, k) = a with exp((log n)^(2/3+ε)) ≤ k ≤ n/2.
      have h_interior : ∃ a₀ : ℕ, ∀ a ≥ a₀, {n : ℕ | ∃ k : ℕ, 1 ≤ k ∧
          Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ 2 := by
        sorry
      exact h_interior
  obtain ⟨hF, ⟨K, B₁, hM⟩, ⟨a₀, hI⟩⟩ := hall
  refine ⟨1 + K + B₁ + (a₀ + 2), fun a => ?_⟩
  set F := {n : ℕ | ∃ k : ℕ, 2 ≤ k ∧ k ≤ K ∧ 2 * k ≤ n ∧ choose n k = a}
  set M := {n : ℕ | ∃ k : ℕ, K < k ∧
    (k : ℝ) < Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ∧ 2 * k ≤ n ∧ choose n k = a}
  set I := {n : ℕ | ∃ k : ℕ, 1 ≤ k ∧
    Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ choose n k = a}
  have key : ∀ n k : ℕ, 1 ≤ k → 2 * k ≤ n → choose n k = a → n ≤ a := by
    intro n k hk1 hk2 h
    rw [← h]
    calc n = n.choose 1 := (Nat.choose_one_right n).symm
      _ ≤ n.choose k := by
        have hmono : ∀ j, 1 ≤ j → j ≤ n / 2 → n.choose 1 ≤ n.choose j := by
          intro j
          induction j with
          | zero => intro h _; omega
          | succ j ih =>
            intro hr hj
            rcases Nat.eq_or_lt_of_le hr with h' | h'
            · rw [← h']
            · exact (ih (by omega) (by omega)).trans
                (Nat.choose_le_succ_of_lt_half_left (by omega))
        exact hmono k hk1 (by omega)
  have hsub : {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a} ⊆ (({a} ∪ F) ∪ M) ∪ I := by
    rintro n ⟨k, hk1, hk2, h⟩
    by_cases hk : k = 1
    · subst hk
      left; left; left
      simpa using h
    by_cases hkK : k ≤ K
    · left; left; right
      exact ⟨k, by omega, hkK, hk2, h⟩
    by_cases hf : (k : ℝ) < Real.exp (Real.log n ^ ((5 : ℝ) / 6))
    · left; right
      exact ⟨k, by omega, hf, hk2, h⟩
    · right
      exact ⟨k, hk1, not_lt.mp hf, hk2, h⟩
  have hfin : ((({a} ∪ F) ∪ M) ∪ I).Finite := by
    refine (Set.finite_Iic a).subset ?_
    rintro n (((hn | ⟨k, hk, -, hk2, h⟩) | ⟨k, hk, -, hk2, h⟩) | ⟨k, hk, -, hk2, h⟩)
    · exact le_of_eq hn
    · exact key n k (by omega) hk2 h
    · exact key n k (by omega) hk2 h
    · exact key n k hk hk2 h
  calc {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard
      ≤ ((({a} ∪ F) ∪ M) ∪ I).ncard := Set.ncard_le_ncard hsub hfin
    _ ≤ (({a} ∪ F) ∪ M).ncard + I.ncard := Set.ncard_union_le _ _
    _ ≤ (({a} ∪ F).ncard + M.ncard) + I.ncard := by gcongr; exact Set.ncard_union_le _ _
    _ ≤ (({a} : Set ℕ).ncard + F.ncard + M.ncard) + I.ncard := by
        gcongr; exact Set.ncard_union_le _ _
    _ ≤ 1 + K + B₁ + (a₀ + 2) := by
        rw [Set.ncard_singleton]
        have h1 : F.ncard ≤ K := hF K a
        have h2 : M.ncard ≤ B₁ := hM a
        have h3 : I.ncard ≤ a₀ + 2 := by
          by_cases ha : a₀ ≤ a
          · have : I.ncard ≤ 2 := hI a ha
            omega
          · have hIsub : I ⊆ Set.Iic a := by
              rintro n ⟨k, hk, -, hk2, h⟩
              exact key n k hk hk2 h
            have e : (Set.Iic a).ncard = a + 1 := by simp
            have := Set.ncard_le_ncard hIsub (Set.finite_Iic a)
            omega
        omega
