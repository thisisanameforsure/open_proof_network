## Overview

Write $e_m = \frac{1}{2^m-1}$ (in Lean $e_0 = \frac10 = 0$) and $T_m = \sum_{k\ge0} e_{k+m}$ for the tail of the series from $m$ on. Let $r$ be any sequence with $r_0 = \frac12$ and $r_{m+1} = r_m - e_m$ if $e_m \le r_m$ (step $m$ is taken), else $r_{m+1} = r_m$ (step $m$ is skipped). The statement: $r_m \le T_m$ for every $m$. The proof shows that the bound follows from the walk skipping infinitely often, and leaves that as its one hole.

**The hole.** For every $r$ obeying the recursion from $\frac12$: for every $m$ there is $n > m$ with $r_n < e_n$. It is left open (node spec-a70fcca4--h4--h2). In words, the set of taken steps is not co-finite.

**Convergence and the tail (`e_nonneg`, `e_le`, `e_summable`, `tail_summable`).** Every term is nonnegative, since $2^n \ge 1$. For $n \ge 1$, $2^n - 1 \ge 2^{n-1}$, so $e_n \le 2\cdot(\tfrac12)^n$, and at $n = 0$ the term is $0 \le 2$. Comparison with the geometric series shows $\sum_n e_n$ converges, and so does every shifted series $k \mapsto e_{k+m}$.

**The tail identity and the term below the tail (`tail_succ`, `e_le_tail`).** Splitting off the first term of the shifted series gives $T_m = e_m + T_{m+1}$. Since $T_{m+1} \ge 0$, this gives $e_m \le T_m$.

**The run lemma (`hrun`).** Suppose, for a contradiction, that $T_m < r_m$ for some $m$. Then $T_{m+k} < r_{m+k}$ for every $k$, by induction on $k$: given $T_{m+k} < r_{m+k}$, the step $m+k$ is taken because $e_{m+k} \le T_{m+k} < r_{m+k}$, so $r_{m+k+1} = r_{m+k} - e_{m+k} > T_{m+k} - e_{m+k} = T_{m+k+1}$ by the tail identity.

**The close.** The hole gives a skipped $n > m$, that is $r_n < e_n$. Writing $n = m + k$, the run lemma gives $T_n < r_n$, while $e_n \le T_n$; so $r_n < e_n \le T_n < r_n$, a contradiction.
