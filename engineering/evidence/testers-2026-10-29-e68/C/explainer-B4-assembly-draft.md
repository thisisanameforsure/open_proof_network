## What the assembly proves, and from what {steps: h1 close}

Write $F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$ and let $\{x\}=x-\lfloor x\rfloor$ be the fractional part. The node `erdos-68--h6` states
$$\forall M\ \exists N\ge M:\quad \{F_N\}\le 1-\frac1N\ \ \text{or}\ \ 1-\frac{1}{N+1}\le\{F_N\}.$$
The assembly proves it from its one hole (`erdos-68--h6--h1`): for every $M$ some $N\ge M$ has $\{F_N\}\le 1-\frac1N$. Given $M$, the hole supplies such an $N$, and that $N$ satisfies the first alternative. The second alternative is never used.
