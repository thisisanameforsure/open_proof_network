$$\forall n, m \in \mathbb{N}:\quad 4 \le n \to 6 \le m \to \tbinom{n}{2} = \tbinom{m}{3} \to (n, m) = (16, 10) \vee (n, m) = (56, 22) \vee (n, m) = (120, 36)$$

Here $n$, $m$ are natural numbers; the bounds $4 \le n$ and $6 \le m$ are the half-triangle conditions $2 \cdot 2 \le n$ and $2 \cdot 3 \le m$ for the fixed columns $k = 2$, $l = 3$. The conclusion is written in the Lean as a disjunction of conjunctions of equalities.

In words: the only solutions of $\binom{n}{2} = \binom{m}{3}$ with $(n, 2)$ and $(m, 3)$ in the half triangle are $(n, m) = (16, 10)$, $(n, m) = (56, 22)$, $(n, m) = (120, 36)$ (the values $120$, $1540$, $7140$): the complete solution of the collision equation for the column pair $(2, 3)$.
