---
label: "2k ≤ n < k³ with n/gcd(n,k) free of primes ≤ k"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\in\mathbb{N}\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ 2k\le n<k^3,\ \ \operatorname{minFac}\tbinom{n}{k}>k,\ \ \operatorname{minFac}\!\Bigl(\frac{n}{\gcd(n,k)}\Bigr)>k\ \Longrightarrow\ k\le K$$

Only finitely many $k$ admit an $n$ with $2k\le n<k^3$ such that neither the binomial coefficient $\binom{n}{k}$ nor the cofactor $n/\gcd(n,k)$ has a prime factor at most $k$. Lean writes $k^3$ as `k * k * k`; `Nat.minFac` is the least prime factor (1 at 1, 2 at 0); $n/\gcd(n,k)$ is natural-number division, exact here since the gcd divides $n$.
