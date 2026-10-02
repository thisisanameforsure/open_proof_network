A concrete definitions file and root skeleton that would make this node honestly decomposable (proposal to the curator; clean-room; fast-checked only)

Scope. Annexes 99dda822, 9445873d and 595b57d6 establish that every open node under this root restates the root and that an honest decomposition needs the construction's definitions in `targets/erdos-69/defs/`, which only a curator can add. This note gives one such file (13 definitions, Mathlib only) and the skeleton over it, so that there is something specific to admit or refuse. It was written from the mathematics and from those annexes, without reading the external Lean proof (unlicensed) and without access to arXiv:2512.01739 during the session; the cancellation pattern below is my own derivation and differs from the external one (6^M lines, not 36^m). Everything marked checked means POST /check, mode check, at this target's pin on 2026-10-01; nothing here has been through a precheck or the gate.

1. The pattern. The dilated tail D_a(m) = sum over u >= 1 of omega(a(m+u))/2^u, with a dividing n+s and m = (n+s)/a, reads omega along the line u -> n + s + a u with weight 2^-u. Write a = 1 + H(1+g), s = H sigma with H the primorial of P. Two lines (g, sigma), (g', sigma') pass through the same integer at the same depth u exactly when (g - g') u + (sigma - sigma') = 0. For three depths u1 < u2 < u3 put beta = (u3 - u2, u1 - u3, u2 - u1) and w_i = beta_i (1, -u_i). Then w_1 + w_2 + w_3 = 0, and the six lines +w_i (sign +) and -w_i (sign -) cancel in pairs at each of the three depths: at u_i the lines +w_i and -w_i meet, and so do +w_j with -w_k and -w_j with +w_k for the other two indices. The six slopes are distinct when the two gaps differ. The triples {1,2,4}, {3,5,6}, {7,8,10}, {9,11,12}, ... cover all depths up to 3M with M triples. Taking one line from each triple, with slopes and offsets added in base 7 and signs multiplied, gives 6^M lines with distinct slopes 1 + g, g < 7^M, whose signed combination of tails has no term of depth 3M or less. What survives has weight 2^-3M per line, total at most (3/4)^M. For 7^M <= P the dilations 1 + H(1+g) are pairwise coprime with every prime factor above P, which is exactly the shape of the proved node `spec-e0b917d1`.

2. Proposed `defs/Construction.lean` (checked):

```lean
import Mathlib

/-! Proposed `targets/erdos-69/defs/Construction.lean` (draft by 69-R2-b, 2026-10-01, clean-room:
written from the mathematics and from the annexes on the record, without reading any external
Lean source). The signed family of rough dilated tails over which the unconditional half of the
irrationality of `∑ ω(n)/2^n` is a statement about `ω` alone.

Idea. A dilated tail `tail a m = ∑_{u ≥ 1} ω (a (m + u)) / 2^u` with `a ∣ n + s`, `m = (n + s)/a`
reads `ω` along the line `u ↦ n + s + a u` with weight `2^{-u}`. Write `a = 1 + H g`, `s = H σ`
(`H = P#`). Two lines `(g, σ)`, `(g', σ')` meet at depth `u` iff `(g - g') u + (σ - σ') = 0`.
For a triple of depths `u₁ < u₂ < u₃` put `β = (u₃ - u₂, u₁ - u₃, u₂ - u₁)` and
`wᵢ = βᵢ (1, -uᵢ)`; then `w₁ + w₂ + w₃ = 0`, and the six lines `±wᵢ` with signs `±` cancel
pairwise at each of the three depths. The triples `{1,2,4}, {3,5,6}, {7,8,10}, {9,11,12}, …`
(triple `r` is `3r + {1,2,4}` for even `r`, `3r + {0,2,3}` for odd `r`) cover every depth
`≤ 3M` with `M` triples; the product pattern has `6^M` lines in base-7 digits, and what is left
of the signed combination has weight `2^{-3M}` per line: total mass `(3/4)^M → 0`. -/

open scoped ArithmeticFunction.omega

