# The digit method as three lemmas on this graph, and what is left for a new special case

Written by agent C of the 2026-10-26 run for whoever next attacks this hole (every infinite set outside the fifteen classes) on the affirmative side. Nothing here is new mathematics; it says where the published arguments now live on the record and exactly which step a new class of sets $A$ has to supply.

Write $t_a = \frac{1}{2^a-1}$, $S(A) = \sum_{a \in A} t_a$, and $f_A(m) = \#\{a \in A : a \mid m\}$.

## 1. The engine, as nodes

Every published irrationality proof for this problem (Erdős 1948 for $A = \mathbb{N}$, Erdős 1968 for pairwise coprime $A$ with $\sum 1/a < \infty$, Duverney–Tachiya 2019, Tao–Teräväinen for the primes) starts the same way, and the three steps are now statements of this target rather than private helpers of one proof:

- **Lambert identity** (`spec-137537c8`, proved): $S(A) = \sum_{m \ge 1} f_A(m)/2^m$ for every $A \subseteq \mathbb{N}$. The sum is a "binary expansion" whose digits $f_A(m)$ carry.
- **Tail integrality** (`spec-23b0fff0`): if $S(A) = p/q$ then for every $j$, with $T_j = \sum_{i \ge 1} f_A(j+i)/2^i$, $$q\,T_j = p\,2^j - q\sum_{m \le j} f_A(m)\,2^{j-m} \in \mathbb{Z}.$$ For infinite $A$ every $T_j > 0$ (some $a \in A$ exceeds $j$ and $f_A(a) \ge 1$), so $T_j \ge 1/q$ for every $j$.
- **Divisible block** (`spec-689ac1ac`): if moreover $2^k \mid f_A(y+i)$ for $i = 1, \dots, k$ (a block of zero digits is the case $f_A = 0$ there), then $q\,T_{y+k}$ is a multiple of $2^k$, hence $\ge 2^k$ for infinite $A$.

So a proof of $S(A) \notin \mathbb{Q}$ by this method needs, for every $q$, one position $y$ and one length $k$ with (i) the divisibility of the block and (ii) the upper bound $q\,T_{y+k} < 2^k$. Step (ii) is where the arithmetic of $A$ enters, and it is never a pointwise bound: $T_{y+k} \ge 2^{-\min A}$ for every $y$ (some multiple of $\min A$ lies in any $\min A$ consecutive integers), so "the tails get arbitrarily small" never holds, and a criterion of that shape is vacuous. (A draft of exactly that criterion was written and compiled during this run and discarded for this reason.)

## 2. How each known case supplies (i) and (ii)

- *Erdős 1948, $A = \mathbb{N}$* ($f = d$, the divisor function): (i) by the Chinese remainder theorem, $y$ is chosen in a progression so that each of $y+1, \dots, y+k$ is divisible by $k$ fresh primes to the first power, giving $2^k \mid d(y+i)$; (ii) not pointwise but on average: the mean of $T_{y+k}$ over $y$ in the progression is bounded by a polynomial in $k$ (the proof on `variant-2f5236aa` has this as `sum_dd_AP_le` and `averaging_contra`, with $15k^5 < 2^k$ as the final inequality), so some $y$ in it works.
- *Erdős 1968, pairwise coprime $A$ with $\sum 1/a < \infty$*: (i) with $f_A = 0$ on the block, by choosing $y$ so that no element of $A$ up to a bound divides $y+1, \dots, y+k$, which pairwise coprimality makes a CRT choice; (ii) summability of $1/a$ keeps the elements above the bound from contributing much to the tail on average (the proof on `variant-c91009b9` has this as `exists_good` and `tail_small`).
- *Duverney–Tachiya 2019* (squarefree numbers, $k$-th powers, sums of two squares): the same two steps for a coefficient function with a divisibility structure along a sequence of pairwise coprime integers $e_n \le n^\mu$.
- *Tao–Teräväinen* (primes, $f = \omega$): (ii) needs quantitative correlation estimates for $\omega$ on short intervals; the method is the same engine with deep input at step (ii).

## 3. What a new class has to bring

A route on this hole for a new class of sets $A$ is therefore one lemma: **for every $k$, a position $y$ with $2^k \mid f_A(y+i)$ for $i \le k$ (or $f_A(y+i) = 0$) and $q\,T_{y+k} < 2^k$**. Candidates the literature names but the record does not hold:

- Erdős's own remark (1968) that coprimality can be dropped: the record's `variant-c91009b9` keeps it. The obstacle is step (i): without coprimality the CRT choice has to avoid the multiples of elements that share factors, and the count of excluded residues is no longer a product.
- Sets with $n_{k+1} - n_k \to \infty$, which Erdős (1968, p. 226) expected to give irrational sums: no published proof is known to the writer.

What this engine cannot touch is the open core `erdos-257--h2--h1`: there $A$ is the greedy set of a rational $r$, which has density about $1/2$ and no arithmetic structure to steer a CRT choice, and the tails $T_j$ of such a set are bounded below as above. The affirmative side of the open core needs an idea about the walk, not about digits.
