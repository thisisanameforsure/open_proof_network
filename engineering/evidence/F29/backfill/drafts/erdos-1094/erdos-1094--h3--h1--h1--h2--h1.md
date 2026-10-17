---
label: "Residue form, k even, 3 ∤ k, no carry at 3 to 13"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_3\ \forall n,k\in\mathbb{N}:\quad K_3<k,\ \ 2k\le n<k^2,\ \ 2\mid k,\ \ 3\nmid k,\ \ k \bmod q \le n \bmod q\ (q=3,5,7,11,13) \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

For all large even $k$ not divisible by $3$, every $n$ with $2k\le n<k^2$ whose residue mod $q$ is at least that of $k$ for each of $q=3,5,7,11,13$ (so none of those five primes gives a carry) has a prime $p\le k$ whose residue of $n$ is smaller than its residue of $k$. Lean writes $3\nmid k$ as `0 < k % 3`, the five no-carry hypotheses as `k % q ≤ n % q`, and $k^2$ as `k * k`. `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$, a carry at the last base-$p$ digit when $k$ is subtracted from $n$ (hence $p \mid \binom{n}{k}$ by Kummer's theorem, though the statement names no binomial coefficient).
