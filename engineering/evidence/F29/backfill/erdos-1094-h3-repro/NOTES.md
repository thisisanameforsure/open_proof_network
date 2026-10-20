# erdos-1094--h3 — "Small range 2k ≤ n < k²: k is bounded": reproduction notes (2026-10-19)

Not committed; graph.json untouched. Scripts: `check_h3.py` (→ `output.txt`), `check_hgr_ext.py`
(→ `output_hgr_ext.txt`). Run with `uv run --no-project --with numpy --with sympy python <script>`.

## Source
The node's live decomposition (annex `1df9e201…`) is **Granville–Ramaré, Mathematika 43 (1996)
73–107, Theorem 8, proof §5e** (preprint pp. 24–25). Theorem 8: lpf C(n,k) > k ⇒ n > exp(c(log³k/log log k)^{1/2}),
which exceeds k² for large k. **I did not re-read the paper**; page references and quotations are
those recorded by agents t1015b-g/h in the annex. Status: cited, not verified by me.

## Statement (node)
∃K ∀n,k: 0<k, 2k ≤ n < k², lpf C(n,k) > k ⇒ k ≤ K.

## Proof (assembly) — proved here, every step checked
Holes (cited): 
- h_els [ELS 1993, cited by GR]: ∃C,K₁: k>K₁, 2k≤n, lpf C(n,k)>k ⇒ k² ≤ C·n·⌊log₂k⌋.
- h_gr [GR §5e]: ∀C ∃K₂: k>K₂, k² ≤ C n ⌊log₂k⌋, n<k² ⇒ ∃ prime p, k/2<p<11k/20, n mod p < k mod p.

**Lemma L (proved).** p prime, n ≥ k, n mod p < k mod p ⇒ p | C(n,k).
Legendre: v_p(C(n,k)) = Σ_{i≥1} (⌊n/pⁱ⌋ − ⌊k/pⁱ⌋ − ⌊(n−k)/pⁱ⌋), each term ∈ {0,1}. For i=1 write
n = ap+r, k = bp+s, r < s. Then n−k = (a−b−1)p + (p+r−s) with 0 < p+r−s < p, so the i=1 term is
a − b − (a−b−1) = 1. Hence v_p ≥ 1. (Brute-force check, k ≤ 40, n ≤ 400: 0 violations.)

**Assembly.** Take C,K₁ from h_els, K₂ from h_gr(C), K = max(K₁,K₂). Suppose k > K, 2k ≤ n < k²,
lpf C(n,k) > k. h_els ⇒ k² ≤ C n ⌊log₂k⌋; with n < k², h_gr gives a prime p < 11k/20 < k with
n mod p < k mod p; Lemma L ⇒ p | C(n,k), so lpf ≤ p < k. Contradiction. ∎ (Matches annex §3, which
says the Lean assembly is checked.)

## Reduction of h_gr to its children (proved here, given the children)
Children: h_cheb = erdos-1094--h3--h3--h1 (S(k) := Σ_{k/2<p<11k/20} log p ≥ k/100 for large k) and
Lemma 5.1 = erdos-1094--h3--h3--h2--h1 (for every δ, large k in the range, every σ∈[0,1]:
|Σ [ {n/p} < σ ] log p − σ S(k)| ≤ δk).
For p in (k/2, 11k/20): 1 < k/p < 2 so k mod p = k − p, and k − p > 9p/11 ⇔ p < 11k/20.
So if NO such p carries, n mod p ≥ k−p > 9p/11, i.e. {n/p} > 9/11 for all of them, and the
σ = 9/11 sum is 0. Lemma 5.1 with δ = 1/200 gives 0 ≥ (9/11)S(k) − k/200 ≥ (9/1100 − 1/200)k > 0
(9/1100 ≈ 0.00818 > 0.005). Contradiction, so h_gr holds with K₂ = max(K₃,K₅). This bypasses
h3--h3--h2 (the ψ-sum form); the annex's route via (5.1) with ε = 1/1000 is equally valid
((7/22)(1/100) > 1/1000 checked).

## h_cheb made explicit (new; proved modulo one cited classical bound)
Claim: S(k) ≥ k/100 for **every k ≥ 231** (k = 230 is the last failure).
- k ≤ 2,000,000: computed exactly (sieve, `check_h3.py` part C). Last failure k = 230; for
  231 ≤ k ≤ 2·10⁶ the minimum of S(k)/k is 0.01321.
- k > 2·10⁶ (in fact k ≥ ~954,200 suffices): Rosser–Schoenfeld 1962 (Illinois J. Math. 6, (3.14)
  θ(x) < x(1+1/(2 log x)) for x>1, (3.16) θ(x) > x(1−1/(2 log x)) for x ≥ 563) — **cited from
  memory, not re-checked against the paper**. S(k) = θ((11k−1)/20) − θ(k/2) ≥
  a(1−1/(2 ln a)) − b(1+1/(2 ln b)) with a=(11k−1)/20, b=k/2; divided by k this is
  ≈ 0.05 − 0.275/ln a − 0.25/ln b, increasing in k, and ≥ 1/100 from k ≈ 954,200 on (script).
So node h3--h3--h1 is true with K₃ = 230, and needs only R–S, not the full PNT
(h3--h3--h1--h1 and its Wiener–Ikehara subtree become unnecessary if R–S is accepted as a citation).

## Computational checks of the branch
- **Node claim, k ≤ 300** (all n, 2k ≤ n < k², exact Kummer): exactly the 13 pairs, last (284,28) —
  agrees with the existing numerical annex (k ≤ 1000). So K = 28 works in range.
- **h_gr shape**: for k ≤ 700 there ARE failures for every C tried (1..16), last at k = 652
  (~0.65–0.75M failing (n,k)). So h_gr's K₂ is at least 652 for these C — expected (the interval
  (k/2,11k/20) holds few primes for small k), and harmless: the node claim itself has no exception
  there because other primes ≤ k carry. Extended (C = 16, every k in 650..1000, then every 7th k
  to 4000; `output_hgr_ext.txt`): no failure after k = 652 (last: n = 186683). Consistent with
  h_gr holding with K₂ = 652 for C ≤ 16, but k > 1000 was only sampled.
  This is evidence about how large GR's ineffective K₂ is, not a proof of h_gr.
- Lemma L: brute force, 0 violations.

## Still open
- h_els (ELS 1993) and Lemma 5.1 / (5.1) (Sander's equidistribution over primes) are cited, not
  proved or re-read; neither has explicit constants, so K is ineffective along this route.
- I did not fetch the GR paper; the attribution rests on the existing annex.
- R–S constants above should be checked against the paper before the h_cheb shortcut is recorded.
