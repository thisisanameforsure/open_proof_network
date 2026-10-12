$$\exists K_1\ \forall n,k\in\mathbb{N}:\quad K_1<k,\ \ 2k\le n<k^2,\ \ k \text{ even} \implies \exists\,p\le k \text{ prime with } n \bmod p < k \bmod p$$

- Lean writes $k^2$ as `k * k` and "$k$ even" as `k % 2 = 0`.
- `n % p` is the least non-negative residue, so the condition reads $n \bmod p < k \bmod p$.
- Nothing is said about odd $k$.

By Kummer's theorem such a $p$ divides $\binom{n}{k}$, since subtracting $k$ from $n$ in base $p$ borrows at the last digit. The statement itself mentions no binomial coefficient.
