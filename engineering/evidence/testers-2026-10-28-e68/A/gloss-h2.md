$$\forall N\in\mathbb{N}:\quad N\ge 2\ \Longrightarrow\ \exists c\in\mathbb{R}:\ \ 0<c,\quad c\le\frac{2}{N},\quad N!\sum_{n=0}^{\infty}\frac{1}{(n+2)!-1}=\sum_{n=2}^{N}\frac{N!}{n!-1}+c$$

All arithmetic is in $\mathbb{R}$. The infinite sum is Lean's `∑'`, which is defined as $0$ for a family that is not summable; its index starts at $0$ with summand $1/((n+2)!-1)$, so it is $\sum_{n\ge 2}1/(n!-1)$, the sum of Erdős problem 68. The finite sum runs over $2\le n\le N$.

In words: for $N\ge 2$, $N!$ times the series is the finite sum of its first $N-1$ terms, each multiplied by $N!$, plus a remainder $c$ with $0<c\le 2/N$.
