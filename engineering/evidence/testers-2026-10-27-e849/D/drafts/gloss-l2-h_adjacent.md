$$\forall n, k, m, l \in \mathbb{N}:\quad 2 \le k \to 2k \le n \to 2 \le l \to 2l \le m \to k < l \to \tbinom{n}{k} = \tbinom{m}{l} \to m + 1 = n \to l = k + 1 \to \exists i \ge 1:\ n = F_{2i+2}F_{2i+3}\ \wedge\ k = F_{2i}F_{2i+3}\ \wedge\ m + 1 = n\ \wedge\ l = k + 1$$

Here $n$, $k$, $m$, $l$, $i$ are natural numbers and $F_j$ is `Nat.fib` ($F_0 = 0$, $F_1 = 1$). The last two conjuncts of the conclusion restate two of the hypotheses, so the content is the existence of $i$.

In words: an adjacent-row collision $\binom{n}{k} = \binom{n-1}{k+1}$ in the half triangle, with $2 \le k$, $2k \le n$ and $2(k+1) \le n - 1$, has $(n, k) = (F_{2i+2}F_{2i+3}, F_{2i}F_{2i+3})$ for some $i \ge 1$: every such collision lies in Lind's family ($i = 1$ gives $\binom{15}{5} = \binom{14}{6} = 3003$, $i = 2$ gives $\binom{104}{39} = \binom{103}{40}$).
