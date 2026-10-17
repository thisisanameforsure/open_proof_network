---
label: "Residue form, k even, every prime ≤ k dividing n divides k"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\ \forall n,k\in\mathbb{N}:\quad K<k,\ \ 2k\le n<k^2,\ \ 2\mid k,\ \ \bigl(\forall q\le k \text{ prime},\ q\mid n \Rightarrow q\mid k\bigr) \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

For all large even $k$, every $n$ with $2k\le n<k^2$ such that each prime $q\le k$ dividing $n$ also divides $k$ has a prime $p\le k$ whose residue of $n$ is smaller than its residue of $k$. Lean writes $k^2$ as `k * k` and $2\mid k$ as `k % 2 = 0`. `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$, a carry at the last base-$p$ digit when $k$ is subtracted from $n$ (hence $p \mid \binom{n}{k}$ by Kummer's theorem, though the statement names no binomial coefficient).
