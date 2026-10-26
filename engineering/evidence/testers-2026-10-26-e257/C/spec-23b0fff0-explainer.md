## Overview

Write $F(m) = \#\{a \in A : 0 < m,\ a \mid m\}$ for the binary coefficients and $T_j = \sum_{i \ge 0} F(j+i+1)/2^{i+1}$ for the tail after position $j$. By the Lambert identity (the dependency `Opn.erdos_257_lambert_identity`, in scope through this node's Context) the hypothesis $\sum_{a\in A} 1/(2^a-1) = p/q$ reads $\sum_{m \ge 0} F(m)/2^m = p/q$. The proof splits that series at position $j$: the finite part is $\sum_{m \le j} F(m)/2^m$ and the rest is $2^{-j} T_j$. Multiplying by $q\,2^j$ and rearranging gives $q\,T_j = p\,2^j - q \sum_{m \le j} F(m)\,2^{j-m}$, which is the stated integer once the real-number identity is matched term by term with the integer expression.

## The coefficients are summable {steps: hF_le hFs hlam}

$F(m) \le m$: for $m = 0$ the counted set is empty, and for $m \ge 1$ it is a subset of the divisors of $m$, of which there are at most $m$ (hF_le). Hence $F(m)/2^m \le m/2^m$, which is summable, so $m \mapsto F(m)/2^m$ is summable (hFs). Rewriting the hypothesis through the Lambert identity gives $\sum_m F(m)/2^m = p/q$ (hlam).

## The tail in the statement is the tail of $F$ {steps: hjeq}

The statement's tail counts $\{a \in A : a \mid j+i+1\}$ without the guard $0 < j+i+1$; since $j+i+1 \ge 1$ the guard holds, so the two sets agree and the statement's tail is $T_j$ (hjeq).

## Splitting the series at $j$ {steps: hb hsplit hshift}

$q > 0$ as a real (hb). Summability lets the series be split as the finite sum over $m \le j$ plus the shifted series $\sum_{i \ge 0} F(i + (j+1))/2^{i+(j+1)}$ (hsplit), and the shifted series is $2^{-j}\,T_j$ after reindexing $i + (j+1) = j + i + 1$ and factoring $2^{j+i+1} = 2^j \cdot 2^{i+1}$ (hshift).

## Solving for $q\,T_j$ and matching the integer {steps: hb' h2j hT s11 s12}

With $q \ne 0$ and $2^j \ne 0$ (hb', h2j), clearing denominators in the split identity $\sum_{m \le j} F(m)/2^m + 2^{-j} T_j = p/q$ gives $q\,T_j = 2^j\bigl(p - q \sum_{m \le j} F(m)/2^m\bigr)$ (hT, a `linear_combination` of the cleared identity). The right side of the statement is the cast of the integer $p\,2^j - q \sum_{m \le j} F(m)\,2^{j-m}$; after pushing the cast through, the two sides agree term by term: $2^j p = p\,2^j$ (s11, `ring`), and for each $m \le j$, $2^j \cdot F(m)/2^m = F(m)\,2^{j-m}$ because $2^{j-m} = 2^j/2^m$ when $m \le j$ (s12). This closes the theorem.
