## Overview

The statement (hole `h_open` of the partial on --h2--h1) says every collision $\binom{n}{k} = \binom{m}{l}$ in the half triangle with $k < l$ has its columns among the nine solved pairs, or the adjacent shape $(m, l) = (n-1, k+1)$, or $n \le 10^6$. The assembly peels off the last proved case of Blokhuis–Brouwer–de Weger's Theorem 2.2, the collisions of value at most $10^{60}$, as a hole, and leaves the open core as the other: every collision has its columns among the nine pairs, or the adjacent shape, or $n \le 10^6$, or value at most $10^{60}$.

## The two holes {steps: hall s2}

`hall` states them as one conjunction, each with a `sorry` body: `h_value` — a collision with $\binom{n}{k} \le 10^{60}$ is one of the eight sporadic quadruples or lies in Lind's family; and `h_core` — every collision has its columns among the nine pairs, or satisfies $m + 1 = n$ and $l = k + 1$, or has $n \le 10^6$, or has value at most $10^{60}$. The conjunction is taken apart into the two facts.

## The case split {steps: s3 s4 s5 s6}

Given a collision, `h_core` says which of its four cases holds. The first three are the three disjuncts of the conclusion and are passed through. In the fourth, the value is at most $10^{60}$, and `h_value` says the collision is sporadic or in Lind's family: a sporadic quadruple has $n \le 221 \le 10^6$ (checked by `omega` on each of the eight), and a Lind member has $m + 1 = n$ and $l = k + 1$, the adjacent shape.
