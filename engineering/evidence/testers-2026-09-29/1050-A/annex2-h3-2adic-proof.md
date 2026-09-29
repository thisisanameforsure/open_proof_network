# hden (erdos-1050--h1-v2--h3): a proof of the 2-adic crux v2(p_k(n)) >= k(k-1)/2

Contributor: t0929-1 (agent 1050-A). **Informal proof, not formalized in Lean.** The algebra in
step 1 is checked by hand below; steps 2 and 3 are standard; every identity used was also
confirmed in exact rational arithmetic (Python `fractions`) for all n <= 15. Annex 4670684d2f0d on
this node calls this valuation bound "the one non-termwise fact" a proof of h3 needs; the partial
proof in graph PR #276 reduces h3 in Lean to exactly this bound plus the odd half (spec-1a5ab7c3),
so together they give a complete proof of h3 on paper.

Notation as in h3, with q = 2: Qc_j = Qc n j = (-1)^j q^(j(j-1)/2) [n, j]_q [2n-j, n]_q,
p_k = sum over j < k of Qc_j / (q^(k-j) - 1) (the j = k term is 0 in h3's Lean), a = k(k-1)/2.
Write (q)_m = prod over 1 <= s <= m of (q^s - 1), so [n, j]_q = (q)_n / ((q)_j (q)_(n-j)).

## 1. Partial fractions (the Pade structure, made explicit)

Let x_j = q^j for 0 <= j <= n, N(z) = prod over n < K <= 2n of (z - q^K) (monic, degree n),
D(z) = prod over 0 <= i <= n of (z - x_i), and D_j(z) = D(z) / (z - x_j). Then for every j <= n

    Qc_j q^j = N(x_j) / D_j(x_j).                                              (1)

Proof: N(q^j) = prod_K (-q^j)(q^(K-j) - 1) = (-1)^n q^(jn) (q)_(2n-j) / (q)_(n-j), and
D_j(q^j) = prod_{i<j} q^i (q^(j-i) - 1) * prod_{i>j} (-q^j)(q^(i-j) - 1)
         = q^(j(j-1)/2) (q)_j (-1)^(n-j) q^(j(n-j)) (q)_(n-j).
The quotient is (-1)^j q^(j(j-1)/2 + j) (q)_(2n-j) / ((q)_j (q)_(n-j)^2), and
[n, j]_q [2n-j, n]_q = (q)_(2n-j) / ((q)_j (q)_(n-j)^2). So (1) holds.

Since deg N = n < n + 1 = deg D, Lagrange interpolation at the n + 1 nodes x_j gives

    sum over j <= n of Qc_j q^j / (z - x_j) = N(z) / D(z).                    (2)

(Comparing leading terms also gives Q_n(2) = sum_j Qc_j 2^j = 1, and evaluating (2) at z = q^K for
n < K <= 2n gives the Pade vanishing sum_j Qc_j / (q^(K-j) - 1) = 0 there; both confirmed
numerically.)

## 2. A closed form for p_k

For j < k, Qc_j / (q^(k-j) - 1) = Qc_j q^j / (x_k - x_j). So p_k is the sum in (2) at z = x_k with
the pole term j = k removed and the terms j > k removed. The first is the regular part of N/D at
x_k, which is g'(x_k) for g = N / D_k, and g'(x_k) = g(x_k) (log g)'(x_k) = Qc_k q^k beta_k by (1).
Hence, for 0 <= k <= n,

    p_k = Qc_k q^k beta_k - sum over k < j <= n of Qc_j q^(j-k) / (1 - q^(j-k)),     (3)
    beta_k = sum over n < K <= 2n of 1/(q^k - q^K) - sum over i <= n, i != k of 1/(q^k - q^i).

(3) was confirmed in exact arithmetic for every k <= n <= 15.

## 3. The valuation bound

[m, j]_q is odd for j <= m (as a polynomial in q its constant term is 1), so v2(Qc_j) = j(j-1)/2.
In beta_k every term has 2-adic valuation at least -k: q^k - q^K = q^k (1 - q^(K-k)) for K > k,
q^k - q^i = q^i (q^(k-i) - 1) for i < k, q^k - q^i = q^k (1 - q^(i-k)) for i > k. So the first term
of (3) has valuation at least a + k - k = a. Each term of the tail has valuation
j(j-1)/2 + (j - k) >= k(k+1)/2 + 1 = a + k + 1 for j >= k + 1. Therefore v2(p_k) >= a = k(k-1)/2,
with every denominator in (3) odd.

## 4. From here to the hole of PR #276

(3) shows Omega p_k / 2^a is an integer for some odd Omega (a product of numbers 2^s - 1, s <= 2n).
spec-1a5ab7c3 (merged) says B = M_n p_k is an integer, M_n = prod over n/2 < m <= n of (2^m - 1).
Then 2^a divides Omega B, and gcd(2^a, Omega) = 1, so 2^a divides B: that is exactly the hole
"z 2^(k(k-1)/2) = M_n p_k" of PR #276. The Lean steps this needs are (1) (a finite product
manipulation), Lagrange interpolation for (2) and its derivative at a node for (3) (Mathlib has
`Lagrange.interpolate`), and the coprimality step (`IsCoprime.dvd_of_dvd_mul_left`). Step 3's
valuation argument can be written without valuations: multiply (3) by 2^k times the product of its
odd denominators and read off a factor 2^a from each term.

The coprimality step, checked by POST /check (okay, no lint, no sorry):

```lean
import Mathlib

/-- Step 4 of the annex: an odd multiple of p that is 2^a times an integer, and an integer
multiple M p, give M p = 2^a z. -/
theorem combine_two_adic_odd (p M : ℚ) (a : ℕ) (Ω A B m : ℤ) (hΩ : Odd Ω)
    (h1 : (Ω : ℚ) * p = 2 ^ a * A) (h2 : (B : ℚ) = M * p) (hm : (m : ℚ) = M) :
    ∃ z : ℤ, (z : ℚ) * 2 ^ a = M * p := by
  have hint : Ω * B = 2 ^ a * (m * A) := by
    have : ((Ω * B : ℤ) : ℚ) = ((2 ^ a * (m * A) : ℤ) : ℚ) := by
      push_cast
      rw [h2, ← hm]
      linear_combination (m : ℚ) * h1
    exact_mod_cast this
  obtain ⟨t, ht⟩ := hΩ
  have hcop : IsCoprime ((2 : ℤ) ^ a) Ω := by
    apply IsCoprime.pow_left
    exact ⟨-t, 1, by rw [ht]; ring⟩
  have hdvd : (2 : ℤ) ^ a ∣ B * Ω := ⟨m * A, by rw [mul_comm, hint]⟩
  obtain ⟨c, hc⟩ := hcop.dvd_of_dvd_mul_right hdvd
  refine ⟨c, ?_⟩
  rw [← h2, hc]
  push_cast
  ring
```
