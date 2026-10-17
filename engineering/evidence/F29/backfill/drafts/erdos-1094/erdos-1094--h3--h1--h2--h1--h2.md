---
label: "Residue form, k and n odd, 3 | k, 5 ∤ k, no carry at 5"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_2\ \forall n,k\in\mathbb{N}:\quad K_2<k,\ \ 2k\le n<k^2,\ \ k \text{ odd},\ \ n \text{ odd},\ \ 3\mid k,\ \ 5\nmid k,\ \ k \bmod 5 \le n \bmod 5 \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

For all large odd $k$ divisible by $3$ but not by $5$, every odd $n$ with $2k\le n<k^2$ whose residue mod $5$ is at least that of $k$ (so $p=5$ itself gives no carry) has a prime $p\le k$ whose residue of $n$ is smaller than its residue of $k$. Lean writes oddness as `k % 2 = 1` and `n % 2 = 1`, $5\nmid k$ as `0 < k % 5`, and $k^2$ as `k * k`. `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$, a carry at the last base-$p$ digit when $k$ is subtracted from $n$ (hence $p \mid \binom{n}{k}$ by Kummer's theorem, though the statement names no binomial coefficient).
