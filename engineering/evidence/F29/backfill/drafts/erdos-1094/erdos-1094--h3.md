---
label: "Small range 2k ≤ n < k²: k is bounded"
supersedes: "8af8380f707963c0bd6dc3714eaf8532669a2cccd84f686ac6bf80326813f08f"
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists K\ \forall n,k\in\mathbb{N}:\quad 0<k,\ \ 2k\le n<k^2,\ \ \operatorname{lpf}\tbinom{n}{k} > k \implies k\le K$$

- Lean writes $k^2$ as `k * k`.
- $\operatorname{lpf}$ is Mathlib's `Nat.minFac`. It is the least prime factor of any $m\ge 2$; `Nat.minFac 1 = 1` and `Nat.minFac 0 = 2`. Here $n>k>0$, so $\binom{n}{k}\ge 2$.
- On this range $\lfloor n/k\rfloor<k$, so the condition is the root's condition $\operatorname{lpf}\binom{n}{k} > \max(\lfloor n/k\rfloor,k)$.
