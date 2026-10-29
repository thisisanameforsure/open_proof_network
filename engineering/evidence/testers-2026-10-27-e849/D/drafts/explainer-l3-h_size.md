## Overview

The statement (hole `h_size` of the third-level partial on --h3--h1) bounds the size of a position $(n, k)$ of the half triangle in terms of its value $a = \binom{n}{k}$: always $\log a \le k \log n$; for $k \ge 3$, $k \le 2 \log a$; and for an interior position, $e^{(\log n)^{5/6}} \le k$, both $k \ge 3$ and $\log n \le (\log k)^{6/5}$. It is the elementary bookkeeping (1.5), (1.7) of Matomäki–Radziwiłł–Shao–Tao–Teräväinen in the form the distance estimate needs. One private lemma precedes the theorem and is no step of the outline: `e849_two_pow_le_choose`, $2^k \le \binom{n}{k}$ for $k \ge 3$ and $2k \le n$, from Mathlib's $4^k \le (2k+1)\binom{2k}{k}$, the inequality $2k + 1 \le 2^k$ for $k \ge 3$, and the monotonicity $\binom{2k}{k} \le \binom{n}{k}$ in the upper index.

## Setting up {steps: hn2 ha0}

After introducing $a$, $n$, $k$ and the three hypotheses, two facts are recorded for the real-number work: $n \ge 2$ as a real (from $1 \le k$ and $2k \le n$), and $a > 0$ (since $\binom{n}{k} > 0$ for $k \le n$). The conclusion is a conjunction of three claims, proved one by one.

## The first claim {steps: s3}

$\log a \le k \log n$: by Mathlib's `Nat.choose_le_pow`, $a = \binom{n}{k} \le n^k$; casting to $\mathbb{R}$ and taking logarithms (`Real.log_le_log`, valid as $a > 0$) gives $\log a \le \log(n^k) = k \log n$.

## The second claim {steps: s4}

If $k \ge 3$ then $k \le 2 \log a$: the private lemma gives $2^k \le a$; taking logarithms, $k \log 2 \le \log a$; and $\log 2 > 1/2$ (from Mathlib's decimal bound `Real.log_two_gt_d9`), so $k \le 2 \log a$ by `linarith`.

## The third claim {steps: s5}

Assume the interior condition $e^{(\log n)^{5/6}} \le k$. First $k \ge 3$: since $n \ge 2$, $\log n \ge \log 2$, and as $0 < \log 2 < 1$ (the decimal bounds on $\log 2$) and $5/6 < 1$, $(\log n)^{5/6} \ge (\log 2)^{5/6} > \log 2$, so $k \ge e^{(\log n)^{5/6}} > e^{\log 2} = 2$, giving $k \ge 3$ as a natural number. Then $\log n \le (\log k)^{6/5}$: taking logarithms of the interior condition gives $(\log n)^{5/6} \le \log k$ (as $\log n \ge 0$), and raising both sides to the power $6/5$ (`Real.rpow_le_rpow`) gives $\log n = ((\log n)^{5/6})^{6/5} \le (\log k)^{6/5}$.
