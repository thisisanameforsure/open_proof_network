## What the assembly proves, and from what {steps: ht hcore}

Write $S=\sum_{n\ge 2}\frac{1}{n!-1}$ and $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$, and let $\{x\}=x-\lfloor x\rfloor$ be the fractional part. The node states
$$\forall M\ \exists N\ge M:\quad \{F_N\} < 1-\frac{2}{N}.$$
The assembly derives this from two statements, each a hole of the partial:

- the tail split (the same statement as `erdos-68--h2`, already proved): for every $N\ge 2$ there is $c$ with $0<c\le \frac2N$ and $N!\,S = F_N + c$;
- the open core (`erdos-68--h3--h2`): there is $\delta>0$ such that for every $M$ some $N\ge M$ has $\delta\le\{N!\,S\}\le 1-\delta$.

## Choosing N {steps: s3 s4 s5 hN2 hKN hNpos hKr h_x3b4N}

Fix $M$. Take $\delta$ from the core, and an integer $K>\frac{2}{\delta}$ (Archimedes). Apply the core at $\max(M,K,2)$: it gives $N\ge M$, $N\ge K$, $N\ge 2$ with $\delta\le\{N!S\}\le 1-\delta$. Since $N\ge K>\frac2\delta$, we have $\frac2N<\delta$.

## The fractional part of F_N {steps: s8 hxF key close}

The tail split at $N$ (allowed, as $N\ge2$) gives $N!S=F_N+c$ with $0<c\le\frac2N$. Because $c\le\frac2N<\delta\le\{N!S\}$, subtracting $c$ from $N!S$ does not cross an integer: $\{F_N\}=\{N!S\}-c$, which the proof checks from the definition of the fractional part, with $\lfloor N!S\rfloor$ as the integer. Hence
$$\{F_N\}=\{N!S\}-c\le 1-\delta-c<1-\delta<1-\frac2N .$$
(Only the upper bound $\{N!S\}\le1-\delta$ and $c>0$ are needed for the last inequality; the lower bound $\delta\le\{N!S\}$ is what makes the subtraction stay inside $[0,1)$.)
