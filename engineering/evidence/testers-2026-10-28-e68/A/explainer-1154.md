## What the assembly proves

Write $S=\sum_{n\ge 2}\frac{1}{n!-1}$ and, for a natural number $N$, $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$, a finite sum computed in $\mathbb{R}$; $\{y\}=y-\lfloor y\rfloor$ is the fractional part. This is the first decomposition of the problem (route 1) with the remainder of $N!\,S$ pinned more tightly, between $1/(N+1)$ and $1/N$ instead of in $(0,2/N]$.

## The three holes {steps: h1 h2 h3}

- $h_1$ is the criterion of route 1, restated, so it is the existing node `erdos-68--h1`: if for every $M$ there is $N\ge M$ with $N!\,x$ not an integer, then $x$ is irrational.
- $h_2$ (node `erdos-68--h5`): for every $N\ge 4$ there is $c$ with $\frac{1}{N+1}<c<\frac{1}{N}$ and $N!\,S=F_N+c$.
- $h_3$ (node `erdos-68--h6`): for every $M$ there is $N\ge M$ with $\{F_N\}\le 1-\frac1N$ or $\{F_N\}\ge 1-\frac{1}{N+1}$.

## Choosing N {steps: s4 hN4 s6}

By $h_1$ applied to $x=S$, it suffices, given $M$, to find $N\ge M$ with $N!\,S$ not an integer. Apply $h_3$ to $\max(M,4)$: it gives $N\ge M$ with $N\ge 4$ and $\{F_N\}$ outside the open interval $\big(1-\frac1N,\,1-\frac1{N+1}\big)$. Apply $h_2$ to this $N$: $N!\,S=F_N+c$ with $\frac1{N+1}<c<\frac1N$; in particular $0<c<1$.

## N!·S is not an integer {steps: hNpos hF h0 h1' key hcpos hc1' hk close}

Suppose $N!\,S=m$ with $m\in\mathbb{Z}$. Then $\{F_N\}+c=m-\lfloor F_N\rfloor$ is an integer, and since $0\le\{F_N\}<1$ and $0<c<1$ it lies strictly between $0$ and $2$, so it equals $1$. Hence $\{F_N\}=1-c$, which lies strictly between $1-\frac1N$ and $1-\frac1{N+1}$, contradicting the choice of $N$ (linear arithmetic in each of the two cases).
