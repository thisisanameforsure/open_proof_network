---
label: "The factorial is positive"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n\in\mathbb{N}:\ \bigl(\forall k,\ 0<k\le n\Rightarrow k\mid n!\bigr)\Rightarrow\bigl(\forall m\ge 2,\ \exists p,\ p\ \text{prime}\wedge p\mid m\bigr)\Rightarrow\bigl(\forall d,m,\ d\mid m\wedge d\mid m+1\Rightarrow d=1\bigr)\Rightarrow\ \forall k\in\mathbb{N},\ 0<k!$$

For every natural number $n$, under the three inherited hypotheses (every $k$ with $0<k\le n$ divides $n!$; every $m\ge 2$ has a prime divisor; a common divisor of $m$ and $m+1$ is $1$; the earlier holes' claims, which the conclusion does not use), every factorial $k!$ is positive. Divisibility is the problem's own `Opn.Divides`, prime is `Opn.IsPrime`, and the factorial is Mathlib's `Nat.factorial`.
