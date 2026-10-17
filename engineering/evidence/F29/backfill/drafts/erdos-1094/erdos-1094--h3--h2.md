---
label: "ELS lower bound: k² ≤ C·n·log₂k when lpf C(n,k) > k"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists C, K_1\in\mathbb{N}\ \forall n,k\in\mathbb{N}:\quad K_1<k,\ \ 2k\le n,\ \ \operatorname{minFac}\tbinom{n}{k}>k \implies k^2 \le C\cdot n\cdot\lfloor\log_2 k\rfloor$$

There are constants $C$ and $K_1$ such that for all $k>K_1$ and $n\ge 2k$, if every prime factor of $\binom{n}{k}$ exceeds $k$ then $k^2\le C\,n\lfloor\log_2 k\rfloor$; in words, $n\gg k^2/\log k$ on the pairs in question. $\operatorname{minFac}$ is Mathlib's `Nat.minFac`, the least prime factor (here $\binom{n}{k}\ge 2$); `Nat.log 2 k` is $\lfloor\log_2 k\rfloor$ (and $0$ for $k\le 1$), a natural number, so the right-hand side is a product of naturals, and $k^2$ is `k * k`.
