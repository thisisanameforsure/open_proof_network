$$\forall a \in \mathbb{N}:\quad \#\bigl\{\, n \in \mathbb{N} : \exists k \ge 1,\ 2k \le n,\ \tbinom{n}{k} = a \,\bigr\} \le \lfloor \log_2 a \rfloor$$

Here $a$, $n$, $k$ are natural numbers, and $2k \le n$ is the range $1 \le k \le n/2$ written without division. The set collects **rows** $n$ of Pascal's triangle, counted once each; its size is `Set.ncard`, which is $0$ for an infinite set as well as an empty one (every such set lies in $[2, a]$, the statement spec-38faff03). The right side is `Nat.log 2 a`, the largest $m$ with $2^m \le a$; it is $0$ when $a$ is $0$ or $1$.

In words: a number $a$ appears as $\binom{n}{k}$ with $1 \le k \le n/2$ in at most $\lfloor \log_2 a \rfloor$ rows of Pascal's triangle.
