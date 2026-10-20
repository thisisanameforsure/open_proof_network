---
label: "Every k with 1 <= k <= n divides n!"
supersedes: df65addf582c5fd4ae8595d218337ee5776840712b913e385c367013d23457a2
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n,k\in\mathbb{N}:\quad 0<k\le n\ \Rightarrow\ k\mid n!$$

For all natural numbers $n$ and $k$ with $0<k$ and $k\le n$, $k$ divides $n!$ (Mathlib's `Nat.factorial`). Divisibility is the problem's own `Opn.Divides`: $k\mid m$ means $m=k\cdot c$ for some natural number $c$.
