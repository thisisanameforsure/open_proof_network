# 402-R4-b finding: does a factorisation induction prove Graham's gcd conjecture? (erdos-402, 2026-10-01)

G(A) = max over a, b in A of a/gcd(a,b). Theorem (B–S 1996): |A| = n implies G(A) >= n.
Scripts `e1.py`, `e2.py`; outputs `e1.out`, `e2.out`. Nothing was submitted to the network. No Lean was written
(no step survived that is both new and useful; see "What is true" for two small provable facts).

## Verdict (plain words)
**No, in both readings, and for the same reason.**

- **Reading 1, factorise n (the step S: sizes m and k give size mk).** No strengthened hypothesis I could
  state survives a computer search, and there is a structural reason: a set of size mk has no canonical
  "m-part" and "k-part". The only natural way to cut it (strip one prime p from every element, giving k
  distinct "p-free parts" and fibres of at most m powers of p) yields two bounds, G >= k and G >= p^(m-1),
  and they give only their **maximum**, never their product. Smallest example: **{1,2,3}** with p = 2 has
  k = 2, m = 2, and G = 3 < 4. Nothing in the proved prime case uses that n is a product; it uses that
  Z/n is a field.
- **Reading 2, factorise the numbers (induct on the primes dividing the elements, "taking in one more prime").**
  This is a real theorem in the squarefree case (Marica–Schönheim 1969) and it is the natural hope. It
  **does not extend to repeated prime factors**: the squarefree proof shows there are at least n *distinct*
  quotients, and that is false in general. Smallest example, found by exhaustive search and already in the
  1969 paper (Levin and Szemerédi): **{2,3,4,6,9,12,18}**, the non-trivial divisors of 36: 7 numbers, only 6
  distinct quotients {1,2,3,4,6,9}. (G = 9 >= 7, so Graham's bound holds; the counting argument is what dies.)
- **One-sentence reason.** Factorisation inductions need the quantity to multiply or add across the pieces,
  and G does neither: across a split the bounds combine as a maximum, and the one known inductive argument
  (counting distinct quotients) is false as soon as an exponent 2 appears.
- **Is (S) hopeless in principle?** Not proved impossible (S is a true statement). But 27 years of literature
  between the squarefree case (1969) and the full theorem (1996) found no such route, and the final proof uses
  primes near n and 2n, not the factors of n (see 402-R3-b). I would not spend more agent time on it.

## Evidence

### 1. Candidates for a strengthened hypothesis H(n)
| Candidate | Status | Smallest counterexample / note |
|---|---|---|
| (a) weighted: weights s_c >= 1 on a set C, max s_c * c/gcd(c,d) >= sum of s_c | **false** (by hand) | C = {1,2}, s = (5,1): max(5,2) = 5 < 6 |
| (a') weight 2^(s_c - 1) (fibres of powers of 2 without coprimality) | **false** (by hand) | C = {1,2}, s = (2,1): 2 < 3. The true version needs p coprime to C, and then it *is* Graham for the set, not a stronger H |
| (b) multisets | **false** trivially | {1,1}: G = 1 < 2 |
| (c) fibre form "G >= k*m" (k distinct p-free parts, largest fibre m) | **false** (exhaustive, [1..16], n <= 6, p = 2, 3) | {1,2,3}, p = 2: G = 3, k*m = 4. Also {1,2,3,4}: 4 < 6 |
| (c') what the two branches do give: G >= max(k, p^(m-1)) | **true**, asserted on every set in the same search; proof below | too weak: n <= k*m, and max(k, p^(m-1)) < k*m is common |
| (c'') bipartite form for two layers X, Y: some cross pair has quotient >= max(|X|,|Y|) | **false** (by hand) | X = {1,2,4}, Y = {2}: cross quotients are 1 and 2 |
| (d)/(e) counting form: at least n distinct quotients (multiset Marica–Schönheim, exponent vectors in N^r with truncated subtraction) | **false** (exhaustive in [1..20] for n = 7, in [1..19] for n = 8; exhaustive in the 3x3, 4x3, 4x4 grids) | {2,3,4,6,9,12,18}: 6 quotients for 7 elements. Grid 4x4: a 10-set with 8. True for n <= 6 in the ranges searched, and in the grids 2x2x2 and 3x2x2 with at most one exponent 2 |
| (e') lattice form: at least n distinct values gcd(a, L/b), L = lcm(A) | **true** (exhaustive n <= 7 in range; and a theorem, see below) | but a/gcd(a,b) only *divides* gcd(a, L/b), so it bounds the wrong quantity from the wrong side |

### 2. Why the fibre/pigeonhole step (c) cannot multiply
Write a = p^e * c with p not dividing c. For a = p^e c, b = p^f d the quotient is
p^max(e-f,0) * c/gcd(c,d). So:
- G(A) >= G(set of p-free parts) (*proved*, one line: the quotient is a multiple of c/gcd(c,d)); with H(k) this gives G >= k.
- a fibre with m elements gives G >= p^(m-1) (*proved*, trivially).
- To multiply you need a pair where c/gcd(c,d) is large **and** e > f. The good pair from H(k) may have
  e <= f, and then the p-part contributes nothing. When all fibres are full ({0..m-1} for every c) the
  bounds do multiply; staggered fibres are the obstruction, and handling them needs a statement about two
  different layers X, Y at once, which is false in every simple form (c'') and in its true form is just
  Graham's conjecture with one more prime. Adding a **large** new prime is trivial (any two layers give a
  quotient >= p); all the difficulty sits in the small primes, i.e. exactly where exponents are > 1.

### 3. What the prime case uses, and where n = pq breaks
Prime n = p: if every quotient is < p, then a -> (p-free part of a) mod p is injective into the p-1 nonzero
classes (two elements in one class have quotients congruent mod p and both < p, hence equal, hence the
elements differ by a power of p, a quotient >= p). So n <= p - 1.
For n = pq the Chinese-remainder analogue strips both primes and maps into the units mod pq
((p-1)(q-1) classes). A collision still forces equal {p,q}-free parts, but now a fibre is a set of numbers
p^e q^f with all quotients < pq, and such a fibre can be large: for n = 6 the fibre **{1,2,3,4}** is legal
(largest quotient 4 < 6). The count gives only n <= phi(6) * 4 = 8, not n <= 5. Explicit set where the
argument sees nothing: **{1,2,3,4,5,10,15,20}** (two classes, each fibre {1,2,3,4}); its large quotients
(10/gcd(10,3) = 10) are between classes, where residues mod 6 say nothing because quotients such as
2, 3, 4 are not units. Computed (fibres containing 1; a lower bound on fibre size): n = 10: 4*5 = 20;
n = 15: 8*4 = 32; n = 14: 6*5 = 30; n = 21: 12*4 = 48; n = 35: 24*4 = 96. The loss grows with n.

### 4. Reading (e): the squarefree induction and what is known
- Marica–Schönheim, "Differences of sets and a problem of Graham", Canad. Math. Bull. 12 (1969): for a
  finite family F of sets, the number of distinct differences A \ B is at least |F|. Proof by induction
  (minimal counterexample on the size of the family). Squarefree integers are sets of primes and
  a/gcd(a,b) is the set difference, so there are n distinct positive quotients and the largest is >= n.
  (*Read via a summariser of the Cambridge PDF; the quoted sentence about the counterexample is from it.*)
- The same paper records that "n distinct ratios" is **not true in general**, "as shown by a counterexample
  of Levin and Szemeredy; namely, the set of all non trivial divisors of 36". My exhaustive search found
  the same set independently as the smallest failure (no failure with n <= 6 in [1..22]).
- The modern proof of Marica–Schönheim is the Ahlswede–Daykin four-functions theorem, which *does* hold
  in any distributive lattice, including divisors of N with repeated primes, and is proved by induction
  over the ground set. Applied to A and {L/a}, it gives candidate (e'): at least n distinct values of
  gcd(a, L/b) (*derivation mine, standard; checked numerically, not in Lean*). In the squarefree case
  gcd(a, L/b) = a/gcd(a,b); with exponents it is min(alpha, e - beta) against max(alpha - beta, 0), a
  different and larger number. So the induction over primes extends, but to a statement that is not Graham's.
- Not established by me: whether anyone has published a "repaired" counting statement between the two.
  My searches (Daykin–Lovász, multiset Marica–Schönheim) returned nothing relevant; treat as *unknown*, not
  as *nonexistent*.

### What is true (provable, small, probably not worth a node)
1. G(A) >= G(p-free parts of A) for every prime p (so "stripping primes never raises G").
2. At least n distinct values of gcd(a, lcm(A)/b) (four-functions theorem; Mathlib has it for distributive
   lattices, but the divisibility lattice on naturals would need wiring).
Neither moves the root of erdos-402.

### Tested vs proved vs guessed
- Tested by computer: rows (c), (c'), (d)/(e), (e') and the fibre sizes in section 3, in the stated ranges only.
- Proved (by hand, short): (c') and "What is true" 1; counterexamples are checked arithmetic.
- Guessed: that no cleverer H(n) exists. The evidence is the failures above plus the literature's route.

Sources: Marica–Schönheim PDF (cambridge.org, S0008439500054138); 402-R3-b/FINDING.md for the B–S chain.
