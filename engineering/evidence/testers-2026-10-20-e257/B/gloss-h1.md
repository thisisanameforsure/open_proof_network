$$0 \le r_m \quad\text{and}\quad \sum_{a<m,\ a\in A} \frac{1}{2^a-1} = \frac12 - r_m \quad\text{for every } m,\ \text{where } A=\Bigl\{a : \tfrac{1}{2^a-1}\le r_a\Bigr\}.$$

Bookkeeping for the greedy walk to one half. Here $r$ is any sequence with $r_0 = \tfrac12$ and $r_{m+1} = r_m - \tfrac{1}{2^m-1}$ when that term fits under $r_m$, else $r_{m+1} = r_m$. The remainder never goes negative (a term is subtracted only when it fits) and is exactly one half minus the sum of the terms taken so far. Induction on $m$. (The $a = 0$ term is Lean's $0$, taken at no cost.)
