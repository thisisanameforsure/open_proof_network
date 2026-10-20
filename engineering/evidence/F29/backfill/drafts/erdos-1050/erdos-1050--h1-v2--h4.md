---
label: "Borwein's remainder bound (with the denominator hypothesis)"
supersedes: 5da96e2ecab5896e2356cfb00a6829b52891caa8c0ffe0e0763a09d72391000c
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n\in\mathbb{N}:\qquad R_n>0\quad\wedge\quad R_n^{2}\,2^{4n^2}\le 2^{2n+4},\qquad R_n=3T\,Q_x(n)-A_q(n),\quad T=\sum_{m=0}^{\infty}\frac{1}{2^{m+3}-3}$$

For every natural number $n$ the real number $R_n$ is positive and $R_n^2\cdot 2^{4n\cdot n}\le 2^{2n+4}$ (that is, $R_n\le 2^{\,n+2-2n^2}$), where $T$ is Lean's `∑'` over all $m\in\mathbb{N}$ in $\mathbb{R}$ (which would be $0$ for a non-summable family; this one converges) and $Q_x(n)$, $A_q(n)$ are read as reals. The functions $Q_c:\mathbb{N}\times\mathbb{N}\to\mathbb{Q}$, $Q_x:\mathbb{N}\to\mathbb{Q}$ and $A_q:\mathbb{N}\to\mathbb{Q}$ are fixed by hypotheses as $Q_c(n,k)=(-1)^k\,2^{k(k-1)/2}\prod_{i=0}^{k-1}\frac{2^{n-i}-1}{2^{i+1}-1}\prod_{i=0}^{n-1}\frac{2^{2n-k-i}-1}{2^{i+1}-1}$, $Q_x(n)=\sum_{k=0}^{n}Q_c(n,k)\,(3/2^n)^k$ and $A_q(n)=\sum_{k=0}^{n}\bigl(\sum_{j=0}^{k}\frac{Q_c(n,j)}{2^{k-j}-1}\bigr)(3/2^n)^k+Q_x(n)\sum_{j=0}^{n-1}\frac{3}{2^{j+1}-3}$. The statement carries one further hypothesis, which the conclusion does not use: for every $n$ there is a natural number $d>0$ with $d^2\le 2^{3n^2}$ such that $d\,Q_x(n)$ and $d\,A_q(n)$ are integers. Exponents are natural numbers (subtraction in them stops at $0$, $k(k-1)/2$ is natural-number division), division is in $\mathbb{Q}$ with $x/0=0$ so the $j=k$ term of the inner sum of $A_q$ is $0$, and where these functions are used $k\le n$, so no other exponent is truncated.
