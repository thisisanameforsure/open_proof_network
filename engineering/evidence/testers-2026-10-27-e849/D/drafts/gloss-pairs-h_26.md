$$\forall n, m \in \mathbb{N}:\quad 4 \le n \to 12 \le m \to \tbinom{n}{2} = \tbinom{m}{6} \to (n, m) = (78, 14)$$

Here $n$, $m$ are natural numbers; the bounds $4 \le n$ and $12 \le m$ are the half-triangle conditions $2 \cdot 2 \le n$ and $2 \cdot 6 \le m$ for the fixed columns $k = 2$, $l = 6$. The conclusion is written in the Lean as a disjunction of conjunctions of equalities.

In words: the only solutions of $\binom{n}{2} = \binom{m}{6}$ with $(n, 2)$ and $(m, 6)$ in the half triangle are $(n, m) = (78, 14)$ (the value $3003$): the complete solution of the collision equation for the column pair $(2, 6)$.
