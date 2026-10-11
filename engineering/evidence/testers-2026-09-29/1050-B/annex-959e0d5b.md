Audit and decomposition of the hole `integrality` (erdos-1050--h1-v2--h2), by t0929-1 (agent 1050-B), 2026-09-29.

**What the statement says.** Write c = 8/3, q = 2, z for the sum over j >= 0 of 1/(1 - c*2^(j+1)), and for n >= 1

```
W(n) = (n-2)! * prod_{k=1..n} (1 - c*2^k) * prod_{k=(n+1)/2..n} (1 - 2^k)      (n-2, (n+1)/2 in N)
E(n) = sum_{j>=0} -(1 - c*2^(2n+j))^(-1) * prod_{k=1..n-1} (1 - 2^(k-(n+j))) * (1 - c*2^(k+n+j))^(-1)
```

The node asks for integer sequences a, b with b(n)*z - a(n) = 9^n * W(n) * E(n) for every n >= 1. Since z is irrational (Borwein 1991), for each n there is at most one such integer pair, so the statement is not trivially satisfiable: it holds exactly when the right-hand side lies in Z*z + Z.

**Partial fractions (the residue step, Borwein's Lemma 1).** Put x = 2^m and f(x) = -(1 - c*2^n*x)^(-1) * prod_{k=1..n-1} (1 - 2^k/x) * (1 - c*2^k*x)^(-1). Then E(n) = sum_{m>=n} f(2^m), and the terms with 1 <= m <= n-1 vanish (the factor k = m is zero), so E(n) = sum_{m>=1} f(2^m). As a rational function of x, f has simple poles at x = 1/(c*2^k), k = 1..n, a pole of order n-1 at x = 0, and vanishes at infinity; in y = 1/x it is O(y^n) at y = 0. Hence

```
A(n,k)  = -prod_{t=1..n-1} (1 - c*2^(t+k)) / prod_{l in 1..n, l != k} (1 - 2^(l-k))
f(x)    = sum_{k=1..n} A(n,k) / (1 - c*2^k*x) + sum_{i=1..n-1} B(n,i) * x^(-i),
B(n,i)  = sum_{k=1..n} A(n,k) * (c*2^k)^(-i)
```

and summing over m >= 1 (sum_{m>=1} 1/(1 - c*2^(k+m)) = z - s(k) with s(k) = sum_{i=1..k} 1/(1 - c*2^i), and sum_{m>=1} 2^(-i*m) = 1/(2^i - 1)):

```
E(n) = beta0(n) * z - alpha0(n),
beta0(n)  = sum_{k=1..n} A(n,k),
alpha0(n) = sum_{k=1..n} A(n,k) * s(k) - sum_{i=1..n-1} B(n,i) / (2^i - 1).
```

**Integrality (Borwein's Lemmas 2 and 3).** The node then follows with b(n) = 9^n W(n) beta0(n) and a(n) = 9^n W(n) alpha0(n), provided both are integers.

**Numerical evidence (Python, exact rationals; not a Lean check).** For n = 1..12 the direct 1200-term sum of E(n) at 300 significant digits agrees with beta0(n)*z - alpha0(n) to better than 1e-237. For every n = 1..40, 9^n W(n) beta0(n) and 9^n W(n) alpha0(n) are integers (n = 1: b = -39, a = 9, both sides 7.8097916822...; n = 2: b = 315549, a = -135999); they stay integers even with the factor (n-2)! removed, so that factor is slack. So the node looks true, and its content is exactly the three facts above.

**Decomposition submitted as a partial proof on this node.** Three holes, each in its own branch so that none becomes a hypothesis of another: `residue` (E(n) = beta0(n)*z - alpha0(n) for n >= 1, written with the explicit finite sums above), `denominator_integral` (9^n W(n) beta0(n) is an integer for n >= 1) and `numerator_integral` (the same for alpha0). The assembly is one `linear_combination`. `residue` is analysis plus a partial-fraction identity for general n; the two integrality holes are statements about finite sums of rationals only, with no series. Prior art for all three is Trevor Morris's lean-gallery (Apache-2.0, commit efc72e14, LeanGallery/NumberTheory/Erdos1050: `Eterm_eq_pVal`, `Bden_cast` and `numerator_integrality`), which uses Borwein's q-binomial form beta0(n) = -p_n(c, q) rather than the partial-fraction coefficients; matching the two forms is the q-Lagrange identity (`qLag_thm` there).
