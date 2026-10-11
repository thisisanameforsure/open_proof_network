# 402-R3-b finding: literature, and "reduce pq to p and q" (erdos-402, 2026-10-01)

## Verdict
- **B (owner's idea): no.** No reading of "if it cannot fail for p and q, it cannot fail for pq" gives a
  reduction. The only true multiplicative fact runs the other way (counterexamples at m and k multiply to one
  at mk), and the factorisation of n plays no role in any proof I could read. Nothing to hand to 402-R3-a in
  Lean from this side.
- **A (literature): the real chain is now in hand, and it changes the plan.** I could not open the
  Balasubramanian–Soundararajan (B–S) PDF, but a public Lean 4 formalisation that follows it lemma by lemma is
  readable (github.com/plby/lean-proofs, `src/latest/ErdosProblems/Erdos402.lean`, 8069 lines, Lean 4.33.0,
  commit 8822f7dd; copy saved as `upstream-plby-Erdos402.lean.txt`). The proof does **not** use primes
  dividing elements beyond Boyle's range, and it does not use the factors of n. It uses a prime **p just
  below 2n** and a prime **q just below n**. One elementary criterion closes almost every open n:

  > n ≥ 10, primes p, q with n < p < 2n, (2n − p)² ≤ n, p − n ≤ q ≤ n  ⟹  Graham holds for every set of size n.

  My own script (`cert.py`) finds such a pair for all but 43 of the 164,031 open n (not prime, not prime+1)
  in 10..200000; the last failure is n = 1656.
- **What nobody has:** a complete machine proof for all n. Upstream proves n ≤ 7000 (with `native_decide`,
  which this network forbids) and n ≥ N₀ for a **non-explicit** N₀ (through `PrimeNumberTheoremAnd.MediumPNT`,
  not in Mathlib). 7001..N₀ is open upstream too.

## A. What I could and could not read
| Source | Status |
|---|---|
| B–S, Acta Arith. 75 (1996) 1–38 | **Not read.** matwbn.icm.edu.pl is off the sandbox allowlist; pldml and impan pages refused. EuDML record (eudml.org/doc/206861) read: metadata and reference list only. |
| Lean formalisation of B–S (plby/lean-proofs) | **Read** (cloned). Everything below marked "upstream" is from its statements and docstrings, which cite B–S lemma numbers. I did not compile it. No licence file in the repo. |
| Zaharescu, JNT 27 (1987) | Abstract page only. Prop. 1: Graham holds for every n with 2n − p(n) < √n, p(n) the largest prime below 2n. Prop. 2: all large n, by Huxley's prime-gap theorem. |
| Ford, "A strong form of a problem of R. L. Graham" (Canad. Math. Bull.) | Read through a summariser. Uses primes p in (1.5N, 2N − √N) and the counts r_p(m); says B–S reach all n with explicit prime-counting bounds. |
| arXiv 2005.04429 (Farey sequences) | Read. An equivalence with Farey subsets, no new proof. Its history: **Winterle = a prime among the a_i; Vélez = n = p+1; the n = p proof is Szemerédi's, printed in Vélez**; Boyle = a prime p > (n−1)/2 divides some a_i; Cheng–Pomerance = the equality case for n > 10^50000. (The assignment's "Winterle proved n prime" is not what this source says.) |
| Szegedy, Cheng–Pomerance, Winterle, Vélez, Boyle, Weinstein, Cobeli–Vâjâitu–Zaharescu | **Not read** (paywall pages or no reachable copy). Chein 1978 abstract only (prime element case). Marica–Schönheim: squarefree case (in Mathlib as `Nat.grahamConjecture_of_squarefree`). |
| B–S numeric threshold | **Unknown to me.** B–S cite Rosser–Schoenfeld and the large sieve (Montgomery–Vaughan) in their reference list; I did not see the number. |

### The lemma chain (upstream, B is a gcd-1 strict counterexample of size N)
1. Normalise (divide by gcd); dual set L/a; every element divides lcm(1..N−1). *Elementary; on our record.*
2. N prime: a ↦ (p-free part of a) mod p is injective into p − 1 classes. *Elementary.*
3. Boyle: no prime q with N ≤ 2q divides an element. *Elementary; on our record.*
4. **Lemma 2.1 (collision).** For a prime p, N < p < 2N: residues mod p, folded by ±, give fewer than N
   classes, so two elements have a/g + b/g = p. Counting: with J = [(p+1)/2, N] and r_p(α) = number of
   pairs with reduced quotients (α, p − α), Σ r_p ≥ |J|, so #{r_p = 0} ≤ Σ_{r_p ≥ 2} (r_p − 1). *Elementary.*
