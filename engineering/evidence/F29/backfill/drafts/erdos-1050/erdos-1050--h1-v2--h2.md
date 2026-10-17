---
label: "Integrality: b(n)z - a(n) = 9^n W(n) E(n)"
supersedes: d6b4a8ae5efadbbfb4dae77bbafb09db7f90510f235b1e1cf6333ef20ccbd7be
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists\, a,b:\mathbb{N}\to\mathbb{Z}\ \ \forall n\ge 1:\qquad b(n)\,z-a(n)\;=\;9^n\,W(n)\,E(n)$$

There are two sequences of integers $a(n)$, $b(n)$ such that for every $n\ge 1$ the identity holds in $\mathbb{R}$, where, with $c=8/3$, $z=\sum_{j\ge 0}\bigl(1-c\,2^{j+1}\bigr)^{-1}$, $W(n)=(n-2)!\;\prod_{k=1}^{n}\bigl(1-c\,2^{k}\bigr)\prod_{k=\lfloor (n+1)/2\rfloor}^{n}\bigl(1-2^{k}\bigr)$ and $E(n)=\sum_{j\ge 0}\;-\bigl(1-c\,2^{\,2n+j}\bigr)^{-1}\prod_{k=1}^{n-1}\bigl(1-2^{\,k-n-j}\bigr)\bigl(1-c\,2^{\,k+n+j}\bigr)^{-1}$. Here $n-2$ is natural-number subtraction (so $(n-2)!=0!=1$ at $n=1$), $\lfloor (n+1)/2\rfloor$ is natural-number division, the exponents $2n+j$, $k-n-j$ and $k+n+j$ in $E(n)$ are integers (so $2^{k-n-j}=1/2^{n+j-k}$, and the product over $k$ is empty at $n=1$), and both infinite sums are Lean's `∑'` over $j\ge 0$, which is $0$ for a non-summable family. Nothing is required of $a(0)$ or $b(0)$, and $a(n)$, $b(n)$ are not required to be nonzero.
