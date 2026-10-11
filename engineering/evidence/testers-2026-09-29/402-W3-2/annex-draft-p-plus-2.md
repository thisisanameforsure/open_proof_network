# Graham's bound for |A| = p + 2 (p prime): a pen-and-paper proof

Draft by 402-W3-2 (pseudonym t0929-6), 2026-09-30. Not submitted, not formalised. Checked only as
stated at the end.

**Claim.** Let p be a prime and A a set of p + 2 positive integers. Then some a, b in A have
a / gcd(a, b) ≥ p + 2, i.e. gcd(a, b) ≤ a / |A|.

**Reformulation.** Suppose not: for all a, b in A the reduced fraction a/b = u/v has u, v ≤ p + 1.
Call such a pair *compatible*. Every p-adic valuation in A then lies in a window {m, m + 1} (a
reduced term is divisible by p at most once, since p² > p + 1). For x in A let class(x) be the
p-free part of x modulo p, a residue in 1..p−1; there are p − 1 classes.

**Lemma 1 (one class).** If x < y are compatible and in one class, then y/x is p + 1, p or
(p + 1)/p. *Proof.* Write y/x = u/v reduced. If p divides neither, u ≡ v (mod p) with u ≠ v and
u, v ≤ p + 1 forces {u, v} = {1, p + 1}. If p | u then u = p and v ≡ 1, so v ∈ {1, p + 1}; if p | v
likewise. ∎ Hence a class holds at most 3 elements: sorted x1 < x2 < x3 < x4 would need
{x2, x3, x4}/x1 = {(p+1)/p, p, p+1}, and then x3/x2 = p²/(p+1) is not allowed. The 3-element
classes are {g, g(p+1)/p, g(p+1)} and {g, gp, g(p+1)}; both contain a pair of ratio p + 1.

**Lemma 2 (two classes).** Call a compatible same-class pair of type P1 (ratio p + 1), P (ratio p)
or Q (ratio (p+1)/p). Two such pairs lying in *different* classes, with all four elements pairwise
compatible, must be one of type P and one of type Q. *Proof* (scale the first pair to {1, r}, the
other pair is {y, y·s}, y = u/v reduced, class(y) ≠ 1):
- r = p + 1. Compatibility of y with 1 and with p + 1 gives v ≤ gcd(u, p + 1) ≤ u (the cases u = p,
  v = p put y in class 1). s = p forces u = 1, so y = 1; s = p + 1 forces u ≤ gcd(p + 1, v) ≤ v, so
  u = v; s = (p+1)/p forces v | p + 1 and u ≤ v, so u = v. Each contradicts class(y) ≠ 1.
- r = p. Compatibility with 1 and p gives y ∈ {2, …, p−1} ∪ {p/v : 2 ≤ v ≤ p−1}. s = p and
  s = p + 1 take y·s outside that set; s = (p+1)/p is possible (y = p/v, v | p + 1).
- r = (p+1)/p, s = (p+1)/p. Scale to {p, p + 1} and {z, z(p+1)/p}, t = z/p = a/b. If a = p the
  numerator p² appears in z/(p+1); if b = p the denominator p² appears in z(p+1)/p². Otherwise
  compatibility forces a | p + 1, b | p + 1, b ≤ a and a ≤ b, so t = 1, in class 1. ∎
(Compatibility is symmetric, so the cases listed cover every unordered pair of types.)

**Counting.** If some class has 3 elements it contains a type-P1 pair, which by Lemma 2 shares A
with no other same-class pair, so every other class is a singleton: |A| ≤ 3 + (p − 2) = p + 1.
Otherwise each class has at most 2 elements, and the classes with 2 carry pairs of pairwise
different, P/Q-compatible types: at most two such classes, so |A| ≤ (p − 1) + 2 = p + 1. Either
way |A| ≤ p + 1 < p + 2. ∎

**What was checked.** Python, exact rationals (`pplus2_exhaustive.py`, output beside it): for every
prime p ≤ 47, the largest same-class clique through 1 has 3 elements and the only cross-class
coexisting pair types are (P, Q); an independent Bron–Kerbosch search (`pplus2_clique.py`) finds the
largest compatible set for p = 2, 3, 5, 7, 11, 13 to be exactly p + 1. The general argument above is
not machine-checked. (For p = 2 the argument goes through with one class.)

**Use on the record.** The hole that #289 leaves (erdos-402--h3-v2--h1, and after the cut-45 child
skeleton its |B| ≥ 45 hole) excludes |B| prime and prime + 1; this argument would also exclude
prime + 2 (45, 49, 55, 61, 63, 73, 75, 81, 85, … among the sizes ≥ 45), and it does not use the
hole's extra hypotheses. A formal version needs the class map and Lemma 2's case analysis in one
declaration (helper declarations are refused), which is a real Lean project, not a certificate.
