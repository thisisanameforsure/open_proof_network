$$\exists\,\delta>0\ \ \forall M\in\mathbb{N}\ \ \exists N\ge M:\qquad \delta\ \le\ \Big\{\,N!\sum_{n\ge 2}\frac{1}{n!-1}\Big\}\ \le\ 1-\delta$$

Here $\{x\}=x-\lfloor x\rfloor$ is the fractional part (`Int.fract`), and the sum is the root's number $S=\sum_{n\ge 2}1/(n!-1)$, written in Lean as a `tsum` over $n\ge 0$ of $1/((n+2)!-1)$. All arithmetic is in $\mathbb{R}$, and $\delta$ is a real number.

In words: one fixed margin $\delta$ works for infinitely many $N$, and at each of them $N!\,S$ is at distance at least $\delta$ from every integer.
