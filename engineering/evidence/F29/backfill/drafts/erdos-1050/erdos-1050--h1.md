---
label: "Borwein approximants to T (untyped binders)"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists\, a,b:\ \bigl(\forall n\in\mathbb{N},\ b_n\,T-a_n\neq 0\bigr)\ \wedge\ \lim_{n\to\infty}\bigl(b_n\,T-a_n\bigr)=0,\qquad T=\sum_{m=0}^{\infty}\frac{1}{2^{m+3}-3}$$

There are two sequences $a$, $b$ such that $b_n T - a_n$ is never zero and tends to $0$, where $T$ is the sum of $1/(2^{m+3}-3)$ over all $m\ge 0$ (Lean's `∑'`, with the summation variable also written `n` in the file). As written, `a` and `b` carry no binder types and the sum, the quotient and the coercions `↑` carry no type ascriptions, so the text does not fix the domain of the arithmetic (the display reads it with $a,b:\mathbb{N}\to\mathbb{Z}$ and the sum in $\mathbb{R}$, the types the parent's `have borwein` carries); the limit is `Filter.Tendsto … atTop (nhds 0)`.
