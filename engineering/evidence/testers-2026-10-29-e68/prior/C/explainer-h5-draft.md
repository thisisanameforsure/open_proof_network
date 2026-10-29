## What is proved

For every integer $N \ge 4$ there is a real $c$ with $\frac{1}{N+1} < c < \frac1N$ and
$$N!\sum_{n\ge 0}\frac{1}{(n+2)!-1} \;=\; \sum_{n=2}^{N}\frac{N!}{n!-1} \;+\; c .$$
The proof takes $c$ to be the scaled tail $c = N!\sum_{j\ge 0}\frac{1}{(j+N+1)!-1}$, the part of $N!\,S$ from the terms with $n > N$, and bounds it on both sides. Three lemmas in the file's private helper block carry the work.

## A factorial inequality (C_fac_big)

For $N \ge 4$, $2N(N+2) < (N+1)!$. By induction from $N = 4$ ($48 < 120$): if it holds at $n$, then $2(n+1)(n+3) \le (n+2)\cdot 2n(n+2) < (n+2)(n+1)! = (n+2)!$.

## One term of the tail (C_term_le)

Let $m = j + N + 1$ with $N \ge 1$. Since $m! = N!\,(N+1)(N+2)\cdots(N+1+j) \ge N!\,(N+1)(N+2)^j$, and since $m! \ge (N+1)! \ge 2$ gives $\frac{1}{m!-1} \le \frac{1}{m!}\bigl(1 + \frac{2}{(N+1)!}\bigr)$,
$$\frac{N!}{m!-1} \;\le\; \Bigl(1+\frac{2}{(N+1)!}\Bigr)\,\frac{1}{N+1}\,\Bigl(\frac{1}{N+2}\Bigr)^{j}.$$

## Both bounds on c (C_tail_sharp)

Upper bound. The right-hand side is a geometric series with ratio $\frac1{N+2}$, so the tail converges by comparison and
$$c \;\le\; \Bigl(1+\frac{2}{(N+1)!}\Bigr)\frac{N+2}{(N+1)^2} \;=\; \frac{((N+1)!+2)(N+2)}{(N+1)!\,(N+1)^2}.$$
This is $< \frac1N$ exactly when $N(N+2)\bigl((N+1)!+2\bigr) < (N+1)!\,(N+1)^2$, i.e. $2N(N+2) < (N+1)!$, the factorial inequality.

Lower bound. All terms are positive, so $c$ is at least $N!$ times its first term: $c \ge \frac{N!}{(N+1)!-1} > \frac{N!}{(N+1)!} = \frac{1}{N+1}$.

## The identity

The whole series converges (each term is at most $2/(n+2)!$, compared with the series for $e$). Split it after its first $N-1$ terms (Mathlib's `Summable.sum_add_tsum_nat_add`); the second piece, re-indexed by $i + (N-1) + 2 = i + N + 1$, is exactly the tail in $c$. Multiplying by $N!$ and re-indexing the finite sum from $\{2,\dots,N\}$ to $k + 2$ for $k < N-1$ gives the identity, term by term.
