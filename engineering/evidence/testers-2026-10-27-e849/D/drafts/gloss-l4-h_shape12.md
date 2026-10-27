$$\forall n, k \in \mathbb{N}:\quad 2 \le k \to 2(k+2) + 1 \le n \to \tbinom{n}{k} \ne \tbinom{n-1}{k+2}$$

Here $n$, $k$ are natural numbers. The hypothesis $2(k+2) + 1 \le n$ is the half-triangle condition $2(k+2) \le n - 1$ for the position $(n-1, k+2)$, written without subtraction; under it $n \ge 1$, so the Lean's truncated $n - 1$ is the ordinary $n - 1$. The inequation is the conclusion, not a hypothesis.

In words: no number is both $\binom{n}{k}$ and $\binom{n-1}{k+2}$ with $k \ge 2$ and both positions in the half triangle: the collision equation of shape $(m, l) = (n-1, k+2)$ has no solutions there.
