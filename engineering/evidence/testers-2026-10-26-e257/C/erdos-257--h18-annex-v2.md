# The digit method as three lemmas on this graph, and what is left for a new special case

Written by agent C of the 2026-10-26 run for whoever next attacks this hole (every infinite set outside the fifteen classes) on the affirmative side. Nothing here is new mathematics; it says where the published arguments now live on the record and exactly which step a new class of sets $A$ has to supply. (This corrects an earlier version of the same note on this node, annex 3e8b2d11, which merged before it could be withdrawn: its description of Erdős 1968 was wrong, since that proof uses no block of vanishing coefficients but the weighted divisibility described below. Read this version.)

Write $t_a = \frac{1}{2^a-1}$, $S(A) = \sum_{a \in A} t_a$, and $f_A(m) = \#\{a \in A : a \mid m\}$.

## 1. The engine, as nodes

Every published irrationality proof for this problem (Erdős 1948 for $A = \mathbb{N}$, Erdős 1968 for pairwise coprime $A$ with $\sum 1/a < \infty$, Duverney–Tachiya 2019, Tao–Teräväinen for the primes) starts the same way, and the steps are now statements of this target rather than private helpers of one proof:

- **Lambert identity** (`spec-137537c8`, proved): $S(A) = \sum_{m \ge 1} f_A(m)/2^m$ for every $A \subseteq \mathbb{N}$. The sum is a binary expansion whose digits $f_A(m)$ carry.
- **Tail integrality** (`spec-23b0fff0`): if $S(A) = p/q$ then for every $j$, with $T_j = \sum_{i \ge 1} f_A(j+i)/2^i$, $$q\,T_j = p\,2^j - q\sum_{m \le j} f_A(m)\,2^{j-m} \in \mathbb{Z}.$$ For infinite $A$ every $T_j > 0$ (some $a \in A$ exceeds $j$ and $f_A(a) \ge 1$), so $T_j \ge 1/q$ for every $j$. In the proof of `variant-c91009b9` the same quantity is $R_j = q\sum_{a\in A} w(a,j)$ with $w(a,j) = 2^{j \bmod a}/(2^a-1) = \sum_{i \ge 1,\ a \mid j+i} 2^{-i}$.
- **Block divisibility** (`spec-689ac1ac` states the per-coefficient case $2^k \mid f_A(y+i)$ for each $i \le k$; the weighted form is proposed as its own node): if moreover the weighted block sum $B = \sum_{i=1}^{k} f_A(y+i)\,2^{k-i}$ is divisible by $2^k$, then $q\,T_{y+k}$ is a multiple of $2^k$, because $2^k\,q\,T_y = q\,B + q\,T_{y+k}$. Hence $q\,T_{y+k} \ge 2^k$ for infinite $A$. Per-coefficient divisibility $2^k \mid f_A(y+i)$ for each $i$ is a special case.

So a proof of $S(A) \notin \mathbb{Q}$ by this method needs, for every $q$, one position $y$ and one length $k$ with (i) $2^k \mid B$ and (ii) the upper bound $q\,T_{y+k} < 2^k$. Step (ii) is where the arithmetic of $A$ enters, and it is never a pointwise statement about small tails: $T_j \ge 2^{-\min A}$ for every $j$ (some multiple of $\min A$ lies in any $\min A$ consecutive integers), so "the tails get arbitrarily small" never holds, and a criterion of that shape is vacuous. (A Lean proof of exactly that criterion was written during this run and discarded for this reason.)

## 2. How each known case supplies (i) and (ii)

- *Erdős 1948, $A = \mathbb{N}$* ($f = d$, the divisor function): (i) per coefficient, by the Chinese remainder theorem: $y$ is chosen in a progression so that each of $y+1, \dots, y+k$ is divisible by $k$ fresh primes to the first power, giving $2^k \mid d(y+i)$; (ii) not pointwise but on average: the mean of $T_{y+k}$ over $y$ in the progression is bounded by a polynomial in $k$ (the proof on `variant-2f5236aa` has this as `sum_dd_AP_le` and `averaging_contra`, with $15k^5 < 2^k$ as the final inequality), so some $y$ in it works.
- *Erdős 1968, pairwise coprime $A$ with $\sum 1/a < \infty$* (the proof on `variant-c91009b9`): (i) in the weighted form: the elements of $A$ up to a bound $K$ contribute a fixed residue of $B$ modulo $2^k$, and the residue is completed to $0$ by adding $r < 2^k$ further elements $b > K$ of $A$, each made to divide $y+k$ (so each contributes exactly $1$ to $B$), which pairwise coprimality turns into one Chinese-remainder condition on $y$; (ii) summability of $1/a$ makes the elements above $K$ contribute little to the tail on average over $y$ in that progression (`tail_small`, `exists_good`), giving $q\,T_{y+k} < q\,(k+4) < 2^k$.
- *Duverney–Tachiya 2019* (squarefree numbers, $k$-th powers, sums of two squares): the same two steps for a coefficient function with divisibility along a sequence of pairwise coprime integers $e_n \le n^\mu$.
- *Tao–Teräväinen* (primes, $f = \omega$): (ii) needs quantitative correlation estimates for $\omega$ on short intervals; the engine is the same, with deep input at step (ii).

## 3. What a new class has to bring

A route on this hole for a new class of sets $A$ is therefore one lemma: **for every $k$ (or every $q$), a position $y$ with $2^k \mid \sum_{i=1}^k f_A(y+i)\,2^{k-i}$ and $q\,T_{y+k} < 2^k$**. Candidates the literature names but the record does not hold:

- Erdős's own remark (1968) that coprimality can be dropped: the record's `variant-c91009b9` keeps it. Without coprimality the Chinese-remainder conditions "$b \mid y+k$ for the $r$ added elements" need not be simultaneously solvable, and the count of residues excluded by the small elements is no longer a product; a weaker sufficient condition on $A$ (for instance, pairwise coprimality only among elements above every bound) is the natural first target.
- Sets with $n_{k+1} - n_k \to \infty$, which Erdős (1968, p. 226) expected to give irrational sums: no published proof is known to the writer.

What this engine cannot touch is the open core `erdos-257--h2--h1`: there $A$ is the greedy set of a rational $r$, which has density about $1/2$ and no arithmetic structure to steer a Chinese-remainder choice, and the tails $T_j$ of such a set are bounded below as above. The affirmative side of the open core needs an idea about the walk, not about digits.
