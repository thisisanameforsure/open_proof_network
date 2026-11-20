## What is proved, and the lemmas it rests on

For every integer $N \ge 4$ there is a real $c$ with $\frac{1}{N+1} < c < \frac1N$ and
$$N!\sum_{n\ge 0}\frac{1}{(n+2)!-1} \;=\; \sum_{n=2}^{N}\frac{N!}{n!-1} \;+\; c .$$
The witness is the scaled tail $c = N!\sum_{j\ge 0}\frac{1}{(j+N+1)!-1}$, the part of $N!\,S$ from the terms with $n > N$. Three lemmas in the file's private helper block bound it; they are not nodes.

*A factorial inequality* (`C_fac_big`). For $N \ge 4$, $2N(N+2) < (N+1)!$, by induction from $N = 4$ ($48 < 120$): if it holds at $n$, then $2(n+1)(n+3) \le (n+2)\cdot 2n(n+2) < (n+2)\,(n+1)! = (n+2)!$.

*One term of the tail* (`C_term_le`). Let $N \ge 1$ and $m = j + N + 1$. Since $m! \ge N!\,(N+1)(N+2)^j$ (Mathlib's `Nat.factorial_mul_pow_le_factorial`), and since $m! \ge (N+1)! \ge 2$ gives $\frac{1}{m!-1} \le \frac{1}{m!}\bigl(1 + \frac{2}{(N+1)!}\bigr)$,
$$\frac{N!}{m!-1} \;\le\; \Bigl(1+\frac{2}{(N+1)!}\Bigr)\,\frac{1}{N+1}\,\Bigl(\frac{1}{N+2}\Bigr)^{j}.$$

*Both bounds on the tail* (`C_tail_sharp`, for $N \ge 4$). The right-hand side above is a geometric series with ratio $\frac1{N+2}$, so the tail converges by comparison and
$$c \;\le\; \Bigl(1+\frac{2}{(N+1)!}\Bigr)\frac{N+2}{(N+1)^2} \;=\; \frac{\bigl((N+1)!+2\bigr)(N+2)}{(N+1)!\,(N+1)^2}.$$
Clearing denominators, this is $< \frac1N$ exactly when $2N(N+2) < (N+1)!$, the factorial inequality. For the lower bound, every term is positive, so $c$ is at least $N!$ times its first term: $c \ge \frac{N!}{(N+1)!-1} > \frac{N!}{(N+1)!} = \frac{1}{N+1}$.

## Taking c to be the tail {steps: s1}

The proof applies `C_tail_sharp` at $N$ (allowed, as $N \ge 4$), obtaining both strict bounds, and offers the tail itself as $c$. What remains is the identity.

## The identity {steps: hsplit he hI close}

The whole series converges (a fourth helper, `C_summable`, compares each term with $2/(n+2)!$ and uses the series for $e$). Split it after its first $N-1$ terms: $\sum_{i\ge 0} a_i = \sum_{i<N-1} a_i + \sum_{i\ge 0} a_{i+N-1}$ with $a_i = 1/((i+2)!-1)$. Since $N \ge 4$, $i + (N-1) + 2 = i + N + 1$, so the second piece is exactly the tail inside $c/N!$. Multiply through by $N!$ and distribute over the finite sum. Finally write $\{2,\dots,N\}$ as $[2, N+1)$ and re-index $n = k + 2$ for $k < N - 1$; the two finite sums then agree term by term, since $N!\cdot\frac{1}{x} = \frac{N!}{x}$.
