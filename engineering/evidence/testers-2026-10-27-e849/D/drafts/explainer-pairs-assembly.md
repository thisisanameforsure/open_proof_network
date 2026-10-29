## Overview

The statement (hole `h_pairs` of the level-2 partial on --h2--h1) says that a collision $\binom{n}{k} = \binom{m}{l}$ in the half triangle with $k < l$ and $(k, l)$ among the nine solved column pairs $(2,3), (2,4), (2,5), (2,6), (2,8), (3,4), (3,6), (4,6), (4,8)$ is one of the eight sporadic collisions. The assembly is a case split over the nine pairs: for each pair, the published complete solution of that pair's equation, restricted to the half triangle, is a hole, and the sporadic disjunction is then checked by computation.

## The nine holes {steps: hall s2}

One conjunction `hall` states the nine holes, each with a `sorry` body. For the five pairs with solutions, the hole lists them: $(2,3)$ gives $(n, m) \in \{(16,10), (56,22), (120,36)\}$ (Avanesov 1966); $(2,4)$ gives $(21, 10)$ (Pintér 1995, de Weger 1996); $(2,5)$ gives $(78, 15)$ or $(153, 19)$ (Bugeaud–Mignotte–Siksek–Stoll–Tengely 2008); $(2,6)$ gives $(78, 14)$ and $(2,8)$ gives $(221, 17)$ (Stroeker–de Weger 1999). For the four pairs $(3,4)$, $(3,6)$, $(4,6)$, $(4,8)$ the hole says the two binomial coefficients are never equal in the half triangle (Mordell 1963 for $(3,4)$; Stroeker–de Weger 1999 for the rest). Each hole carries the half-triangle bounds $2k \le n$ and $2l \le m$ as its only hypotheses besides the equation.

## The case split {steps: s3 s4 s5 s6 s7 s8 s9 s10 s11}

The conjunction is taken apart into the nine named facts, the four numbers and the hypotheses are introduced, and the disjunction naming the pair is split into its nine cases, each substituting the values of $k$ and $l$. In the five cases with solutions, the pair's hole applied to the collision yields the possible $(n, m)$; each is substituted, and `decide` checks that the resulting quadruple is one of the eight listed (for instance $(16, 2, 10, 3)$ in the $(2,3)$ case). In the four cases without solutions, the pair's hole contradicts the collision directly (`absurd`).
