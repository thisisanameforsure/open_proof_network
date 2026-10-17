---
label: "Residue form, k even"
supersedes: "8a9d9e741c86024d214ae4b70a0966f7f6b3b9ef81622d784c350e31ed87ab8d"
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_1\ \forall n,k\in\mathbb{N}:\quad K_1<k,\ \ 2k\le n<k^2,\ \ k \text{ even} \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

- Lean writes $k^2$ as `k * k` and "$k$ even" as `k % 2 = 0`.
- `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$.
- Nothing is said about odd $k$.

By Kummer's theorem such a $p$ divides $\binom{n}{k}$, since subtracting $k$ from $n$ in base $p$ borrows at the last digit. The statement itself mentions no binomial coefficient.
