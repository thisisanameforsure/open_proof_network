$$\forall M\in\mathbb{N}\ \ \exists N\ge M:\qquad \Big\{\sum_{n=2}^{N}\frac{N!}{n!-1}\Big\}\ \le\ 1-\frac{1}{N}$$

Here $\{x\}=x-\lfloor x\rfloor$ is the fractional part (`Int.fract`), the sum runs over $2\le n\le N$, and the quotients and $1/N$ are real divisions.

In words: for infinitely many $N$, the fractional part of the finite sum $F_N=\sum_{n=2}^{N}N!/(n!-1)$ is at most $1-1/N$.
