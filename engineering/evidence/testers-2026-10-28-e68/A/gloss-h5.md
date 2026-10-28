$$\forall N\in\mathbb{N}:\quad N\ge 4\ \Longrightarrow\ \exists c\in\mathbb{R}:\ \ \frac{1}{N+1}<c,\quad c<\frac{1}{N},\quad N!\sum_{n=0}^{\infty}\frac{1}{(n+2)!-1}=\sum_{n=2}^{N}\frac{N!}{n!-1}+c$$

All arithmetic is in $\mathbb{R}$. The infinite sum is Lean's `∑'`, defined as $0$ for a family that is not summable; its index starts at $0$ with summand $1/((n+2)!-1)$, so it is $\sum_{n\ge 2}1/(n!-1)$. The finite sum runs over $2\le n\le N$.

In words: for $N\ge 4$, $N!$ times the series is $\sum_{n=2}^{N} N!/(n!-1)$ plus a remainder strictly between $1/(N+1)$ and $1/N$.
