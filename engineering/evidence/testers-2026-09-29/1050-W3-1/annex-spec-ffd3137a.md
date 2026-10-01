# spec-ffd3137a (closed form for the Padé numerator coefficient p_k): an elementary proof route

Contributor: t0929-1 (agents 1050-C, 1050-W3-1). Status: all three steps are proved in Lean, as one theorem with the node's
own statement: verdict pass from precheck 01M3QTYJZGY0J129XF270Y9PXC (2026-09-30, every step), submitted as graph pull
request #311, not merged at the time of writing. The same argument, inlined into a proof of erdos-1050--h1-v2--h3, passed a
precheck too. The identities are also checked in exact rational arithmetic (Python fractions). The Lean block at the end is
step 1 alone, for reading; the full proof is the node's Proof.lean once merged.

Write q = 2, x_l = q^l, c_j = Qc n j, and E(X) = Π_{i<n} (X − q^(n+1+i)), a polynomial of degree n.

1. The Padé denominator's coefficients are Lagrange coefficients (numerical: 315 cases, q ∈ {2,3,5},
   n ≤ 13, every j ≤ n):

       c_j · q^j · Π_{l ≤ n, l ≠ j} (q^j − q^l) = E(q^j).

   Proof sketch: Π_{l<j}(q^j − q^l) = q^(j(j−1)/2) (q;q)_j, Π_{j<l≤n}(q^j − q^l) = (−1)^(n−j) q^(j(n−j)) (q;q)_(n−j),
   E(q^j) = (−1)^n q^(jn) Π_{t=n+1−j}^{2n−j} (q^t − 1), and c_j = (−1)^j q^(j(j−1)/2) [n j]_q [2n−j n]_q with
   [n j]_q (q;q)_j (q;q)_(n−j) = (q;q)_n and (q;q)_n [2n−j n]_q = Π_{t=n+1−j}^{2n−j} (q^t − 1). The powers of q
   add up to jn on both sides.

2. Hence, by Lagrange interpolation (n + 1 nodes, deg E = n),

       Σ_{j ≤ n} c_j / (z/q^j − 1) = Σ_j c_j q^j / (z − q^j) = E(z) / Π_{l ≤ n} (z − q^l).

   At z = q^m, m > n, this is spec-f2b55478 (proved on the record), which this route re-derives
   without using it.

3. The regular part at z = q^k (k ≤ n) of the left side is Σ_{j ≠ k} c_j q^j/(q^k − q^j); of the right side
   it is G'(q^k) with G(z) = E(z)/Π_{l ≠ k}(z − q^l), and G'(q^k) = G(q^k) · [Σ_i 1/(q^k − q^(n+1+i)) −
   Σ_{l ≠ k} 1/(q^k − q^l)] with G(q^k) = c_k q^k. Rewriting each fraction with powers of q and moving
   the terms j > k (which p_k leaves out) to the right gives exactly the statement of spec-ffd3137a.

A Lean route: prove 1 as a product identity (Finset.prod_range_succ, prod_range_reflect for the
reindexing t = n+1−j..2n−j); get 2 from Mathlib's Lagrange interpolation or by clearing denominators
and comparing two degree-n polynomials at the n+1 nodes; get 3 from Polynomial.derivative of a
product at a node. Consequences for the hole `hpint` of erdos-1050--h1-v2--h3's skeleton are in annex
7c650db6… on that node.

```lean
import Mathlib

theorem lag_test (n j : ℕ) (hj : j ≤ n) :
    (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
        ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
      (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
    ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) := by
  have hpos : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
    intro s
    have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  -- (b) the nodes below j
  have hb : ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) =
      (2 : ℚ) ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
    have h1 : ∀ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) = 2 ^ l * ((2 : ℚ) ^ (j - l) - 1) := by
      intro l hl
      have hl' := Finset.mem_range.mp hl
      have : (2 : ℚ) ^ j = 2 ^ l * 2 ^ (j - l) := by rw [← pow_add]; congr 1; omega
      rw [this]; ring
    rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
      Finset.sum_range_id]
    congr 1
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun s hs => ?_)
    have hs' := Finset.mem_range.mp hs
    congr 2
    omega
  -- (c) the nodes above j
  have hc : ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
      (-(2 : ℚ) ^ j) ^ (n - j) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
    calc ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s))
        = ∏ s ∈ Finset.range (n - j), ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (s + 1) - 1)) := by
          refine Finset.prod_congr rfl (fun s _ => ?_)
          rw [show j + 1 + s = j + (s + 1) by omega, pow_add]
          ring
      _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
  -- (d) the right side
  have hd : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) =
      (-(2 : ℚ) ^ j) ^ n * ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
    calc ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i))
        = ∏ i ∈ Finset.range n, ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (n + 1 + i - j) - 1)) := by
          refine Finset.prod_congr rfl (fun i _ => ?_)
          rw [show n + 1 + i = j + (n + 1 + i - j) by omega, pow_add, Nat.add_sub_cancel_left]
          ring
      _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
  -- (e) the q-factorial splits at j
  have he : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
    have hn : n = (n - j) + j := by omega
    conv_rhs => rw [hn]
    rw [Finset.prod_range_add, mul_comm]
    congr 1
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun t ht => ?_)
    have ht' := Finset.mem_range.mp ht
    congr 2
    omega
  -- (f) reflect the second Gaussian binomial's numerator
  have hf : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) =
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun i hi => ?_)
    have hi' := Finset.mem_range.mp hi
    congr 2
    omega
  have hF : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
  have hB : ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
  have hjj : j * j = j * (j - 1) / 2 + j * (j - 1) / 2 + j := by
    have h2 := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self j)
    rcases j with _ | j
    · simp
    · simp only [Nat.add_sub_cancel] at h2 ⊢
      nlinarith
  have hpow : (-(2 : ℚ) ^ j) ^ n = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j *
      (-(2 : ℚ) ^ j) ^ (n - j) := by
    rw [show n = j + (n - j) by omega, pow_add, Nat.add_sub_cancel_left, neg_pow, ← pow_mul, hjj,
      pow_add, pow_add]
    ring
  rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hb, hc, hd, hf, hpow]
  field_simp
  rw [← he]
  ring
```
