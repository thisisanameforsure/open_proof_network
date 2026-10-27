$$\forall n, m \in \mathbb{N}:\quad 4 \le n \to 10 \le m \to \tbinom{n}{2} = \tbinom{m}{5} \to (n, m) = (78, 15) \vee (n, m) = (153, 19)$$

Here $n$, $m$ are natural numbers; the bounds $4 \le n$ and $10 \le m$ are the half-triangle conditions $2 \cdot 2 \le n$ and $2 \cdot 5 \le m$ for the fixed columns $k = 2$, $l = 5$. The conclusion is written in the Lean as a disjunction of conjunctions of equalities.

In words: the only solutions of $\binom{n}{2} = \binom{m}{5}$ with $(n, 2)$ and $(m, 5)$ in the half triangle are $(n, m) = (78, 15)$, $(n, m) = (153, 19)$ (the values $3003$ and $11628$): the complete solution of the collision equation for the column pair $(2, 5)$.
