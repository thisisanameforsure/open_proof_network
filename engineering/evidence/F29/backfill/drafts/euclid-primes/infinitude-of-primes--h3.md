---
label: "Only 1 divides two consecutive numbers"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n\in\mathbb{N}:\ \bigl(\forall k,\ 0<k\le n\Rightarrow k\mid n!\bigr)\Rightarrow\bigl(\forall m\ge 2,\ \exists p,\ p\ \text{prime}\wedge p\mid m\bigr)\Rightarrow\ \forall d,m\in\mathbb{N},\ d\mid m\ \wedge\ d\mid m+1\ \Rightarrow\ d=1$$

For every natural number $n$, under the two inherited hypotheses (every $k$ with $0<k\le n$ divides $n!$, and every $m\ge 2$ has a prime divisor; the earlier holes' claims, which the conclusion does not use), any natural number $d$ dividing both $m$ and $m+1$ equals $1$. Divisibility is the problem's own `Opn.Divides` ($a\mid b$ when $b=a\cdot c$ for some natural $c$), prime is `Opn.IsPrime`, and $n!$ is `Nat.factorial`.
