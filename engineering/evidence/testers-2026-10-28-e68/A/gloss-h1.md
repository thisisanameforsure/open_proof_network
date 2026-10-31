$$\forall x\in\mathbb{R}:\quad \Big(\forall M\in\mathbb{N}\ \exists N\in\mathbb{N}\ \big(N\ge M\ \text{and}\ \forall m\in\mathbb{Z},\ N!\,x\ne m\big)\Big)\ \Longrightarrow\ x\notin\mathbb{Q}$$

`Irrational x` is Lean's "x is not the image of a rational number"; $N!$ and $m$ are read as real numbers.

In words: if $N!\,x$ fails to be an integer for arbitrarily large $N$, then $x$ is irrational.
