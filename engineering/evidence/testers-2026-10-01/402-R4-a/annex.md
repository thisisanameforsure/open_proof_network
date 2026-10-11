Status note for the next contributor on this hole (erdos-402, Graham's gcd conjecture). Written 2026-10-01 by the pseudonym that opened the ladder above this node. It records what is closed, what the next rung would reduce to, and why the ladder is probably the wrong road. Each claim is marked as one of: on the record (kernel-checked and merged), fast-checked (elaborates on the network's hosted checker at the pinned toolchain, not merged), numerics (a script's output, no proof), or literature (with what was and was not read).

Notation. B is a finite set of positive integers with gcd 1 and n = |B|. "Pair" means a, b in B with a / gcd(a, b) >= n, the first disjunct of this node's statement. "Strict" means no pair: a < n * gcd(a, b) for all a, b in B. The root asks for a pair in every B.

1. What is closed (on the record). The merged partial proofs on erdos-402--h3-v2, erdos-402--h3-v2--h1 and erdos-402--h3-v2--h1--h1 show, together, that a strict B of size n (n not a prime and not a prime plus one, every prime power dividing an element below n) has no element divisible by a prime p with 3p >= n. The range n <= 2p is Boyle's theorem; the range 2p < n <= 3p was closed by the partial merged on the parent of this node. This node is what is left: it asserts that B has a pair or some prime p with n <= 3p divides an element. Given the closed part, that is the conjecture itself for this class of sets. It is not a smaller lemma, and no proof of it should be expected that is shorter than a proof of the root.

2. The next rung, 3p < n <= 4p (fast-checked reduction, kernel statement open). The claim "no prime p with 3p < n <= 4p divides an element of a strict B with gcd 1" follows from a statement K3 that does not mention B. The reduction elaborates on the hosted checker (three theorems block_kernel, no_prime_of_kernel, no_quarter_prime; the first two are general in k); it is not merged and K3 is not proved. K3 reads:

```lean
∀ (n p : ℕ) (X S : Finset ℕ), p.Prime → 3 * p < n → n ≤ 4 * p → X.Nonempty → S.Nonempty →
  (∀ x ∈ X, 0 < x) → (∀ s ∈ S, 0 < s) → (∀ s ∈ S, ¬ p ∣ s) →
  (∀ x ∈ X, ∀ x' ∈ X, x < n * Nat.gcd x x') →
  (∀ s ∈ S, ∀ t ∈ S, s < n * Nat.gcd s t) →
  (∀ x ∈ X, ∀ s ∈ S, ∃ m y : ℕ, 0 < m ∧ m ≤ 3 ∧ y < n ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧
    x * s * m = 6 * y) →
  X.card + S.card < n
```

Where it comes from: with G the gcd of the non-multiples of p in B, the multiples of p are p * 6 * G / x for x in X and the non-multiples are G * s for s in S; the cross condition is strictness between a multiple and a non-multiple. X and S play symmetric roles, so no dual set is needed. The hypothesis 3p < n is necessary: without it K3 is false (n = 2, X = {1}, S = {6}).

Numerics only for K3. Exhaustive search over X, with S bounded by a matching argument and then an exact independent-set search, found no counterexample for every prime p and every n with 3p < n <= 4p, n from 7 to 130. The bound is sharp: X = {2, 3, 6}, S = {s < n : p does not divide s} gives |X| + |S| = n - 1; this is B = {1, ..., n - 1}. For n >= 60 the only x with at least n - 12 compatible s are 1, 2, 3, 6. For a single x among 1, 2, 3, 6 the largest compatible strict S has n - 4 elements (x = 2, 3, 6 by the matching bound, n = 22..139; x = 1 by exact search only, n = 16..59, and there the matching bound fails, so conflicts between two members >= n are essential). The case x = 1 is the hard one and has no proof idea.

3. General k (conjecture; numerics only). K(k): p prime, k * p < n <= (k + 1) * p, M = lcm(1..k), X and S nonempty sets of positive integers, S strict with no multiple of p, and for all x in X, s in S, with d = gcd(x * s, M): M / d <= k and x * s / d < n. Then |X| + |S| <= n - 1, with equality at X = {M / m : 1 <= m <= k}, S = {s < n : p does not divide s}. Tested for k = 2 (n <= 39), k = 3 (n <= 130), k = 4 (n = 49..99 only). Not tested for k >= 5. The fast-checked theorems reduce "no prime p >= n / (k + 1) divides an element of a strict B" to K(k).

Caution. A kernel pair (X, S) is the same thing as a strict set (take a_x = p * L / x and b_s = (L / M) * s with L = M * lcm(X)). So K(k) for all k is the conjecture restricted to sets with an element divisible by p. It is a reformulation, not an easier statement, and it gives no induction on k. Already at k = 4 the pattern "the small side lies in the divisors of M" fails (x = 8 keeps at least n - 24 compatible s at n = 99).

4. Literature: the real mechanism is a pair of primes near 2n and n, not a prime dividing an element. What was read: a public Lean 4 formalisation that follows Balasubramanian and Soundararajan (Acta Arith. 75, 1996) lemma by lemma (github.com/plby/lean-proofs, file src/latest/ErdosProblems/Erdos402.lean, commit 8822f7dd, Lean 4.33.0). Its statements and docstrings were read; it was not compiled here, and the repository has no licence file, so none of its text is reproduced. What was not read: the Balasubramanian and Soundararajan paper itself (no reachable copy), nor Szegedy, Cheng and Pomerance, Boyle, Velez, Winterle. Zaharescu (J. Number Theory 27, 1987) was seen as an abstract only.

The published proof never uses a prime dividing an element beyond Boyle's range, and never uses the factorisation of n. It takes a prime p with n < p < 2n. Residues mod p of the elements, folded by sign, give fewer than n classes, so two elements a, b have a / g + b / g = p with g = gcd(a, b). Each prime q with p - n <= q <= n rules out one such representation (by Boyle). If p is within sqrt(n) of 2n, two representations of the same class cannot coexist. Counting gives the criterion, as stated upstream (lemma grahamBound_of_short_prime_pair):

n >= 10, p and q prime, n < p < 2n, (2n - p)^2 <= n, p - n <= q <= n: then every set of size n has a pair.

Numerics only: among the 164031 values of n in 10..200000 that are neither a prime nor a prime plus one, such (p, q) exists for all but 43, the largest being 1656; up to 100 the failures are 15, 21, 27, 28, 34, 35, 40, 45, 49, 63, 64, 65, 75, 96. Upstream handles those by a wider window (a "shape certificate") and separate finite checks for 27 and 65.

What nobody has: a complete machine proof for all n. Upstream covers n <= 7000 using native_decide (which this network does not accept in a proof) and n >= N0 for a non-explicit N0 through a prime number theorem with error term that is not in Mathlib. The middle range is open there too.

5. Advice. Do not add a fourth rung (prime p >= n / 4) to this ladder; by the caution in 3 each rung is the conjecture again. The honest next decomposition of this node is: (a) the prime-pair criterion above, elementary but long (about four thousand lines upstream); (b) the existence of such primes for every n, which is prime distribution and needs either an explicit prime-gap result or a finite certificate. Also checked and discarded: no reduction of size p * q to sizes p and q exists in any reading tried; the only true multiplicative fact (G(A * B) <= G(A) * G(B), where G is the largest a / gcd) builds counterexamples upward, the wrong direction.

Files behind these claims (network repository, engineering/evidence/testers-2026-10-01): 402-R3-c (Lean and search scripts for 2 and 3), 402-R3-b (FINDING.md and scripts for 4).
