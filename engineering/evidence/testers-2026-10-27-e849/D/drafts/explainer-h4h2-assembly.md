## Overview

The statement (hole `h_core` of the partial on --h2--h1--h4) says every collision $\binom{n}{k} = \binom{m}{l}$ in the half triangle with $k < l$ has its columns among the nine solved pairs, or the adjacent shape $(m, l) = (n-1, k+1)$, or $n \le 10^6$, or value at most $10^{60}$. The assembly peels off the last proved case of Blokhuis–Brouwer–de Weger's Theorem 2.2, Stroeker–de Weger's result that there are no collisions of the shapes $(n-1, k+2)$ and $(n-2, k+1)$, as two holes, and leaves the open core as the third: every collision falls in one of the previous four cases or has one of those two shapes.

## The three holes {steps: hall s2}

`hall` states them as one conjunction, each with a `sorry` body: `h_shape12` — for $k \ge 2$ and $2(k+2) \le n - 1$, $\binom{n}{k} \ne \binom{n-1}{k+2}$; `h_shape21` — for $k \ge 2$ and $2(k+1) \le n - 2$, $\binom{n}{k} \ne \binom{n-2}{k+1}$; and `h_core` — every collision has its columns among the nine pairs, or the shape $(n-1, k+1)$, or $n \le 10^6$, or value at most $10^{60}$, or one of the shapes $(n-1, k+2)$, $(n-2, k+1)$. The conjunction is taken apart into the three facts.

## The case split {steps: s3 s4 s5 s6 s7 s8}

Given a collision, `h_core` says which of its six cases holds. The first four are the four disjuncts of the conclusion and are passed through. In the fifth, $m = n - 1$ and $l = k + 2$, and the half-triangle condition $2l \le m$ gives the hypothesis of `h_shape12`, which contradicts the collision; the sixth case, $m = n - 2$ and $l = k + 1$, is contradicted the same way by `h_shape21`.
