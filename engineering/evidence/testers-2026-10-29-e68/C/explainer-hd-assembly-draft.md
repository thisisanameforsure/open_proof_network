## What the assembly proves, and from what {steps: ht hd}

Write $S=\sum_{n\ge 2}\frac{1}{n!-1}$, $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$, and let $\{x\}=x-\lfloor x\rfloor$ be the fractional part. The node `erdos-68--h6--h1` states
$$\forall M\ \exists N\ge M:\quad \{F_N\}\le 1-\frac1N .$$
The assembly derives it from two holes:

- the sharp tail split (the same statement as `erdos-68--h5`, already proved): for every $N\ge 4$ there is $c$ with $\frac{1}{N+1}<c<\frac1N$ and $N!\,S=F_N+c$;
- the open core (`erdos-68--h6--h1--h2`): for every $M$ some $N\ge M$ has $\frac{2}{N+1}\le\{N!\,S\}<1-\frac{1}{N+1}$. In factorial base, $S=\sum a_n/n!$ with $0\le a_n\le n-1$, and $a_{N+1}=\lfloor (N+1)\{N!S\}\rfloor$; the core says $2\le a_{N+1}\le N-1$ for infinitely many $N$.

## Choosing N {steps: SRANGE1}

Fix $M$. The core at $\max(M,4)$ gives $N\ge M$, $N\ge4$ with $\frac{2}{N+1}\le\{N!S\}<1-\frac1{N+1}$, and the tail split at $N$ gives $c$ with $\frac1{N+1}<c<\frac1N$ and $N!S=F_N+c$.

## The fractional part of F_N {steps: SRANGE2}

Since $N\ge4$, $\frac1N\le\frac2{N+1}$, so $c<\frac1N\le\frac{2}{N+1}\le\{N!S\}$. Subtracting $c$ from $N!S$ therefore does not cross an integer: $\{F_N\}=\{N!S\}-c$, checked from the definition of the fractional part with $\lfloor N!S\rfloor$ as the integer. Then
$$\{F_N\}=\{N!S\}-c<1-\frac1{N+1}-\frac1{N+1}\le 1-\frac1N,$$
the last step because $\frac{2}{N+1}\ge\frac1N$ again.
