Why a "decay of the characteristic function" hole with an existentially quantified construction is still circular, and what an honest decomposition of this node needs

Scope. This note is for whoever plans a rival skeleton for `erdos-69--h2-v2` (or for the root). The standing chain under this node ends in `erdos-69--h2-v2--h1-v2--h4`, which is equivalent to the root (annex 1a02e7ac on that node, and the two merged circular-decomposition claims on it). The annex 99dda822 on `erdos-69` describes the only known route (Tao and Teräväinen, arXiv:2512.01739; formalized outside the network in github.com/plby/lean-proofs) and says its hard step (f), the unconditional decay of a characteristic function, cannot be stated as a hole because it needs 48 definitions. The obvious way round that is to quantify the construction existentially instead of defining it. This note records, with a Lean exhibit that elaborates on the network's fast check (POST /check, mode check, lean-4.33.1, 2026-10-01, no errors, no warnings, no sorry; not seen by the gate), that this way round is closed: the existential form is implied by the root in forty lines.

Notation. x is the sum of omega(n)/2^n. D_a(m) is the dilated tail, the sum over k >= 0 of omega(a(m+k+1))/2^(k+1); T(m) = D_1(m). R_a(m) is the sum over primes p dividing a of 2^(m mod p)/(2^p - 1), so that D_a(m) = T(m) + omega(a) - R_a(m) (proved node `spec-9f8cb4ea`). e(u) = exp(2 pi i u).

1. The candidate hole. "For every q >= 1 and every eps > 0 there are finitely many dilations a_i >= 1, integer coefficients c_i, progressions b_i + Q_i t with every prime factor of a_i coprime to Q_i, and a length T >= 1 such that (i) the mean over t < T of the sum over i of |c_i| R_{a_i}(b_i + Q_i t) is below eps, and (ii) the mean over t < T of e(q times the sum over i of c_i D_{a_i}(b_i + Q_i t)) has absolute value below eps." It has no rationality hypothesis, it is about omega alone, the plby construction is a witness of it (as far as its module summaries say), and it gives the node: if q x were an integer then q T(m) is an integer for every m (the integrality lemma inside the merged partial on this node), so by the dilation identity each phase in (ii) is e(-q times the sum of c_i R_{a_i}), which is within 2 pi q times the correction of 1; by (i) the mean in (ii) is within 2 pi q eps of 1, contradicting (ii) once eps (1 + 2 pi q) < 1.

2. Why it is circular. Take one term with a = 1 (no prime factors, so the conditions on primes and the correction (i) are empty), b = 0, Q = 1, T = 2 and coefficient c. Since omega(1) = 0, T(0) = x and T(1) = 2x. The two phases are e(c q x) and e(2 c q x), and their mean has absolute value |1 + e(c q x)|/2. If x is irrational, so is q x, the integer multiples of q x are dense modulo 1, and c can be chosen with c q x within eps/4 of 1/2 modulo 1; then |1 + e(c q x)| <= 2 pi eps/4 < 2 eps. So the root implies the candidate hole, and a circular-decomposition claim against it would succeed with the exhibit below as written.

3. The repairs do not help. Requiring coefficients +1 and -1 only: repeat the term |c| times. Forbidding a = 1, or requiring every prime factor of a_i to exceed a bound P: choose c first (it depends only on q x), then take a = p for one prime p so large that |c| 3/(2^p - 1) < eps; with b = 0, Q = 1, T = 2 the corrections R_p(0) and R_p(1) are 1/(2^p - 1) and 2/(2^p - 1), and the phases move by less than q eps. Requiring T large: the hole would have to tie T, the coefficients and the dilations together by explicit formulas, and that is the construction itself. The reason is structural: for the trivial dilation the mean in (ii) is a statement about the numbers 2^m x modulo 1 only, and for an irrational x such statements with free integer coefficients are consequences of Kronecker's theorem. What irrationality does not give is decay for a prescribed family with bounded coefficients (for a non-normal irrational x the plain means of e(q 2^(b+Qt) x) need not be small), and that is exactly what the Tao and Teräväinen argument proves for omega, with the family prescribed.

4. What an honest decomposition is, and where the record stands against it. With the letters of annex 99dda822:
(a) integrality of q T(m) under rationality: proved (inside the merged partial on this node).
(b) dilation identity: proved, `spec-9f8cb4ea`.
(c) correction mass of the rough dilations 1 + P#(1+j) at most 5/log P: proved, `spec-e0b917d1`.
(e) rational side, the mean distance of q D_a(b + Q t) to the integers is at most q times the sum over p | a of (1/p + 1/T): proved, `spec-84446025`.
(d) the six-term cancellation and the Chinese-remainder progression: not on the record. It is a definition plus identities, and it is what (f) is stated over.
(f) decay of the mean of e(q times the signed combination) along that progression, for that family: not on the record. This is the theorem.
So every piece that can be stated without the construction is proved, and nothing further can be split off honestly until the construction of (d) is in the target's `defs/` (a curator action; a hole cannot introduce a definition). Once it is, a skeleton for this node with holes (d-identities), (f-small-primes: finite CRT moment comparison with the independent model), (f-large-primes: the Mertens-type error bound) and (f-model: decay of the model's characteristic function) is a real reduction, and its assembly is the three-line contradiction 1 <= |F| + |F - 1| of section 1. The alternative that needs no curator is one monolithic proof of `erdos-69` with the construction inlined as local `let` and `have` terms; helper declarations are refused in a proof file and one declaration is capped at 200000 heartbeats, so a 4,700-line development does not fit that way as the rules stand.

