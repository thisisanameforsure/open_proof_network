## Overview

The statement (hole `h_dw` of the partial on --h2) is de Weger's conjecture: every collision $\binom{n}{k} = \binom{m}{l}$ in the half triangle with $k < l$ is one of eight sporadic ones or lies in Lind's adjacent-row family. The assembly splits it into what Blokhuis–Brouwer–de Weger's Theorem 2.2 proves and one open remainder: the nine solved column pairs, the adjacent shape $(m, l) = (n-1, k+1)$, and the rows $n \le 10^6$, each a hole stated as the published result; the fourth hole, the open core, says every collision falls in one of those three cases. The assembly is the case split.

## The four holes {steps: hall s2}

`hall` states the four holes as one conjunction, each with a `sorry` body: `h_pairs` — a collision whose columns $(k, l)$ are among $(2,3), (2,4), (2,5), (2,6), (2,8), (3,4), (3,6), (4,6), (4,8)$ is one of the eight sporadic quadruples; `h_adjacent` — a collision with $m + 1 = n$ and $l = k + 1$ lies in Lind's family $(n, k) = (F_{2i+2}F_{2i+3}, F_{2i}F_{2i+3})$, $i \ge 1$; `h_small` — a collision with $n \le 10^6$ is sporadic or in Lind's family; and `h_open` — every collision has its columns among the nine pairs, or the adjacent shape, or $n \le 10^6$. The conjunction is taken apart into the four named facts.

## The case split {steps: s3 s4 s5}

Given a collision with its six hypotheses, `h_open` says which case it is in. In the first case the columns are among the nine pairs and `h_pairs` gives a sporadic quadruple, the left disjunct of the conclusion. In the second the shape is adjacent and `h_adjacent` gives the Lind index, the right disjunct. In the third $n \le 10^6$ and `h_small` gives the whole conclusion directly.
