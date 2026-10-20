import Mathlib
import Nodes.«spec-5e2e0890».Context
import Nodes.«spec-ddd99827».Proof

/-- Uniqueness of representation: two sets of positive integers with the same Mersenne
reciprocal sum are equal. It follows from the gap `∑_{m > n} 1/(2^m - 1) < 1/(2^n - 1)` by
looking at the least element of the symmetric difference. Consequence for Erdős 257: a rational
`x` is a subset sum for at most one `A`, found by the greedy walk (take `n` whenever the
remainder is at least `1/(2^n - 1)`), so the affirmative statement is false iff some rational
with an even denominator (such as `1/2`, whose representation cannot be finite) is reached by
a greedy walk that never stalls. -/
theorem Opn.erdos_257_subsum_injective (A B : Set ℕ) (hA : 0 ∉ A) (hB : 0 ∉ B)
    (h : ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = ∑' n : B, (1 : ℝ) / (2 ^ n.1 - 1)) :
    A = B := by
  -- approach: least element of the symmetric difference; the side that contains it has the larger sum, by the gap lemma (spec-ddd99827, used)
  -- licence: CC-BY-4.0
  -- label: Mersenne reciprocals are summable
  -- claim: $\sum_{m \ge 0} \frac{1}{2^m - 1} < \infty \text{ (with Lean's convention } 1/0 = 0 \text{ at } m = 0)$
  -- Comparison with a geometric series: for $m \ge 1$, $1/(2^m - 1) \le 2 \cdot (1/2)^m$.
  have h1 : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) := spec_5e2e0890__h1 A B hA hB h
  -- label: lexicographic comparison of subset sums
  -- claim: $g \ge 0 \text{ summable}, \sum_{k \ge 0} g(n+1+k) < g(n), n \in S \setminus T, S \cap [0,n) = T \cap [0,n) \implies \sum_{T} g < \sum_{S} g$
  -- Split both sums at $n$: the parts below $n$ agree, the $S$ side has $g(n)$ in addition, and the rest of the $T$ side is a tail bounded by the gap.
  have h3 : ∀ g : ℕ → ℝ, Summable g → (∀ m, 0 ≤ g m) → ∀ S T : Set ℕ, ∀ n : ℕ, n ∈ S → n ∉ T →
      (∀ m, m < n → (m ∈ S ↔ m ∈ T)) → ∑' k : ℕ, g (n + 1 + k) < g n →
      ∑' m : T, g m < ∑' m : S, g m := spec_5e2e0890__h2 A B hA hB h
  -- the assembly
  by_contra hne
  have hex : ∃ n, (n ∈ A ∧ n ∉ B) ∨ (n ∈ B ∧ n ∉ A) := by
    by_contra hno
    push_neg at hno
    apply hne
    ext m
    exact ⟨fun hm => (hno m).1 hm, fun hm => (hno m).2 hm⟩
  classical
  have hn := Nat.find_spec hex
  have hmin : ∀ m, m < Nat.find hex → (m ∈ A ↔ m ∈ B) := by
    intro m hm
    have hnot := Nat.find_min hex hm
    push_neg at hnot
    exact ⟨hnot.1, hnot.2⟩
  have hnonneg : ∀ m : ℕ, (0 : ℝ) ≤ 1 / (2 ^ m - 1) := by
    intro m
    apply div_nonneg zero_le_one
    have : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
    linarith
  rcases hn with ⟨hnA, hnB⟩ | ⟨hnB, hnA⟩
  · have hn1 : 1 ≤ Nat.find hex := Nat.one_le_iff_ne_zero.mpr (fun h0 => hA (h0 ▸ hnA))
    have hlt := h3 (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) h1 hnonneg A B _ hnA hnB hmin (Opn.erdos_257_tail_lt_term _ hn1)
    exact absurd h (ne_of_gt hlt)
  · have hn1 : 1 ≤ Nat.find hex := Nat.one_le_iff_ne_zero.mpr (fun h0 => hB (h0 ▸ hnB))
    have hlt := h3 (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) h1 hnonneg B A _ hnB hnA
      (fun m hm => (hmin m hm).symm) (Opn.erdos_257_tail_lt_term _ hn1)
    exact absurd h (ne_of_lt hlt)
