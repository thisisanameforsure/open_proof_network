$$\forall n, k, m, l \in \mathbb{N}:\quad 2 \le k \to 2k \le n \to 2 \le l \to 2l \le m \to k < l \to \tbinom{n}{k} = \tbinom{m}{l} \to (k, l) \in P\ \vee\ (m + 1 = n \wedge l = k + 1)\ \vee\ n \le 10^6\ \vee\ \tbinom{n}{k} \le 10^{60}$$

where $P = \{(2,3), (2,4), (2,5), (2,6), (2,8), (3,4), (3,6), (4,6), (4,8)\}$, written in the Lean as a disjunction of conjunctions of equalities. Here $n$, $k$, $m$, $l$ are natural numbers.

In words: every collision $\binom{n}{k} = \binom{m}{l}$ in the half triangle with $k < l$ has its columns among the nine listed pairs, or is an adjacent-row collision ($m = n - 1$, $l = k + 1$), or has $n \le 10^6$, or has value at most $10^{60}$. Stated positively, this is de Weger's conjecture with the four cases that are proved set aside: it says nothing about which collisions occur in those cases, only that no collision lies outside them.
