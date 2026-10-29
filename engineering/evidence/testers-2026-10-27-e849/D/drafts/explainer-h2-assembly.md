## Overview

The statement to prove is the middle case of Singmaster's conjecture in row form: there are $K$ and $B$ such that every $a$ lies in at most $B$ rows $n$ of the half triangle at a column $k$ with $K < k < e^{(\log n)^{5/6}}$. The assembly takes the route of Matomäki–Radziwiłł–Shao–Tao–Teräväinen's Remark 1.5: de Weger's collision conjecture is assumed as the one hole, and from it the bound follows with $K = 1$ and $B = 17$ by elementary counting. The real-valued threshold plays no role in the argument: the hole is used for every pair of rows with columns $\ge 2$, whatever their size.


Three private lemmas precede the theorem (they are not steps of the outline). `choose_lt_succ_n`: $\binom{n}{j+1} < \binom{n+1}{j+1}$ for $j \le n$, by Pascal's rule and $\binom{n}{j} > 0$. `choose_strict_n`: for a fixed column $j+1$, $\binom{n}{j+1} < \binom{m}{j+1}$ whenever $j \le n < m$, by induction on $m$. `row_unique`: two rows $n, m$ of the half triangle holding the same value at the same column $k \ge 1$ are the same row, since otherwise the strict monotonicity in the row gives a strict inequality between the two equal values.

## The hole {steps: h_dw}

`h_dw` is de Weger's conjecture (Blokhuis–Brouwer–de Weger, Conjecture 2.1) stated as a hypothesis, with a `sorry` body: every collision $\binom{n}{k} = \binom{m}{l}$ with $2 \le k \le n/2$, $2 \le l \le m/2$ and $k < l$ is one of eight listed sporadic quadruples (the values $3003$ twice, $120$, $210$, $1540$, $7140$, $11628$, $24310$) or lies in Lind's adjacent-row family $n = F_{2i+2}F_{2i+3}$, $k = F_{2i}F_{2i+3}$, $m = n - 1$, $l = k + 1$ for some $i \ge 1$.

## Two middle rows are both sporadic or adjacent {steps: hScard pair}

With $K = 1$ and $B = 17$ chosen (`refine ⟨1, 17, …⟩`), fix $a$ and let $M$ be its set of middle rows: rows $n$ with a column $k > 1$ below the threshold, $2k \le n$ and $\binom{n}{k} = a$. Let $S$ be the finite set of the fourteen row numbers occurring in the sporadic list, $\{78, 15, 14, 16, 10, 21, 56, 22, 120, 36, 153, 19, 221, 17\}$ (its size is at most $14$, checked by `decide`). The lemma `pair` says: two distinct rows $x, y \in M$ are either both in $S$, or adjacent ($y + 1 = x$ or $x + 1 = y$). Indeed their columns $k_x, k_y$ differ, by `row_unique`; whichever is smaller, `h_dw` applied to the two positions (in the order that makes $k < l$) says the collision is sporadic — in which case both row numbers are in $S$, read off from the listed quadruple by `simp` — or in Lind's family, in which case the rows are adjacent ($m + 1 = n$).

## Counting {steps: s4 s5}

If $M \subseteq S$, then $\#M \le \#S \le 14 \le 17$ (`Set.ncard_le_ncard` and `Set.ncard_coe_finset`). Otherwise pick $x \in M \setminus S$ and let $T = \{x - 1, x, x + 1\}$, of size at most $3$. Every $y \in M$ is in $S \cup T$: for $y = x$ this is clear, and for $y \ne x$, `pair` rules out the sporadic case (as $x \notin S$) and leaves $y$ adjacent to $x$, hence in $T$ (`omega`). So $\#M \le \#(S \cup T) \le \#S + \#T \le 14 + 3 = 17$ (`Finset.card_union_le`). In both cases $\#M \le 17 = B$, which proves the statement.
