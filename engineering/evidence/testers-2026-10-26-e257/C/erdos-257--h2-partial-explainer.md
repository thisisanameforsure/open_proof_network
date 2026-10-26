## Overview

Write $t_n = \frac{1}{2^n-1}$ for $n \ge 1$. The statement says: if $0 \notin G$, $G$ is the greedy set of a rational $r$ (for every $n \ge 1$, $n \in G$ exactly when $t_n \le r - \sum_{a \in G,\ a < n} t_a$), and $\sum_{a \in G} t_a = r$, then $G$ is finite. The partial proof splits on the shape of $G$. Its one hole says a greedy set of a rational is finite or co-finite; the assembly closes the finite case at once and rules out the co-finite case with Erdős's 1948 theorem that $\sum_{n \ge 1} t_n$ is irrational, whose Lean proof (the proof of variant-2f5236aa) is carried in the file as private helper lemmas. What is left open is therefore exactly the case of a greedy set that is infinite and co-infinite, and the hole states it with no infinite sum in its hypotheses.

## The hole: a rational's greedy set is finite or co-finite {steps: h_walk}

The hole h_walk is the statement: for every rational $r$ and every $G \subseteq \mathbb{N}$ with $0 \notin G$ that is greedy for $r$ in the sense above, $G$ is finite or its complement $\mathbb{N} \setminus G$ is finite. It is left as sorry and became the node erdos-257--h2--h1. It has one hypothesis fewer than the statement being proved: nothing is assumed about the value of $\sum_{a \in G} t_a$. (That is no loss: a co-infinite greedy set always sums to $r$, since at every skipped $n$ the remainder $r - \sum_{a \in G,\ a<n} t_a$ is below $t_n$, never increases and never goes negative, so it tends to $0$; so the hole is equivalent to the statement it decomposes. The partial does not use this converse.)

## The finite case {steps: s2}

After introducing $r$, $G$, the hypotheses $0 \notin G$, greediness and $\sum_{a\in G} t_a = r$, the assembly applies h_walk to $r$ and $G$ and takes the two cases apart. In the first, $G$ is finite, which is the goal.

## The co-finite case: Erdős 1948 {steps: s3}

In the second case the complement of $G$ is finite, and the helper lemma o_cofinite derives a contradiction from this together with $\sum_{a \in G} t_a = r$. The terms $t_n$ are nonnegative and at most $2 \cdot 2^{-n}$, so the family $(t_n)_{n \in \mathbb{N}}$ is summable (Lean's $t_0 = \frac{1}{0} = 0$), and the sum over $\mathbb{N}$ splits as the sum over $G$ plus the sum over its complement. The complement is a finite set $F$, so its sum is the finite sum $\sum_{n \in F} t_n$, a rational number (each $t_n$ is the real image of the rational $\frac{1}{2^n-1}$). Hence
$$\sum_{n \ge 0} \frac{1}{2^n-1} \;=\; r + \sum_{n \in F} \frac{1}{2^n-1}$$
is rational. But the helper o_erdos1948 says this sum is irrational: it is Erdős's 1948 theorem for $A = \mathbb{N}$, proved in the file by the Lambert identity $\sum_{n \ge 1} \frac{1}{2^n-1} = \sum_{n \ge 1} \frac{d(n)}{2^n}$ ($d$ the number of divisors) followed by the Chinese-remainder argument that the binary expansion $\sum d(n) 2^{-n}$ is not eventually periodic, the same proof that closed variant-2f5236aa. The contradiction closes the case, so $G$ is finite.
