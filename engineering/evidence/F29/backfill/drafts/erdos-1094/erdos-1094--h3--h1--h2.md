---
label: "Residue form, k and n odd"
supersedes: "a2ee721ef615fe90eee3417fe8dc237be4136bf88f8e74f6891f5bb8f9c511e6"
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K_2\ \forall n,k\in\mathbb{N}:\quad K_2<k,\ \ 2k\le n<k^2,\ \ k \text{ odd},\ \ n \text{ odd} \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

- Lean writes $k^2$ as `k * k`, and "odd" as `k % 2 = 1` and `n % 2 = 1`.
- `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$.
- Nothing is said about even $k$, or about odd $k$ with even $n$.

By Kummer's theorem such a $p$ divides $\binom{n}{k}$, since subtracting $k$ from $n$ in base $p$ borrows at the last digit. The statement itself mentions no binomial coefficient.