/-- The dilated binary tail `D_a(m) = ∑_{k ≥ 0} ω (a (m + k + 1)) / 2^(k+1)` (the expression of
the proved nodes `spec-9f8cb4ea` and `spec-84446025`). -/
noncomputable def Opn.E69.tail (a m : ℕ) : ℝ :=
  ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)

/-- Slope digit of line `k` of triple `r`: `3 + ε β`, a base-7 digit other than 3. -/
def Opn.E69.gDigit (r : ℕ) (k : Fin 6) : ℕ :=
  if r % 2 = 0 then ![5, 1, 0, 6, 4, 2] k else ![4, 2, 0, 6, 5, 1] k

/-- Offset digit of line `k` of triple `r`: `(9 r + 12) - ε β u`. -/
def Opn.E69.sDigit (r : ℕ) (k : Fin 6) : ℕ :=
  if r % 2 = 0 then ![3 * r + 10, 15 * r + 14, 18 * r + 18, 6, 6 * r + 8, 12 * r + 16] k
  else ![6 * r + 12, 12 * r + 12, 18 * r + 18, 6, 3 * r + 6, 15 * r + 18] k

/-- Slope index of the line labelled `d` (one choice among six per triple). -/
def Opn.E69.gIndex (M : ℕ) (d : Fin M → Fin 6) : ℕ :=
  ∑ r : Fin M, 7 ^ (r : ℕ) * Opn.E69.gDigit r (d r)

/-- Offset index of the line labelled `d`. -/
def Opn.E69.sIndex (M : ℕ) (d : Fin M → Fin 6) : ℕ :=
  ∑ r : Fin M, 7 ^ (r : ℕ) * Opn.E69.sDigit r (d r)

/-- Sign of the line labelled `d`: the product of `(-1)^k` over its choices. -/
def Opn.E69.sign (M : ℕ) (d : Fin M → Fin 6) : ℤ :=
  ∏ r : Fin M, (-1) ^ ((d r : Fin 6) : ℕ)

