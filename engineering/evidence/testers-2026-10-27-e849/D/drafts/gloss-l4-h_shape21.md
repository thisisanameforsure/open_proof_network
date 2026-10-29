$$\forall n, k \in \mathbb{N}:\quad 2 \le k \to 2(k+1) + 2 \le n \to \tbinom{n}{k} \ne \tbinom{n-2}{k+1}$$

Here $n$, $k$ are natural numbers. The hypothesis $2(k+1) + 2 \le n$ is the half-triangle condition $2(k+1) \le n - 2$ for the position $(n-2, k+1)$, written without subtraction; under it $n \ge 2$, so the Lean's truncated $n - 2$ is the ordinary $n - 2$. The inequation is the conclusion, not a hypothesis.

In words: no number is both $\binom{n}{k}$ and $\binom{n-2}{k+1}$ with $k \ge 2$ and both positions in the half triangle: the collision equation of shape $(m, l) = (n-2, k+1)$ has no solutions there.