5. **Lemma 2.2.** Each prime q in [p − N, N] forces r_p(max(q, p−q)) = 0 (by Boyle). *Elementary.*
6. **Lemma 2.3 / 3.1 / 3.3.** Two representations of the same α factor as a "rectangle"
   αd₁C, αd₂C, (p−α)d₁C, (p−α)d₂C; if 2N − p ≤ 2√N then r_p ≤ 2, and r_p(α) ≥ 2 forces
   p − α = ℓ·Y·(Y+1), ℓ ≤ j ≤ 3 where (2N−p)² ≤ (j+1)N. With j = 0 there are no collisions at all, which
   with 4–5 gives the boxed criterion. *Elementary, about 4,000 lines upstream.*
7. Finite table: the shape certificate settles 10 ≤ N ≤ 7000 except **27 and 65** (my script reproduces
   exactly these two), done by separate finite configuration checks; N ≤ 10 by enumeration.
8. **Sections 4–5 (large N).** Window p ∈ [2N − 2G, 2N − G]; Lemma 4.1: primes above a cube-root threshold
   miss every element except at most two exceptional ones; first-moment bounds on factor triples; lower bound
   on primes in the window. **Prime input:** ψ(x) = x + O(x·exp(−c (log x)^{1/10})) (MediumPNT), i.e. primes
   in intervals of length x/(log x)^k. Files `LargeSieve.lean`, `Ramanujan.lean`, `SieveDenominator.lean`
   sit beside it. Non-effective upstream.

## B. The owner's idea, reading by reading (G(A) = max a/gcd(a,b); scripts `numB.py`, output `numB.out`)
- **(i) Project a size-pq set onto size p or q.** Subset form: "G(A) ≥ m_p(A)·m_q(A)", m_k = least G over
  k-subsets (it would give pq from the prime case). **False:** A = {1,3,4,5}: G = 5, m_2 = 3, 3·3 = 9.
  132 of 495 four-subsets of [1,12] violate it; also false for (2,3) and (3,3), e.g.
  {1,3,4,5,6,7}: G = 7 < 2·4. Residue form (classes of the p-free part mod p): a class has ≥ q+1 elements
  but its G is far above its size (in {1..35}, p = 5: sizes 8–10, G 31–35), so nothing descends.
- **(ii) Products.** True: G(A·B) ≤ G(A)·G(B) (0 violations in 20,000 random trials; one-line proof:
  gcd(a,a′)·gcd(b,b′) divides gcd(ab,a′b′)). So counterexamples of sizes m and k with all products distinct
  give one of size mk. **True but the wrong direction**: it derives failure at mk from failure at m and k;
  the owner needs failure at pq to force failure at p or q. Sets do not factor: {1..n} is not A·B for any
  split I tried ((2,2),(2,3),(3,3),(2,5),(3,4)), and {1..m}·{1..k} has fewer than mk elements.
- **(iii) Induction on the number of prime factors.** Needs a step "Graham(m), Graham(k) ⟹ Graham(mk)".
  The natural steps are (i) (false) or a chaining rule "a/(a,b) ≥ m, b/(b,c) ≥ k ⟹ some quotient ≥ mk"
  (**false:** 2, 3, 1 gives m = 2, k = 3, largest quotient 3). No candidate step survived.
- **(iv) What the prime proof uses.** Quotients below p are units mod p, and Z/p is a field, so residues
  are injective into p − 1 classes. For n = pq or p^k quotients below n need not be units mod n
  (n = 6: 2, 3, 4), and mod p alone the classes are too big. The literature's actual generalisation
  replaces "n is prime" by "**a prime p between n and 2n**": residues mod that p are still injective, and
  the count is rescued by folding ± (step 4). So the arithmetic of n is irrelevant; the primes near n and
  2n are what matter.

## What I would do next (for the owner and 402-R3-a)
1. Stop climbing the ladder "prime p ≥ n/k divides an element" (k = 3, 4, …). The literature never goes there.
2. The honest next hole is the pair criterion: "good pair ∨ ¬∃ primes p, q with n < p < 2n, (2n−p)² ≤ n,
   p − n ≤ q ≤ n". Its proof is steps 4–6 at j = 0 (upstream: `exists_gcd_quotients_sum_prime`,
   `card_J_le_representationPairs`, `primeInterval_card_le_zeroFibers`, `collision_fiber_shape`,
   `grahamBound_of_short_prime_pair`). It is long (thousands of lines as inner `have`s is not realistic
   under the one-declaration heartbeat cap; this needs the network's "auxiliary lemma" feature, F2 of R2-b).
3. The residual hole after that ("no such prime pair") is true only through prime distribution; it cannot
   be closed for all n with Mathlib today. Decide whether the target is parked there or the network takes
   on an explicit prime-gap certificate.
4. Ask the upstream author about reuse (no licence file) before porting text; the pin differs by a patch
   release (4.33.0 vs our 4.33.1).
