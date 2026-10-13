$$\Bigl\{(n,k)\in\mathbb{N}^2 \;:\; 0<k,\ \ 2k\le n,\ \ \operatorname{lpf}\tbinom{n}{k} > \max\bigl(\lfloor n/k\rfloor,\,k\bigr)\Bigr\}\ \text{ is finite}$$

- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $n > k > 0$, so $\binom{n}{k}\ge n\ge 2$ and $\operatorname{lpf}$ is the least prime factor.
- `n / k` is floor division, so the statement has $\lfloor n/k\rfloor$. Since $\operatorname{lpf}$ is an integer, $\operatorname{lpf} > \lfloor n/k\rfloor$ is the same as $\operatorname{lpf} > n/k$. The same holds inside the maximum.
- The guard $0<k$ matters: Lean has `n / 0 = 0` and $\binom{n}{0}=1$, so without it every pair $(n,0)$ would satisfy `Nat.minFac 1 = 1 > max 0 0` and the set would be infinite.

In words: for $n\ge 2k$, the least prime factor of $\binom{n}{k}$ is at most $\max(n/k,\,k)$, with only finitely many exceptions.
