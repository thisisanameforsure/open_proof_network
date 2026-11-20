## What the assembly proves

Write $S=\sum_{n\ge 2}\frac{1}{n!-1}$ (in the Lean, $\sum_{n\ge 0} 1/((n+2)!-1)$ over the reals) and, for a natural number $N$, $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$, a finite sum computed in $\mathbb{R}$. The file proves that $S$ is irrational from three lemmas it leaves open as holes. It is the argument that proves $e$ irrational: a rational $S$ would make $N!\,S$ an integer for every large $N$, and the holes say that this fails for arbitrarily large $N$.

## The three holes {steps: h1 h2 h3}

- $h_1$ (node `erdos-68--h1`): for every real $x$, if for every $M$ there is $N\ge M$ such that $N!\,x\ne m$ for every integer $m$, then $x$ is irrational.
- $h_2$ (node `erdos-68--h2`): for every $N\ge 2$ there is a real $c$ with $0<c\le 2/N$ and $N!\,S=F_N+c$.
- $h_3$ (node `erdos-68--h3`): for every $M$ there is $N\ge M$ with $\operatorname{frac}(F_N)<1-\frac{2}{N}$, where $\operatorname{frac}(y)=y-\lfloor y\rfloor$ (Lean's `Int.fract`).

Each is assumed here and is a node of its own.

## Choosing N {steps: s4 s5}

By $h_1$ applied to $x=S$, it suffices, given $M$, to find $N\ge M$ such that $N!\,S$ is no integer. Apply $h_3$ to $\max(M,2)$: this gives $N\ge\max(M,2)$, hence $N\ge M$ and $N\ge 2$, with $\operatorname{frac}(F_N)<1-2/N$. Apply $h_2$ to this $N$: $N!\,S=F_N+c$ with $0<c\le 2/N$.

## N!·S is not an integer {steps: hF h0 key hlt hpos hlt' hpos' close}

Suppose $N!\,S=m$ with $m\in\mathbb{Z}$. Then $F_N+c=m$, and since $F_N=\lfloor F_N\rfloor+\operatorname{frac}(F_N)$,
$$\operatorname{frac}(F_N)+c=m-\lfloor F_N\rfloor,$$
which is an integer. From $\operatorname{frac}(F_N)\ge 0$ and $c>0$ it is positive; from $\operatorname{frac}(F_N)<1-2/N$ and $c\le 2/N$ it is less than $1$ (both by linear arithmetic). An integer strictly between $0$ and $1$ does not exist, which closes the proof. So the three holes together imply that $S$ is irrational; $h_1$ and $h_2$ are elementary, and $h_3$ is the open question.
