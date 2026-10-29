$$\forall n, m \in \mathbb{N}:\quad 4 \le n \to 16 \le m \to \tbinom{n}{2} = \tbinom{m}{8} \to (n, m) = (221, 17)$$

Here $n$, $m$ are natural numbers; the bounds $4 \le n$ and $16 \le m$ are the half-triangle conditions $2 \cdot 2 \le n$ and $2 \cdot 8 \le m$ for the fixed columns $k = 2$, $l = 8$. The conclusion is written in the Lean as a disjunction of conjunctions of equalities.

In words: the only solutions of $\binom{n}{2} = \binom{m}{8}$ with $(n, 2)$ and $(m, 8)$ in the half triangle are $(n, m) = (221, 17)$ (the value $24310$): the complete solution of the collision equation for the column pair $(2, 8)$.
