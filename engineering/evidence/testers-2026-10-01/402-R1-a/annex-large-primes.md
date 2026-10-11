Large primes cannot divide an element of a strict counterexample (erdos-402--h3-v2--h1).

Setting. B is a set of n positive integers with gcd 1, and a ≤ n·gcd(a, b) for all a, b in B (the node's hypotheses). Suppose the conclusion fails; then every quotient is strictly small: a < n·gcd(a, b) for all a, b in B (if a = n·gcd(a, b) the pair (a, b) answers).

Claim. Under the strict inequality, no prime p with n ≤ 2p divides any element of B.

Proof. Let p be such a prime and suppose p divides some element. By the node's prime-power hypothesis p < n. Let B_p be the elements divisible by p and C the others; C is nonempty because gcd(B) = 1.

Step 1. For a in B_p and b in C, a = p·gcd(a, b). Indeed a / gcd(a, b) is a multiple of p (p does not divide gcd(a, b), which divides b), it is positive and below n ≤ 2p, so it is p.

Step 2. Hence for a in B_p the number d_a = a / p equals gcd(a, b) for every b in C, so d_a divides G = gcd(C). Write G = d_a·e_a and b = G·s_b. Then e_a = G·p / a, the map a ↦ e_a is injective on B_p, the map b ↦ s_b is injective on C, and b = gcd(a, b)·e_a·s_b. The strict inequality for the pair (b, a) gives e_a·s_b < n; also e_a·s_b > 0, and p does not divide e_a·s_b because it does not divide b.

Step 3 (counting). Let X = {e_a} and T = {s_b}, with u = |X| = |B_p| ≥ 1, v = |T| = |C| ≥ 1, u + v = n. A set of u distinct positive integers has an element ≥ u, so some x0 ≥ u and t0 ≥ v, and u·v ≤ x0·t0 < n = u + v. So u = 1 or v = 1. If u = 1, the n − 1 numbers x0·t (t in T) are distinct, lie in {1, …, n − 1} and avoid p, which lies in that range: n − 1 ≤ n − 2, absurd. If v = 1, the same with the n − 1 numbers x·t0. ∎

Remarks. (i) The hypothesis n ≤ 2p is used only in Step 1. (ii) In the extremal sets {1, …, n} and {L/1, …, L/n} (L = lcm(1..n)) a prime p in (n/2, n] divides exactly one element, respectively all but one; these are the cases u = 1 and v = 1, which survive only because there a quotient equals n. (iii) Bertrand's postulate gives a prime p with n/2 ≤ p < n for n ≥ 4, so the extremal sets always contain such a multiple: the remaining statement (the hole of the skeleton) is that B has a pair with a = n·gcd(a, b) or an element with a prime factor ≥ n/2. What is left to prove is therefore: a set of n ≥ 2 positive integers, gcd 1, all of whose prime factors are below n/2, has a quotient a / gcd(a, b) ≥ n. (iv) The next step in the same direction is primes in [n/3, n/2): there a / gcd(a, b) is p or 2p for a in B_p, b in C, and the two-block counting above becomes a three-way one. This is the direction of Szegedy's and Zaharescu's proofs for large n; it is not carried out here.

The skeleton submitted with this annex proves the Claim in Lean inside the assembly and leaves the single hole described in (iii), stated as a disjunction so that it keeps the parent's hypotheses (and its witness B = {1, …, 10}).
