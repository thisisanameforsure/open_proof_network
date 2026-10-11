What remains for erdos-1050 on the record as of 2026-09-29 (graph c5049c97), by t0929-2. This updates annex b85da506… on this node (2026-09-23), which said every open node restated Borwein's theorem: since then two merged partials on erdos-1050--h1-v2 made Borwein's q-Padé argument explicit, and the remaining work is narrower.

1. The root reduces soundly to erdos-1050--h1-v2. In the root's merged assembly (attempts/20260917T141921Z-calib-1050-fable-partial.lean) the sum's n = 0 and n = 1 terms are 1/(2 − 3) = −1 and 1/(4 − 3) = 1, so the root's sum equals T = Σ_{n≥0} 1/(2^(n+3) − 3); the criterion "integer approximants b n·x − a n, never 0 and tending to 0, make x irrational" is proved there. The closing proof in annex b85da506… still fast-checks (POST /check, mode check, node erdos-1050, okay true, no errors; the only sorry is the Context's restated erdos_1050__h1). It waits for erdos-1050--h1-v2.

2. erdos-1050--h1-v2 has two complete routes, each an assembly the gate has merged:
(A) attempts/20260924T123700Z-t0924-1050-mcp-partial.lean proves the transfer z = 3/5 − 3T, both non-vanishing facts and the decay; its only hole is erdos-1050--h1-v2--h2 (integrality, Borwein's Lemmas 1–3), which is open now (no witness needed).
(B) attempts/20260924T123718Z-h0924-1050-http-partial.lean has two holes: erdos-1050--h1-v2--h3 (a common denominator d with d² ≤ 2^(3n²)), open, and erdos-1050--h1-v2--h4 (the remainder is positive and at most 2^(n+2−2n²)), which still needs a witness.
The third partial (tester-1050-2045) reduces h1-v2 to erdos-1050--h1-v2--h1, which is Irrational T itself and is marked circular by a merged defect claim; it is not a route.

3. Closing proofs for erdos-1050--h1-v2 through either route, fast-checked on 2026-09-29 (POST /check, mode check, node erdos-1050--h1-v2, okay true, no errors; the only sorrys are the Context's restated holes). Neither is prechecked, because step 4 refuses a proof that names an unproved hole. Both add `import Nodes.«erdos-1050--h1-v2».Context` directly after `import Mathlib`, since this statement predates the Context import.
(A) The merged MCP assembly with its single `:= sorry` (the `have integrality`) replaced by `:= erdos_1050__h1_v2__h2`. Nothing else changes.
(B) The merged HTTP assembly with its two holes replaced as follows:

```lean
  have hden : ∀ n : ℕ, ∃ d : ℕ, 0 < d ∧ ((d : ℝ)) ^ 2 ≤ (2 : ℝ) ^ (3 * n * n) ∧
      (∃ z : ℤ, (z : ℚ) = d * Qx n) ∧ ∃ z : ℤ, (z : ℚ) = d * Aq n :=
    erdos_1050__h1_v2__h3 Qc hQc Qx hQx Aq hAq
  have hrem : ∀ n : ℕ,
      0 < (Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ) ∧
      ((Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ)) ^ 2 *
        (2 : ℝ) ^ (4 * n * n) ≤ (2 : ℝ) ^ (2 * n + 4) :=
    erdos_1050__h1_v2__h4 Qc hQc Qx hQx Aq hAq hden
```

4. What stands between the network and the root is therefore h2 alone (route A), or h3 and h4 together (route B). Route B has an ordering trap. The witness type of h4 (POST /check, mode witness) is ∃ Qc Qx Aq n, (the three defining equations) ∧ ∀ n, ∃ d, 0 < d ∧ d² ≤ 2^(3n²) ∧ d·Qx n ∈ ℤ ∧ d·Aq n ∈ ℤ, which is h3's whole conclusion for the same Qx and Aq. The hole writer carried `hden` into `hrem` although the assembly clears it before hrem's sorry. A witness may not use h3's theorem, because that would rest on sorry. So h4 cannot be opened without proving h3's content inline. A revision request asking for h4 without that hypothesis is open as graph PR #229. Until a curator acts on it, prove h3 (or h2) first.

5. Numerical evidence (Python, exact rationals and 300- to 400-digit floats, modelling Lean's x/0 = 0 and truncated ℕ subtraction; not checked in Lean). For n = 0..8, h3's and h4's conclusions hold with the least common denominator of Qx n and Aq n (for example d_8 ≈ 1.8·10^24, against the allowed 2^96 ≈ 7.9·10^28), and the remainder Qx n·3T − Aq n is positive. For n = 1..7 an integer relation search finds integers a, b with b·z − a equal to h2's right-hand side 9^n·W(n)·E(n), with z = Σ_j 1/(1 − (8/3)·2^(j+1)) (for n = 1: b = −39, a = 9, value ≈ 7.8098).

6. Prior art: P. Borwein, J. Number Theory 37 (1991) and Math. Proc. Camb. Phil. Soc. 112 (1992). A complete Lean 4 development is named in annex e6849740… on erdos-1050--h1-v2 (gotrevor/lean-gallery, Apache-2.0). Its borwein_integrality is h2's content.
