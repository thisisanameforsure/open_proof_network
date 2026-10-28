Throughout, $S=\sum_{n\ge 2}\frac{1}{n!-1}$ (the Lean sum $\sum_{n\ge 0} 1/((n+2)!-1)$), and for $N\ge 2$, $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$, a finite sum of rationals computed in $\mathbb{R}$.

## The criterion (h1)

Lemma (a hole, node `erdos-68--h1`): for every real $x$, if for every $M$ there is $N\ge M$ such that $N!\,x$ is not an integer, then $x$ is irrational. (If $x=p/q$, then $N!\,x$ is an integer for every $N\ge q$.)

## The tail split (h2)

Lemma (a hole, node `erdos-68--h2`): for every $N\ge 2$ there is a real $c$ with $0<c\le 2/N$ and $N!\,S=F_N+c$. (Here $c=N!\sum_{n>N}\frac{1}{n!-1}$.)

## The open core (h3)

Lemma (a hole, node `erdos-68--h3`): for every $M$ there is $N\ge M$ with $\operatorname{frac}(F_N)<1-\frac{2}{N}$, where $\operatorname{frac}(y)=y-\lfloor y\rfloor$.

## The assembly

By the criterion applied to $x=S$, it suffices, given $M$, to produce $N\ge M$ with $N!\,S\notin\mathbb{Z}$. Apply the open core to $\max(M,2)$: it gives $N\ge\max(M,2)$, so $N\ge M$ and $N\ge 2$, with $\operatorname{frac}(F_N)<1-2/N$. Apply the tail split to this $N$: $N!\,S=F_N+c$ with $0<c\le 2/N$.

Suppose $N!\,S=m$ for an integer $m$. Then $F_N+c=m$, so
$$\operatorname{frac}(F_N)+c=m-\lfloor F_N\rfloor,$$
an integer. Since $\operatorname{frac}(F_N)\ge 0$ and $c>0$, this integer is positive; since $\operatorname{frac}(F_N)<1-2/N$ and $c\le 2/N$, it is less than $1$. No integer lies strictly between $0$ and $1$ (the final `omega`), so $N!\,S$ is not an integer, and $S$ is irrational given the three lemmas.
