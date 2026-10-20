# Granville–Ramaré (Mathematika 43 (1996) 73–107): outline for erdos-1094--h3

Author: H (t1015b-h). Source read: the authors' preprint, https://dms.umontreal.ca/~andrew/PDF/ramare.pdf
(45 pp; **page numbers below are the preprint's own page numbers**, not the journal's 73–107; the
journal pagination was not available to me). Text was OCR'd + checked against page images for every
formula quoted here.

## 0. Headline (read this first)

* The result about g(k) is **Theorem 8** (preprint p. 5), stated in the introduction:

  > **Theorem 8.** If the least prime factor of C(n,k) is > k then there exists an absolute constant
  > c > 0 such that n > exp( c (log³k / log log k)^{1/2} ).

  No "k ≥ k₀" is written; it is implicit (the constant is absolute; for small k the claim is
  vacuous or absorbed into c). **Variable shift**: the proof (p. 24–25, §5e) works with
  (n+1)(n+2)···(n+k)/k! = C(n+k, k), i.e. the paper's proof-`n` is our `n − k`. Harmless for h3
  (a bound n−k > X implies n > X).

* **The paper does not prove Theorem 8 from scratch.** Its proof (§5e, ~15 lines) has exactly three
  ingredients:
  1. **[ELS] (cited, not proved here):** if lpf C(n+k,k) > k then n ≫ k²/log k
     (Erdős–Lacampagne–Selfridge, "Estimates of the least prime factor of a binomial coefficient",
     Math. Comp. 61 (1993)). The paper says only "That n ≫ k²/log k has been proved in [ELS], so we
     may assume this." I have NOT read ELS; the exact constant / range is unverified.
  2. **An elementary last-digit lemma** (inline in §5e, p. 24–25; my label **E1** below).
  3. **(5.1)** (p. 18), an equidistribution bound for {x/p} over primes, **quoted from Sander [Sa2]**
     (J. reine angew. Math. 430), via Lemma 5.1. Deep (Vaughan identity / exponential sums over
     reciprocals of primes). Not proved in this paper either — the paper's own exponential-sum work
     (Thm 9, §§8–9) is for Theorems 1/1*, not Theorem 8.

* **What it implies.** exp(c(log³k/loglog k)^{1/2}) = k^{c (log k/loglog k)^{1/2}} > k² for k large,
  so Theorem 8 ⇒ **erdos-1094--h3** for all n (in particular 2k ≤ n < k²).
  More usefully, **the proof (not the statement) gives erdos-1094--h3--h1** on the range
  n ≥ C·k²/log k (our n): it exhibits a prime p ∈ (k/2, 11k/20) with a carry in the last base-p digit,
  i.e. `n % p < k % p` (see §2 below). For the lower range 2k ≤ n < C k²/log k the paper gives nothing
  of its own: it is [ELS]'s result, and whether ELS's argument yields a *last-digit* prime (the h3--h1
  form) rather than just "some prime ≤ k divides C(n,k)" (the h3 form) is unknown to me.
  **So: GR ⇒ h3 (via [ELS] + [Sa2]); GR's proof ⇒ h3--h1 only for n ≳ k²/log k; for the rest of
  h3--h1's range, [ELS] is needed and unread.**

## 1. Notation

