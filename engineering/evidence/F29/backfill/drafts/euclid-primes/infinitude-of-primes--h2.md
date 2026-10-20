---
label: "Every m >= 2 has a prime divisor"
supersedes: 000e299f1638dc9d4723f0a530fa7dcb8d1f6996c33d71876fd7dc65dc22d86a
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n\in\mathbb{N}:\quad \bigl(\forall k,\ 0<k\le n\Rightarrow k\mid n!\bigr)\ \Rightarrow\ \forall m\ge 2,\ \exists p\in\mathbb{N},\ p\ \text{prime}\ \wedge\ p\mid m$$

For every natural number $n$, under the inherited hypothesis that every $k$ with $0<k\le n$ divides $n!$ (the earlier hole's claim, which the conclusion does not use), every natural number $m\ge 2$ has a prime divisor $p$. Prime is the problem's own `Opn.IsPrime` ($2\le p$ and every $d$ dividing $p$ is $1$ or $p$) and divisibility is `Opn.Divides` ($a\mid b$ when $b=a\cdot c$ for some natural $c$); $n!$ is `Nat.factorial`.
