## Overview {steps: hrun}

Write $e_m = \frac{1}{2^m-1}$ (in Lean $e_0 = \frac10 = 0$) and let $r$ be the greedy remainder of $\frac12$: $r_0 = \frac12$, and $r_{m+1} = r_m - e_m$ if $e_m \le r_m$ (step $m$ is taken), else $r_{m+1} = r_m$ (step $m$ is skipped). The statement: at every skipped $m$, $r_m \le \frac{1}{2^m} + \frac{1}{3\cdot4^m}$. The proof reduces it to a statement about runs of taken steps: after a skipped $m \ge 2$ the walk skips again within $(m, 2m]$. That is the hole, `hrun`, left open (node spec-a70fcca4--h4--h1--h1). The reduction is that a skipped $m$ with $r_m > 2^{-m}$ would force every step of $(m, 2m]$ to be taken, because those $m$ terms sum to less than $2^{-m}$.

## A termwise bound {steps: hup}

For real $x \ge 2$, $\frac{1}{x-1} \le \frac12\cdot\frac2x + 2\cdot\frac1{x^2}$, that is $\frac{1}{x-1} \le \frac1x + \frac2{x^2}$: multiplied out, $x^2 \le (x-1)(x+2) = x^2 + x - 2$, which holds since $x \ge 2$.

## The block bound {steps: hblock}

For $m \ge 1$, put $a = 2^{-m}$. Each term $e_{m+1+i}$ with $i < m$ has $2^{m+1+i} \ge 2$, so by `hup` it is at most $a\cdot\frac12\cdot(\tfrac12)^i + 2\cdot a^2\cdot\frac14\cdot(\tfrac14)^i$. Summing the two finite geometric series over $i < m$ gives $\sum_{k=m+1}^{2m} e_k \le a - \frac{a^2}3 - \frac{2a^4}3 < a = 2^{-m}$.

## The small cases {steps: s4}

At $m = 0$ the hypothesis $r_0 < e_0 = 0$ is false. At $m = 1$, $r_1 = r_0 = \frac12$ (step $0$ subtracts $e_0 = 0$), and $\frac12 \le \frac12 + \frac1{12}$.

## The close for m ≥ 2 {steps: s5}

Suppose the bound fails at a skipped $m \ge 2$. Then $r_m > 2^{-m}$, and by `hblock` $r_m$ exceeds every partial sum $e_{m+1} + \dots + e_{m+j}$ with $j \le m$. The hole gives a skipped $n$ with $m < n \le 2m$. An induction along the block (`hwalk`) shows that every step $m+1, \dots, n$ is taken, with $r_{m+1+j} = r_m - (e_{m+1} + \dots + e_{m+j})$: the remainder at each of these steps still exceeds the next term, because the partial sum through it is below $r_m$. In particular $e_n \le r_n$, which contradicts $n$ being skipped.
