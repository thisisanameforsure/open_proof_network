## What is proved, and the one lemma it rests on

For every integer $N \ge 2$ there is a real $c$ with $0 < c \le 2/N$ and
$$N!\sum_{n\ge 0}\frac{1}{(n+2)!-1} \;=\; \sum_{n=2}^{N}\frac{N!}{n!-1} \;+\; c .$$
The constant is the scaled tail $c = N!\sum_{j\ge 0}\frac{1}{(j+N+1)!-1}$, the part of $N!\,S$ coming from the terms with $n > N$.

Everything rests on a lemma proved in the file's private helper block (it is not a node): for every integer $K \ge 1$,
$$0 \;<\; K!\sum_{j\ge 0}\frac{1}{(j+K+1)!-1} \;\le\; \frac{K+1}{K^2}.$$
Proof of the lemma. Write $m = j+K+1$. First, $m! \ge K!\,(K+1)^{j+1}$ (Mathlib's `Nat.factorial_mul_pow_le_factorial`). In particular $m! \ge K+1$, so $m! - 1 \ge m!\cdot\frac{K}{K+1}$, and together
$$\frac{K!}{m!-1} \;\le\; \frac{K+1}{K}\cdot\frac{K!}{m!} \;\le\; \frac{1}{K}\Big(\frac{1}{K+1}\Big)^{j}.$$
The right-hand side is a convergent geometric series, so the series on the left converges (comparison) and its sum is at most $\frac1K\cdot\frac{1}{1-1/(K+1)} = \frac1K\cdot\frac{K+1}{K} = \frac{K+1}{K^2}$. Every term is positive because $m! \ge 2$, so the sum is positive (its first term alone is). A second helper shows the whole series $\sum_{n\ge0} 1/((n+2)!-1)$ converges, by comparing its terms with $2/(n+2)!$ and the series for $e$.

## The constant and its positivity {steps: s1}

Apply the lemma with $K = N$ (allowed, as $N \ge 2 \ge 1$). This gives the scaled tail $c$ together with $0 < c$ and $c \le (N+1)/N^2$; the proof takes $c$ to be exactly this tail.

## The bound c ≤ 2/N {steps: s2}

It remains to see $(N+1)/N^2 \le 2/N$. Clearing the positive denominators this is $(N+1)\,N \le 2N^2$, i.e. $N + 1 \le 2N$, which holds since $N \ge 2$ (the step records $2 \le N$ as a real inequality and closes the polynomial inequality by `nlinarith`).

## The identity {steps: s3}

Split the convergent series after its first $N-1$ terms: $\sum_{i\ge0} a_i = \sum_{i<N-1} a_i + \sum_{i\ge0} a_{i+N-1}$ with $a_i = 1/((i+2)!-1)$ (Mathlib's lemma Summable.sum_add_tsum_nat_add). Since $N \ge 2$, the index $i+(N-1)+2$ equals $i+N+1$, so the second piece is exactly the tail inside $c/N!$. Multiply through by $N!$ and distribute over the finite sum. Finally re-index the finite sum: $\{2,\dots,N\}$ is $[2, N+1)$, and $\sum_{n\in[2,N+1)} f(n) = \sum_{k< N-1} f(2+k)$, which matches $\sum_{i<N-1} N!\cdot a_i$ term by term because $2+k = k+2$ and $N!\cdot\frac{1}{x} = \frac{N!}{x}$.
