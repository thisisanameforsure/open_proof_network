$$\forall a, n, k \in \mathbb{N}:\quad 1 \le k \to 2k \le n \to \tbinom{n}{k} = a \to \Bigl(\log a \le k \log n\Bigr) \wedge \Bigl(3 \le k \to k \le 2\log a\Bigr) \wedge \Bigl(e^{(\log n)^{5/6}} \le k \to 3 \le k \wedge \log n \le (\log k)^{6/5}\Bigr)$$

Here $a$, $n$, $k$ are natural numbers; $\log$ is the natural logarithm of the number cast to $\mathbb{R}$ (so $\log 0 = 0$ in Lean), and every inequality except $1 \le k$, $2k \le n$ and $3 \le k$ is in $\mathbb{R}$ after casting; the powers are real powers.

In words: for a position $(n, k)$ of the half triangle with $\binom{n}{k} = a$: $\log a \le k \log n$ always; if $k \ge 3$ then $k \le 2 \log a$; and if $(n, k)$ lies in the interior region $e^{(\log n)^{5/6}} \le k$, then $k \ge 3$ and $\log n \le (\log k)^{6/5}$. This is the size bookkeeping of Matomäki–Radziwiłł–Shao–Tao–Teräväinen's (1.5) and (1.7) in the form the distance estimate needs.
