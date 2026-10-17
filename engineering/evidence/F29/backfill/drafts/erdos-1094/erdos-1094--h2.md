---
label: "bounded k on n ≥ k²"
supersedes: 4c5c5872d7e4700e00a06bc5941ffb6542045a7c07ab2cc016ee87d74624b0bf
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ k^2\le n,\ \ \operatorname{lpf}\tbinom{n}{k} > \lfloor n/k\rfloor \implies k\le K$$

- Lean writes $k^2$ as `k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $\binom{n}{k}\ge 2$ except at $n=k=1$, where the condition fails.
- `n / k` is floor division, so the statement has $\lfloor n/k\rfloor$. Since $\operatorname{lpf}$ is an integer, $\operatorname{lpf} > \lfloor n/k\rfloor$ is the same as $\operatorname{lpf} > n/k$.
- One $K$ serves every $n$. On this range $\lfloor n/k\rfloor\ge k$, so the condition is the root's condition $\operatorname{lpf}\binom{n}{k} > \max(\lfloor n/k\rfloor,k)$.
