# Notes toward the next lemma (not on the record, not machine-checked)

Notation: strict counterexample B, n = |B|, gcd(B) = 1, a < n·gcd(a,b) for all pairs. p prime dividing some element,
B_p = multiples of p (u of them), C = the rest (v of them), G = gcd(C), b = G·s_b.

Proved in Lean (PR #331 assembly): n ≤ 2p is impossible. Method: a = p·gcd(a,b) for a ∈ B_p, b ∈ C; e_a = G·p/a;
e_a·s_b < n; u·v ≤ max e · max s < u + v; so u = 1 or v = 1; then n − 1 distinct values in [1, n−1] \ {p}.

General form of the same counting (pen and paper). Let k = ⌈n/p⌉ − 1 and suppose p² ≥ n (so p ∥ a). For a ∈ B_p, b ∈ C,
a/gcd(a,b) = p·m with 1 ≤ m ≤ k. With A = a/p: A/gcd(A,b) = m divides M = lcm(1..k), so A | M·G. Put e_a = M·G·p/a
(distinct positive integers). Then b/gcd(a,b) = s_b·e_a·m/M < n, so e_a·s_b < n·M, and u·v < M·(u + v):
min(u, v) < 2M. So for every prime p ≥ √n dividing an element, either fewer than 2·lcm(1..k) elements are multiples
of p, or fewer than 2·lcm(1..k) are not. (This "few or almost all" dichotomy is the shape of Szegedy's / Zaharescu's
structure lemma; in {1..n} it is "few", in the dual set "almost all".)

Case k = 2 (n/3 ≤ p < n/2), worked further. M = 2, e_a = 2pG/a, e_a·s_b < 2n, (u−2)(v−2) < 4, so u ≤ 2 or v ≤ 2 once n > 8.
Take u ≤ 2 (the other is the dual under a ↦ L/a). For a ∈ B_p with e = e_a:
 - e even: gcd(a,b) = a/p for all b, b/gcd = s·e/2 < n; v ≥ n − 2 distinct s < 2n/e not multiples of p forces e = 2 and
   s ∈ [1, n−1] \ {p, 2p}, only n − 3 values: contradiction.
 - e odd ≥ 3: s < 2n/3, fewer than n − 2 values for n > 6: contradiction.
 - so e = 1, u = 1, G = 1: B = {2p} ∪ T, |T| = n − 1, T ⊆ {odd t < n} ∪ {even t < 2n}, no multiple of p, T itself strict.
   T must contain at least two even numbers 2w with n/2 ≤ w < n, and every odd t ∈ T shares an odd factor ≥ 3 with
   every such w. This does NOT close by counting alone; it needs the same analysis at a second prime
   (another q in [n/3, n/2) gives 2q ∈ B as the only multiple of q, etc.). Open.

Dead end to avoid: a hole whose conclusion is False (or whose case hypothesis is impossible) can never be witnessed.
State each remaining case as a disjunct of the conclusion instead (as hsmooth does).
