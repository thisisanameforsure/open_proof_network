## Overview

The statement to prove is the interior case of Singmaster's conjecture in row form: there is an $a_0$ such that every $a \ge a_0$ lies in at most two rows $n$ of the half triangle at a column $k$ with $e^{(\log n)^{5/6}} \le k \le n/2$. The assembly follows the deduction of Theorem 1.3 in Matomäki–Radziwiłł–Shao–Tao–Teräväinen (Quart. J. Math. 73, 2022, §1.2): two deep inputs are left as holes, and the elementary bookkeeping around them is proved here.

## The two holes {steps: hall s2 ha1 ha2}

The assembly first states, as one conjunction `hall`, the two facts it will use, each as its own hole with a `sorry` body: `h_dist`, the distance estimate — there is $a_1$ such that for $a \ge a_1$ any two interior solutions $(n, k)$, $(n', k')$ of $\binom{n}{k} = a$ satisfy $|n - n'| + |k - k'| \le e^{(\log\log a)^{9/10}}$ (the paper's bound (1.10), from its Proposition 1.9 with (1.5) and (1.7)); and `h_kane`, the Kane-type estimate — there is $a_2$ such that for $a \ge a_2$ and an interior solution $(n, k)$, at most one row $n' > n$ holds $a$ at a column $k' < k$ of the half triangle within that distance (the paper's Proposition 1.10). The conjunction is then taken apart (`obtain`) into $a_1$, $a_2$ and the two statements, and $a_0 := \max(a_1, a_2)$ is chosen, so that both apply to every $a \ge a_0$.

## Elementary facts about rows {steps: key hstrict hhalf hkk}

Three lemmas are proved inline for the fixed $a$. `key`: a row $n$ holding $a$ at a column $1 \le k \le n/2$ has $n \le a$, because $n = \binom{n}{1} \le \binom{n}{k}$ (the binomial coefficient increases along the first half of a row, by induction on the column using `Nat.choose_le_succ_of_lt_half_left`). `hstrict`: for a fixed column $j + 1 \ge 1$, $\binom{n}{j+1} < \binom{m}{j+1}$ whenever $j \le n < m$, by induction on $m$ through Pascal's rule $\binom{m+1}{j+1} = \binom{m}{j+1} + \binom{m}{j}$ with $\binom{m}{j} > 0$. `hhalf`: along one row, $\binom{n}{i} \le \binom{n}{j}$ for $i \le j \le n/2$, again by induction on $j$. From these, `hkk` is the maximal-column step of the paper: if two rows $n < n'$ of the half triangle both hold $a$, at columns $k$ and $k'$, then $k' < k$; for if $k' \ge k$ then $\binom{n}{k} < \binom{n'}{k} \le \binom{n'}{k'}$, contradicting equality of both with $a$.

## Finiteness and the count {steps: hSfin main}

Let $S$ be the set of interior rows of $a$. By `key` it lies in $\{0, \dots, a\}$, so it is finite (`hSfin`), and its `Set.ncard` is its true size. The claim `main` is that three distinct interior rows $x < y$, $x < z$, $y \ne z$ are impossible. Fix the columns $k_x, k_y, k_z$ witnessing membership. Let $T$ be the set `h_kane` bounds for the solution $(x, k_x)$: rows $n' > x$ holding $a$ at some $k' < k_x$ of the half triangle within distance $e^{(\log\log a)^{9/10}}$ of $(x, k_x)$. Both $y$ and $z$ lie in $T$: they are later rows, their columns are smaller by `hkk`, and the distance bound is `h_dist` applied to the two interior solutions. $T$ is finite by `key` once more, so two distinct members give $1 < \#T$ (`Set.one_lt_ncard_iff`), while `h_kane` gives $\#T \le 1$; `omega` closes the contradiction.

## Closing {steps: s11 close}

Suppose, for contradiction, that $\#S > 2$. Then `Set.two_lt_ncard_iff` yields three pairwise distinct rows $x, y, z$ in $S$. Whichever of them is the smallest, `main` applied with that row first (the three orderings are tried in turn, with `omega` supplying the inequalities) gives `False`. Hence $\#S \le 2$ for every $a \ge \max(a_1, a_2)$, which is the statement.
