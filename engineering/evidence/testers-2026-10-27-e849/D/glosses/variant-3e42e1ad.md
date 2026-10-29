$$\forall N \in \mathbb{N}:\quad \Bigl(\exists a \ge N,\ \#\bigl\{\, n \in \mathbb{N} : \exists k \ge 1,\ 2k \le n,\ \tbinom{n}{k} = a \,\bigr\} = 1\Bigr) \ \wedge\ \Bigl(\exists a \ge N,\ \#\bigl\{\, n \in \mathbb{N} : \exists k \ge 1,\ 2k \le n,\ \tbinom{n}{k} = a \,\bigr\} = 2\Bigr)$$

Here $N$, $a$, $n$, $k$ are natural numbers, and $2k \le n$ is the range $1 \le k \le n/2$ written without division. Each set collects **rows** $n$ of Pascal's triangle, counted once each; its size is `Set.ncard`, which is $0$ for an infinite set as well as an empty one (every such set lies in $[2, a]$, the statement spec-38faff03). The two $a$ are chosen separately: the first conjunct has its own $a$, the second its own.

In words: for every $N$ there is some $a \ge N$ that appears as $\binom{n}{k}$ with $1 \le k \le n/2$ in exactly one row, and some $a \ge N$ that appears in exactly two rows. That is, the cases $t = 1$ and $t = 2$ of erdos-849 are each attained by infinitely many $a$.
