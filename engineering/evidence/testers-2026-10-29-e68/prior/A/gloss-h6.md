$$\forall M\in\mathbb{N}\ \exists N\in\mathbb{N}:\quad N\ge M\ \ \text{and}\ \ \Big(\{F_N\}\le 1-\frac{1}{N}\ \ \text{or}\ \ 1-\frac{1}{N+1}\le\{F_N\}\Big),\qquad F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$$

Here $\{y\}=y-\lfloor y\rfloor\in[0,1)$ is the fractional part (Lean's `Int.fract`), and the sum and all divisions are in $\mathbb{R}$. The sum is empty, so $0$, when $N<2$. Lean reads $1/N$ as $0$ at $N=0$, so $N=0$ satisfies the first alternative and the case $M=0$ holds trivially.

In words: for arbitrarily large $N$, the fractional part of $F_N$ lies outside the open interval $\big(1-\frac{1}{N},\,1-\frac{1}{N+1}\big)$.
