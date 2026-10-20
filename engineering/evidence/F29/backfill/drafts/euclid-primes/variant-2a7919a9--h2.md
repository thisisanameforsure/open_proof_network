---
label: "A prime beyond the sum of a list"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall\, l\in\operatorname{List}(\mathbb{N}):\quad \bigl(\forall x\in l,\ x\le \textstyle\sum l\bigr)\ \Rightarrow\ \exists p\in\mathbb{N},\ \textstyle\sum l<p\ \wedge\ p\ \text{prime}$$

For every list of natural numbers, under the inherited hypothesis that each of its entries is at most its sum (the earlier hole's claim), there is a prime strictly greater than the sum of the list (`List.sum`). Prime is the problem's own `Opn.IsPrime`: $2\le p$ and every $d$ with $p=d\cdot c$ for some natural $c$ is $1$ or $p$.