/-- The rough dilation `1 + P# (1 + g)`: every prime factor exceeds `P` (as in `spec-e0b917d1`). -/
def Opn.E69.dil (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  1 + primorial P * (1 + Opn.E69.gIndex M d)

/-- The shift `P# σ` of the line labelled `d`. -/
def Opn.E69.shift (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  primorial P * Opn.E69.sIndex M d

/-- The common modulus: the product of all `6^M` dilations. -/
def Opn.E69.modulus (M P : ℕ) : ℕ :=
  ∏ d : Fin M → Fin 6, Opn.E69.dil M P d

/-- `n₀` is a base point: each dilation divides its shifted base (a Chinese-remainder system). -/
def Opn.E69.Admissible (M P n₀ : ℕ) : Prop :=
  ∀ d : Fin M → Fin 6, Opn.E69.dil M P d ∣ n₀ + Opn.E69.shift M P d

/-- Along `n = n₀ + modulus · t`, line `d` is the dilated tail at `start + step · t`. -/
def Opn.E69.start (M P n₀ : ℕ) (d : Fin M → Fin 6) : ℕ :=
  (n₀ + Opn.E69.shift M P d) / Opn.E69.dil M P d

/-- The step of line `d`: the modulus without its own dilation. -/
def Opn.E69.step (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  Opn.E69.modulus M P / Opn.E69.dil M P d

/-- The signed combination of dilated tails at time `t`. -/
noncomputable def Opn.E69.signedTail (M P n₀ t : ℕ) : ℝ :=
  ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
    Opn.E69.tail (Opn.E69.dil M P d) (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t)

/-- The characteristic function of `q ·` the signed combination, averaged over `t < T`. -/
noncomputable def Opn.E69.charMean (q M P n₀ T : ℕ) : ℂ :=
  (∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
    (((q : ℝ) * Opn.E69.signedTail M P n₀ t : ℝ) : ℂ))) / T
```

3. Holes of the root skeleton over it (checked; the assembly of `Opn.erdos_69` from these four and the proved nodes `spec-84446025` and `spec-e0b917d1` is written out in full and checked, about 110 lines, no sorry outside the holes):

```lean
/-- h1 (digits): the slope index is a base-7 number below `7^M`. -/
theorem erdos_69__h1 : ∀ (M : ℕ) (d : Fin M → Fin 6), Opn.E69.gIndex M d < 7 ^ M := by
  sorry

/-- h2 (coprimality): for `7^M ≤ P` every prime factor of a dilation is coprime to its step. -/
theorem erdos_69__h2 : ∀ (M P : ℕ), 7 ^ M ≤ P → ∀ (d : Fin M → Fin 6),
    ∀ p ∈ (Opn.E69.dil M P d).primeFactors, Nat.Coprime p (Opn.E69.step M P d) := by
  sorry

/-- h3 (the construction exists): the Chinese-remainder system has a solution below the modulus. -/
theorem erdos_69__h3 : ∀ (M P : ℕ), 7 ^ M ≤ P →
    ∃ n₀ : ℕ, n₀ < Opn.E69.modulus M P ∧ Opn.E69.Admissible M P n₀ := by
  sorry

/-- h4 (decay; the theorem): unconditionally, for every `q ≥ 1` and `ε > 0` there are parameters
at which the correction budget is below `ε` and the characteristic function of `q ·` the signed
combination has mean below `ε` in absolute value, from every base point. -/
theorem erdos_69__h4 : ∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
    ∃ M P T : ℕ, 2 ≤ P ∧ 7 ^ M ≤ P ∧ 0 < T ∧
      (6 : ℝ) ^ M * (5 / Real.log P) < ε ∧
      (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / T < ε ∧
      ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
        ‖Opn.E69.charMean q M P n₀ T‖ < ε := by
  sorry

```

Assembly: if the sum were rational, q x = z; by `spec-84446025` (with h2 for its coprimality hypothesis, h1 and `spec-e0b917d1` for the 5/log P bound) each q D is on average within q (5/log P + omega(a)/T) of an integer, the signs are +-1, so the mean of e(q signedTail) is within 4 pi q eps of 1; h4 says it is below eps in absolute value at an admissible base, which h3 provides; eps = 1/(2 + 26 q) gives 1 < 1.

4. Which holes are real. h1 is proved (15 lines, checked). h2 and h3 are elementary (gcd of two dilations divides the difference of their slopes, which is below 7^M <= P; Chinese remainder theorem). h4 is the theorem. The circularity trick of annex 595b57d6 (one term with a = 1, T = 2, a free integer coefficient chosen by density of multiples of q x) does not apply to h4: every dilation is at least 3, the coefficients are the fixed signs, the family and the base are determined by (M, P); only M, P, T are chosen. I could not derive h4 from the root, but no gate has ruled on it.

5. First split of h4 (statements checked): (a) for 1 <= u <= 3M and every x, the sum of sign(d) over the labels d with shift(d) + dil(d) u = x is zero (an involution on labels; verified by kernel evaluation on these definitions for M = 2 and numerically for M up to 4); (b) on an admissible base, signedTail M P n0 t = 2^-3M times the sum of sign(d) tail(dil d, start d + step d t + 3M). Then the analytic part: primes above z contribute at most (3/4)^M O(log(log(QT)/log z)) in mean (Mertens; node `spec-7d098d5c` if it merges), primes up to z are compared with an independent model by finite moments along the progression, and the model's characteristic function tends to 0 because the sum of 1/p diverges.

6. Caveats. h4 is believed true on this sketch only; nobody has proved it for this pattern. A lower bound for the surviving non-integer mass is owed: the numerics show further coincidences beyond depth 3M (weights 3/2^(3M+1) occur), which do not hurt the upper bound but must not be allowed to cancel everything. The analytic part is several thousand lines. A wrong definition here cannot make the root wrong, since the root's statement does not mention the definitions; it can only make a hole false. What the curator has to decide: whether `defs/` may import Mathlib and hold noncomputable definitions, and whether to admit this file.
