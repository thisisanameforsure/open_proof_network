## What the assembly proves, and from what {steps: h1}

Write $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$ and let $\{x\}=x-\lfloor x\rfloor$ be the fractional part. The node `erdos-68--h6` states
$$\forall M\ \exists N\ge M:\quad \{F_N\}\le 1-\frac1N\ \ \text{or}\ \ 1-\frac{1}{N+1}\le\{F_N\}.$$
The assembly has one hole (`erdos-68--h6--h1`), the first alternative alone:
$$\forall M\ \exists N\ge M:\quad \{F_N\}\le 1-\frac1N .$$

## Taking the first alternative {steps: s2 close}

Fix $M$. The hole supplies $N\ge M$ with $\{F_N\}\le 1-\frac1N$; the proof returns this $N$, with the first alternative of the disjunction. The second alternative is never used.
