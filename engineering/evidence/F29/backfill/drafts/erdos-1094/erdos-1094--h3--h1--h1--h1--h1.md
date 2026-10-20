---
label: "Residue form, k even, 15 | k"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_1\ \forall n,k\in\mathbb{N}:\quad K_1<k,\ \ 2k\le n<k^2,\ \ 2\mid k,\ \ 3\mid k,\ \ 5\mid k \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

For all large $k$ divisible by $2$, $3$ and $5$, every $n$ with $2k\le n<k^2$ has a prime $p\le k$ whose residue of $n$ is smaller than its residue of $k$. Lean writes $k^2$ as `k * k` and the divisibilities as `k % 2 = 0`, `k % 3 = 0`, `k % 5 = 0`. `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$, a carry at the last base-$p$ digit when $k$ is subtracted from $n$ (hence $p \mid \binom{n}{k}$ by Kummer's theorem, though the statement names no binomial coefficient).
