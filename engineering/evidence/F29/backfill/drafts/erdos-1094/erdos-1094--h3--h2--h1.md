---
label: "Ecklund–Erdős–Selfridge: n > k^(1+c) when lpf C(n,k) > k"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists c\in\mathbb{R},\ c>0,\ \exists K_2\in\mathbb{N}\ \forall n,k\in\mathbb{N}:\quad K_2<k,\ \ 2k\le n,\ \ \operatorname{minFac}\tbinom{n}{k}>k \implies k^{1+c} < n$$

There is an absolute real $c>0$ and a threshold $K_2$ such that for all $k>K_2$ and $n\ge 2k$, if every prime factor of $\binom{n}{k}$ exceeds $k$ then $n$ exceeds $k^{1+c}$. The inequality is in the reals: $k$ and $n$ are cast to $\mathbb{R}$ and $k^{1+c}$ is the real power `(↑k : ℝ) ^ (1 + c)`; $\operatorname{minFac}$ is Mathlib's `Nat.minFac`, the least prime factor.
