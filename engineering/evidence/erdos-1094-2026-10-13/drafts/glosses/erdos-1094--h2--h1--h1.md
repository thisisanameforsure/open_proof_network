$$\exists K\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ 2k\le n<k^3,\ \ \operatorname{lpf}\tbinom{n}{k} > k \implies k\le K$$

- Lean writes $k^3$ as `k * k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $n>k>0$, so $\binom{n}{k}\ge 2$.
- The bound is $k$, not $\lfloor n/k\rfloor$: the condition says $\binom{n}{k}$ has no prime factor $p\le k$.
- Nothing is said about $n\ge k^3$.