* ψ(t) = 0 if t ∈ ℤ, else {t} − 1/2 (p. 13, §3a).
* Kummer: p | C(n,k) iff there is a carry when adding k and n−k in base p. The last digit has a carry
  iff (n−k) % p + k % p ≥ p iff **n % p < k % p**. (This is exactly h3--h1's sieve condition.)

## 2. The chain for Theorem 8 (p. 24–25, §5e), in our variables N = n (top), m = n − k

Assume lpf C(N,k) > k, N ≥ 2k, k large. Fix ε = 1/10.

**E1 (elementary; inline in §5e, p. 24–25).** For k ≥ 5 and every prime p with k/2 < p ≤ k:
if p ∤ C(N,k) (in particular if minFac C(N,k) > k) and N ≥ k, then
`(N − k) % p < 2p − k`  (equivalently `N % p ≥ k % p` — no last-digit carry, since k % p = k − p).
*Paper's proof:* p ∥ k! (as p ≤ k < 2p and p² > k), so p ∥ (m+1)···(m+k); hence exactly one multiple
of p lies in (m, m+k], so p(⌊m/p⌋+2) > m+k, giving p{m/p} < 2p − k.
Uses: nothing. **Elementary** (Lean: descFactorial = choose·k!, two distinct multiples ⇒ p² | product,
padicValNat of k! = 1). Note this is the **contrapositive of the last-digit sieve for these p**:
"N % p < k % p ⇒ p | C(N,k)".

**E1′ (elementary corollary, p. 25).** If moreover p < (k/2)(1+ε), then 0 ≤ {m/p} < εk/p < 2ε = 1/5,
hence ψ(m/p) < 1/5 − 1/2 = −3/10, so
`|Σ_{k/2<p<(k/2)(1+ε)} ψ(m/p) log p| ≥ (3/10) Σ_{k/2<p<(k/2)(1+ε)} log p ≫ k` (last step: PNT /
Chebyshev in short intervals (k/2, 0.55k) — **medium**: needs ϑ(1.1x) − ϑ(x) ≫ x; Mathlib has
Bertrand but not this with explicit constant; a Chebyshev-type estimate would do).

**(5.1) (DEEP, cited from Sander [Sa2] via Lemma 5.1, p. 18).** Lemma 5.1: fix ε>0, J ≥ 1; there is
c>0 such that for y ≤ x^{1/J} the number of primes p ≤ y with {x/p^j} < σ_j (j = 1..J) is
σ₁···σ_J π(y) + O((y^{1−c(log y/log x)²} + y^{J/2+1+ε} x^{−1/2})(log x)^{4J}).
Partial summation (J=1):
`|Σ_{p<y} ψ(x/p) log p| ≪ (y^{1−c(log y/log x)²} + y^{3/2+ε} x^{−1/2}) log⁵x`.

**Conclusion (p. 25).** Apply (5.1) with x = m, y = k/2 and y = (k/2)(1+ε) and subtract: the RHS is
o(k) when (i) y^{3/2+ε}x^{−1/2}log⁵x = o(k), which holds once m ≫ k²/log k [this is where ELS is
used], and (ii) k^{−c(log k/log m)²} log⁵ m = o(1), which holds while
log m ≤ c′ (log³k / log log k)^{1/2}. Contradiction with E1′ ⇒ Theorem 8.

## 3. Proposed skeleton shape (for G) and difficulty

Two honest options; both cite the paper for what it proves and cite ELS/Sander for what it quotes.

**Option A (under h3--h1, the sieve form; preferred — the paper's proof *is* a last-digit sieve):**
- hole A1 (DEEP, GR §5e + [Sa2] (5.1)): ∃ C K, ∀ n k, K < k → C·k² ≤ n·(log k) [or a rational
  surrogate, e.g. k*k ≤ C * n * Nat.log 2 k] → n < k*k → ∃ prime p, k < 2p ∧ 10p < 11k/2·… ∧ n % p < k % p.
  (Simplest Lean form: `∃ p, Nat.Prime p ∧ p ≤ k ∧ n % p < k % p` with the range hypothesis.)
- hole A2 ([ELS], DEEP-ish / UNREAD): the small range 2k ≤ n < C k²/log k. **Warning:** I cannot
  say ELS proves this in *sieve* form. If G wants only what is certain, put A2 in h3 form
  (minFac ≤ k) under h3, not under h3--h1.

**Option B (directly under h3, mirrors the paper's logic exactly):**
- hole B1 = [ELS]: ∃ C K, ∀ n k, K < k → 2k ≤ n → minFac C(n,k) > k → k*k ≤ C * n * (Nat.log 2 k + 1).
  (cited, unread; "≫" constant unknown — keep it existential.)
- hole B2 = (5.1)-consequence (DEEP, Sander): for k large and C k²/log k ≤ n < k², NOT all primes p in
  (k/2, 11k/20) satisfy (n−k) % p < 2p − k. (Pure statement about residues; no binomials.)
- E1 proved inline in the assembly or as a separate elementary lemma (I will prove it).
- Assembly: from B1 get n large; from E1 every such p has small residue; B2 contradicts.

Ratings: E1 **elementary** (I can do it today). E1′'s "≫ k" sum of log p over (k/2, 0.55k): **medium**
(not needed if B2 is phrased over residues directly). B1/A2 ([ELS]): **deep / unread**.
B2/A1 ((5.1)): **deep** (exponential sums over 1/p; Sander 1992 / Jutila 1974). Neither is an
"hour in Lean" item.

**Strength check:** the paper never claims anything about n < k²/log k itself; any hole covering that
range must cite ELS. B2 is weaker than (5.1) (only needs failure of the all-small-residue pattern) — OK.
Do not state a hole with explicit constants (the paper's c, and ELS's ≫, are ineffective as written).

## 4. [ELS] checked (12:55Z) — secondary source only

The AMS PDF of Erdős–Lacampagne–Selfridge, Math. Comp. 61 (1993) 215–224 (doi 10.1090/S0025-5718-1993-1199990-6)
is behind a bot check from here; I could not read it. The Zentralblatt review (Zbl 0787.11008, mirrored at
emis.muni.cz/classics/Erdos/cit/78111008.htm) confirms: with g(k) = least N > k+1 such that C(N,k) has least
prime factor > k (N = the TOP of the binomial, i.e. our n), they prove **g(k) > c k²/ln k** with an unspecified
constant c. So `h_els` in the form "∃ C K, ∀ n k, K < k → 2k ≤ n → minFac C(n,k) > k → k² ≤ C·n·log k" is what
ELS state (GR p.24 quotes it in the shifted variable as n ≫ k²/log k; same thing up to the constant since
n−k ≥ n/2). Nat.log 2 k vs ln k only changes C. ELS's own proof method: unread.

## 5. Status of the second level (12:58Z)

G's draft `G/skeleton-h_gr-draft.lean` splits h_gr into h_cheb (k/100 ≤ Σ_{p prime, k<2p, 20p<11k} log p) and
h_sander ((5.1) on (k/2,11k/20) at x = n, with fract−1/2 for ψ), and proves the step "no carry ⇒ fract(n/p) ≥ 9/11"
in the assembly. Reviewed: faithful (x = n vs GR's x = n−k is harmless: (5.1) is uniform in x).
**h_cheb is not elementary in Mathlib**: Mathlib has `Chebyshev.theta_ge` (θ(n) ≥ n log 2 − log(n+1) − 2√n log n)
and `Chebyshev.theta_le_log4_mul_x` (θ(x) ≤ x log 4); their ratio is 2, so they cannot see primes in a window
(x, 1.1x]. It needs the PNT (not in Mathlib) or explicit Rosser–Schoenfeld bounds. GR use it silently ("≫ k").
My equivalent draft (x = n−k) is `H/h_gr-partial-draft.lean`, superseded by G's.

## 6. [ELS] read after all (13:25Z; G found it through a Wayback `id_` URL)

ELS Theorem 1 (p. 216): g(k) > c₁k²/ln k. ELS write N = n + k for the top (= our n). The proof has three ranges:
- N ≤ k^{1+c}: **cited** from Ecklund–Erdős–Selfridge [1] (Math. Comp. 28, 1974): g(k) > k^{1+c}.
- k^{7/4} < N < c₁k²/ln k (pp. 216–217, (1)–(4)): Ingham (cited) gives > k^{3/4}/(c₂ ln k) primes in (k/2, k/2 + k^{3/4}),
  so by averaging two of them, p₁ < p₂ < p₁ + c₂ ln k. One of the two has two multiples in (N−k, N], so it divides C(N,k).
- k^{1+c} < N < k^{7/4} (p. 217): count the "unusable" primes in (k/2, k/2 + k^{7/8}), at most about k^{3/4}, against
  Ingham's > k^{7/8}/(c ln k).
These became PR #543 (holes h_ees, h_caseB, h_caseA). The next level would be: Ingham's short-interval prime count
(deep, cited) plus the elementary counting in each case (medium).
