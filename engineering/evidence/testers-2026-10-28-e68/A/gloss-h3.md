$$\forall M\in\mathbb{N}\ \exists N\in\mathbb{N}:\quad N\ge M\ \ \text{and}\ \ \Big\{\sum_{n=2}^{N}\frac{N!}{n!-1}\Big\}<1-\frac{2}{N}$$

Here $\{y\}=y-\lfloor y\rfloor\in[0,1)$ is the fractional part (Lean's `Int.fract`), and the sum and both divisions are in $\mathbb{R}$. The sum is empty, so $0$, when $N<2$. Lean reads $2/N$ as $0$ at $N=0$, so $N=0$ satisfies the inequality and the case $M=0$ holds trivially; at $N=1$ the right side is $-1$.

In words: for arbitrarily large $N$, the fractional part of the finite sum $\sum_{n=2}^{N} N!/(n!-1)$ lies below $1-2/N$.