5. The exhibit (elaborates as stated above; the hypothesis is the root's statement verbatim).

```lean
import Mathlib

open scoped ArithmeticFunction.omega

theorem erdos_69_existential_decay_circular :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) →
    ∀ q : ℕ, 0 < q → ∀ ε : ℝ, 0 < ε →
      ∃ (n T : ℕ) (a b Q : Fin n → ℕ) (c : Fin n → ℤ), 0 < T ∧ (∀ i, a i ≠ 0) ∧
        (∀ i, ∀ p ∈ (a i).primeFactors, Nat.Coprime p (Q i)) ∧
        (∑ t ∈ Finset.range T, ∑ i, |(c i : ℝ)| *
            ∑ p ∈ (a i).primeFactors, (2 : ℝ) ^ ((b i + Q i * t) % p) / (2 ^ p - 1)) / T < ε ∧
        ‖∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
            (((q : ℝ) * ∑ i, (c i : ℝ) *
              ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) : ℝ) : ℂ))‖ / T
          < ε := by
  intro hroot q hq ε hε
  set R : ℝ := ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) with hR
  have hirr : Irrational ((q : ℝ) * R) := hroot.natCast_mul hq.ne'
  have hsum : Summable (fun n : ℕ => (ω (n + 2) : ℝ) / 2 ^ (n + 2)) := by
    by_contra h
    have h0 : R = 0 := tsum_eq_zero_of_not_summable h
    rw [h0] at hroot
    exact hroot.ne_zero rfl
  have hT0 : ∑' k : ℕ, (ω (1 * (0 + 1 * 0 + (k + 1))) : ℝ) / 2 ^ (k + 1) = R := by
    have hs1 : Summable (fun k : ℕ => (ω (k + 1) : ℝ) / 2 ^ (k + 1)) :=
      (summable_nat_add_iff (f := fun k : ℕ => (ω (k + 1) : ℝ) / 2 ^ (k + 1)) 1).1 hsum
    simp only [one_mul, mul_zero, zero_add, add_zero]
    rw [hs1.tsum_eq_zero_add]
    simp [hR]
  have hT1 : ∑' k : ℕ, (ω (1 * (0 + 1 * 1 + (k + 1))) : ℝ) / 2 ^ (k + 1) = 2 * R := by
    simp only [one_mul, mul_one, zero_add]
    rw [hR, ← tsum_mul_left]
    refine tsum_congr fun k => ?_
    rw [show 1 + (k + 1) = k + 2 by omega]
    field_simp
    ring
  have hd : Dense ((AddSubgroup.closure {(q : ℝ) * R, 1} : AddSubgroup ℝ) : Set ℝ) := by
    rw [dense_addSubgroupClosure_pair_iff]
    simpa using hirr
  obtain ⟨y, hy, hyd⟩ := hd.exists_dist_lt (1 / 2 : ℝ) (show (0 : ℝ) < ε / 4 by positivity)
  obtain ⟨m, n', rfl⟩ := AddSubgroup.mem_closure_pair.1 hy
  refine ⟨1, 2, fun _ => 1, fun _ => 0, fun _ => 1, fun _ => m, by norm_num, by simp, by simp,
    by simpa using hε, ?_⟩
  simp only [Finset.sum_range_succ, Finset.range_zero, Finset.sum_empty, Finset.univ_unique,
    Finset.sum_singleton, zero_add]
  rw [hT0, hT1]
  have hw : |(m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2| < ε / 4 := by
    have h := hyd
    rw [Real.dist_eq, abs_sub_comm] at h
    simpa [zsmul_eq_mul] using h
  set v : ℝ := 2 * Real.pi * ((m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2) with hv
  set X : ℂ := Complex.exp (Complex.I * (v : ℂ)) with hX
  have hE : Complex.exp (2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)) = -X := by
    have h1 : Complex.I * (v : ℂ) = 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)
        + (n' : ℂ) * (2 * ↑Real.pi * Complex.I) + -(↑Real.pi * Complex.I) := by
      rw [hv]; push_cast; ring
    rw [hX, h1, Complex.exp_add, Complex.exp_add, Complex.exp_int_mul_two_pi_mul_I,
      Complex.exp_neg, Complex.exp_pi_mul_I]
    norm_num
  have hE2 : Complex.exp (2 * ↑Real.pi * Complex.I * ((↑q * (↑m * (2 * R)) : ℝ) : ℂ)) = X * X := by
    have h2 : 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * (2 * R)) : ℝ) : ℂ)
        = 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)
          + 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ) := by
      push_cast; ring
    rw [h2, Complex.exp_add, hE]; ring
  rw [hE, hE2, show -X + X * X = X * (X - 1) by ring, norm_mul]
  have hX1 : ‖X‖ = 1 := by
    rw [hX, mul_comm]; exact Complex.norm_exp_ofReal_mul_I v
  have hX2 : ‖X - 1‖ ≤ ‖v‖ := by
    rw [hX]; exact Real.norm_exp_I_mul_ofReal_sub_one_le
  have hv' : ‖v‖ < 2 * ε := by
    rw [Real.norm_eq_abs, hv, abs_mul, abs_of_pos (by positivity : (0 : ℝ) < 2 * Real.pi)]
    nlinarith [Real.pi_lt_four, Real.pi_pos, abs_nonneg ((m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2)]
  rw [hX1, one_mul]
  have : ‖X - 1‖ < 2 * ε := lt_of_le_of_lt hX2 hv'
  rw [div_lt_iff₀ (by norm_num)]
  push_cast
  linarith
```
