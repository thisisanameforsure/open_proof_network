$$\forall k\ge 1:\quad \Bigl\{n\in\mathbb{N} \;:\; k^2\le n,\ \ \operatorname{lpf}\tbinom{n}{k} > \lfloor n/k\rfloor\Bigr\}\ \text{ is finite}$$

- Lean writes $k^2$ as `k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $\binom{n}{k}\ge 2$ except at $n=k=1$, where $\binom{1}{1}=1$ and `Nat.minFac 1 = 1` is not $> 1$; so the edge values never satisfy the condition.
- `n / k` is floor division, so the statement has $\lfloor n/k\rfloor$. Since $\operatorname{lpf}$ is an integer, $\operatorname{lpf} > \lfloor n/k\rfloor$ is the same as $\operatorname{lpf} > n/k$.

The finite set may depend on $k$. No bound uniform in $k$ is stated.
