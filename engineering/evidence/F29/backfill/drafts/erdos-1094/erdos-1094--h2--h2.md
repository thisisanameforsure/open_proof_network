---
label: "bounded k on n ≥ k³"
supersedes: 0296fca70a88169108809ad4551aa381c05ee40d0b48e9198cde4ca6d8f95339
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ k^3\le n,\ \ \operatorname{lpf}\tbinom{n}{k} > \lfloor n/k\rfloor \implies k\le K$$

- Lean writes $k^3$ as `k * k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $\binom{n}{k}\ge 2$ except at $n=k=1$, where the condition fails.
- `n / k` is floor division, so the statement has $\lfloor n/k\rfloor$. Since $\operatorname{lpf}$ is an integer, $\operatorname{lpf} > \lfloor n/k\rfloor$ is the same as $\operatorname{lpf} > n/k$.
- On this range $\lfloor n/k\rfloor\ge k^2$.
