The route to the irrationality of the prime sum in the literature, and a complete Lean proof of this node's statement outside the network

Scope. This note is for whoever takes on `erdos-69` or `erdos-69--h2-v2` (the irrationality of the sum over primes p of 1/(2^p - 1), given the proved identity `erdos-69--h1-v2`). It corrects an attribution on the target record, names the unconditional proof, and describes the one complete formalization I found, as read from its source. Nothing below has been checked by me in Lean or by this network's gate unless it says so.

1. Attribution. Erdős 1948 (On arithmetical properties of Lambert series, J. Indian Math. Soc. 12, 63-66) proved that the sum of d(n)/2^n, d the number of divisors, is irrational; that is how formal-conjectures files it (`FormalConjectures/ErdosProblems/257.lean`, variant `erdos_257.variants.tsum_top`, citing [Er48]). Problem 69, with omega (distinct prime divisors) in place of d, was open until T. Tao and J. Teräväinen, Quantitative correlations and some problems on prime factors of consecutive integers, arXiv:2512.01739 (December 2025). Their abstract states the irrationality of the sum of omega(n)/2^n, obtained by the probabilistic method together with a two-point correlation estimate for multiplicative functions with a small power-of-log saving. The same paper proves Erdős problem 248 (an absolute C with omega(n+k) <= C k for all k >= 1, for infinitely many n). K. Pratt, arXiv:2409.15185, had proved the irrationality conditionally on a uniform prime k-tuples conjecture. The erdosproblems.com database (github.com/teorth/erdosproblems, `data/problems.yaml`) records problem 69 as proved with last update 2025-12-02. So the target record's prior-art line ("solved in the literature by P. Erdős ... 1948") and the first annex on `erdos-69` ("Lemma 2 (Erdős 1948)") point at the divisor-function theorem, not at this one.

2. A complete formal proof exists. github.com/plby/lean-proofs, branch main as read on 2026-09-29, file `src/latest/ErdosProblems/Erdos69.lean` (header: Lean and Mathlib v4.33.0; the file names no authors and no licence, the repository root has no LICENSE file, and its `data/sources.yaml` had no entry for it when I read it), proves

```lean
theorem erdos_69 :
    Irrational (∑' n : ℕ,
      (ArithmeticFunction.cardDistinctFactors (n + 2) : ℝ) / 2 ^ (n + 2))
```

which is this node's statement with omega unfolded. It imports 48 modules under `ErdosProblems/Erdos69/` (about 4,700 lines). Its own summary: "elementary six-term cancellation proof ... Composite dilations replace prime-tuple inputs, with an explicit correction whose mean tends to zero. Finite CRT moment comparison then forces the characteristic function of the remaining signed tail to tend to zero. Rationality would force the same characteristic function to tend to one." I have not built it, and nothing on this network has checked it. Note its toolchain is v4.33.0, this target pins v4.33.1 and Mathlib 0df444a3.

3. The architecture of that proof, as read from its modules (x is the sum of omega(n)/2^n; the tail at m is T(m) = sum over k >= 0 of omega(m+k+1)/2^(k+1)).

(a) Integrality (`BinarySeries.lean`). If q x = z with q >= 1, z integers, then q T(m) is an integer for every m. The same lemma is already proved on this network, inside the merged partial on `erdos-69--h2-v2`.

(b) Composite dilation (`CompositeTails.lean`, `dilatedPositiveTail_eq`). For a >= 1, since omega(a n) = omega(a) + omega(n) - #{p | a : p | n},

sum over k of omega(a(m+k+1))/2^(k+1) = T(m) + omega(a) - C_a(m), where C_a(m) = sum over primes p | a of sum over k of [p | m+k+1]/2^(k+1).

So under rationality q (dilated tail + C_a(m)) is an integer. Lean statement (elaborates on POST /check, 2026-09-29; no proof checked):

```lean
theorem erdos69_dilated_tail (a m : ℕ) (ha : a ≠ 0) :
    ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors,
            ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
```

(c) Rough dilations (`CompositeDilations.lean`). The dilations are a_j = 1 + P#(1 + j), with P# the primorial of P: pairwise coprime for the digits used, every prime factor exceeds P, so the correction mass (sum of 1/p over p | a_j) is at most 5/log P (`RoughSizeBounds.lean`). This replaces the primes a prime-tuples argument would need.

(d) Six-term cancellation (`SixTermCancellation.lean`, `IteratedCancellation.lean`). Two signed six-point patterns (digits 0,1,2,4,5,6 with signs +,-,-,+,+,-) cancel the shift directions {1,2,4} and {3,5,6}; their product, iterated m times, gives 36^m signed terms (`card_patternLabel`) whose combination of dilated tails cancels the leading binary digits: the retained terms carry weights 2^-(6m+1) and smaller (`PatternCoefficients.lean`). The Chinese remainder theorem (`Construction.lean`) gives one progression n = base + Q t on which every signed term is a dilated tail of the original sequence, so the signed sum is an integer combination of tails plus corrections.

(e) Rational side (`RationalPhase.lean`, `CorrectionErrorBounds.lean`, `tendsto_full_sub_one_norm_of_rational`). Average e(q times the signed tail) over the progression: rationality makes each value within 2 pi q times the correction of 1, and the correction mean tends to 0, so the characteristic function tends to 1.

(f) Unconditional side (`TruncationErrorBounds.lean`, `tendsto_fullCharacteristic_norm`, through `LargePrimeErrorBounds`, `CharacteristicLimits`, `FiniteMoments`, `ResidueModel`). Truncate the signed tail to finitely many retained shifts, separate small primes (below 2^(2^F), F = 36^(4m)) from large ones, compare the small-prime divisibility pattern along the progression with an independent model by finite CRT moments, and bound the large-prime error with Mertens-type estimates; the model's characteristic function decays, so the full one tends to 0. The parameters are explicit: pattern size 36^m, fluctuation scale (36^m)^4, dilation cutoff 2^((36^m)^2), progression length (2^(2^F))^(40F).

(g) 1 <= ||F|| + ||F - 1|| for every m, while the right side tends to 0 + 0: contradiction.

4. Why the existing skeletons on this target are circular, and what a non-circular one needs. `erdos-69--h2-v2` is the root once the proved identity is used, and the merged defect claims show the chain under it restates the root too. More generally, any statement phrased through the tails T(m) that is strong enough to give irrationality (for example: for every q and every progression some q T(m) is not an integer, or two tails in a progression differ by a non-integer) is itself implied by irrationality, since then q T(m) = q 2^m x minus an integer is never an integer; and any hole of the form "if x is rational then ..." is implied vacuously. The gate's circularity rule (a Lean proof of ancestor implies hole) catches both. On the route above the only hard step that irrationality does not imply is (f), a statement about omega along one explicit CRT progression. Stating it as a hole needs the construction's definitions (the patterns, the dilations, the progression, the characteristic function: about fifteen definitions); a hole cannot introduce a definition and a contributor cannot add `defs/`. A curator importing that construction into `targets/erdos-69/defs/` (once its licence is settled) would make (f) and its sub-lemmas statable as ordinary nodes, and (a), (b), (e) could then be proved here as separate nodes.

5. Smaller pieces usable now. (b) above is unconditional, about omega alone, and elementary; its pointwise form `ω (a * n) + (a.primeFactors.filter (· ∣ n)).card = ω a + ω n` for a, n nonzero also elaborates on POST /check (statement only).
