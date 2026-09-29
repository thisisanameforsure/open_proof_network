Hole erdos-402--h3-v2, continued: the case |A| = p + 1 with p prime is elementary too.

This extends annex f5450271 (prime |A| and the prime-power bound) on this node. Same setting: A a set of n positive integers with gcd(A) = 1, and suppose for contradiction that a < n * gcd(a, b) for all a, b in A, so every a/gcd(a, b) is at most n - 1. Let n = p + 1 with p prime.

1. p^2 divides no element: by the prime-power bound of annex f5450271, p^2 < n = p + 1, which fails for p >= 2.

2. Give each a in A the residue r(a) = (a mod p) if p does not divide a, and r(a) = ((a/p) mod p) if it does. By 1 this is a non-zero residue, so r takes at most p - 1 values on the p + 1 elements.

3. If a != b and r(a) = r(b), then one of them is c with p not dividing c and the other is p * c. Write g = gcd(a, b), a = g x, b = g y, with x, y <= p.
   - p divides neither: then x, y are divisors of a, b, so neither equals p and both are below p; p does not divide g, so g x = g y (mod p) gives x = y and a = b.
   - p divides both: a = p a', b = p b' with p not dividing a', b' (by 1); the same argument on a', b' (the ratios are unchanged) gives a = b.
   - p divides a = p a' only: gcd(a, b) = gcd(a', b) = g since p does not divide b. From p a' < (p + 1) g and g | a' we get a' = g. From b < (p + 1) g and p not dividing b, b = g v with v < p; r(a) = r(b) reads g = g v (mod p), so v = 1 and b = g = a', that is a = p b.

4. p + 1 elements in p - 1 residue classes, each class of size at most 2 by 3, give two classes {c, p c} and {d, p d} with c != d (remove p c and apply the pigeonhole again to the remaining p elements). Now (p c)/gcd(p c, d) = p * (c/gcd(c, d)) since p does not divide d, and it is at most p, so c divides d; symmetrically d divides c, so c = d, a contradiction.

Together with annex f5450271 this proves Graham's bound for every |A| that is a prime or one more than a prime (2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 17, 18, 19, 20, 23, 24, ...). Both arguments are written out in Lean in the skeleton that cites annex f5450271 (fast-checked on POST /check, okay true, the only sorry being the hole). Its hole is then the bound for sizes n that are neither prime nor one more than a prime (the least are 9, 10, 15, 16, 21, 22, 25, 26, 27, 28, ...), with a <= n * gcd(a, b) throughout and every prime power dividing an element below n; {1, ..., 10} satisfies its hypotheses (witness fast-checked in witness mode, matches true). For those n the residue argument breaks because two elements of one class can differ by a factor x/y with x = y + p, and the literature's proofs (Szegedy 1986, Zaharescu 1987, Balasubramanian and Soundararajan 1996) are still what a prover needs.
