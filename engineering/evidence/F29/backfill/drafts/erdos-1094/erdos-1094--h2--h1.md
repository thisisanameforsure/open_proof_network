---
label: "bounded k on k² ≤ n < k³"
supersedes: e1513fc4a0d02ca6e3728c6b34230a739d9403e0617a897348e7e198b4560758
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ k^2\le n<k^3,\ \ \operatorname{lpf}\tbinom{n}{k} > \lfloor n/k\rfloor \implies k\le K$$

- Lean writes $k^2$ and $k^3$ as `k * k` and `k * k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $\binom{n}{k}\ge 2$ except at $n=k=1$, where the condition fails.
- `n / k` is floor division, so the statement has $\lfloor n/k\rfloor$. Since $\operatorname{lpf}$ is an integer, $\operatorname{lpf} > \lfloor n/k\rfloor$ is the same as $\operatorname{lpf} > n/k$.
- On this range $k\le\lfloor n/k\rfloor<k^2$.
