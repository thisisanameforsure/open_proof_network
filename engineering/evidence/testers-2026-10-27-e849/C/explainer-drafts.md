# Explainer drafts for C's two third-level proofs (for D to file once merged; anchors to be set from the outline)

## h_size (size of an interior solution)
Let $(n,k)$ be an interior solution: $1 \le k$, $e^{(\log n)^{5/6}} \le k$, $2k \le n$, $\binom{n}{k} = a$.
1. $k \ge 3$. Since $n \ge 2$, $\log n \ge \log 2$, so $(\log n)^{5/6} \ge (\log 2)^{5/6} > \log 2$ (because $0 < \log 2 < 1$ and $5/6 < 1$). Hence $k \ge e^{(\log n)^{5/6}} > e^{\log 2} = 2$.
2. $k \le 2 \log a$. For $k \ge 3$, $2k+1 \le 2^k$, and Mathlib's $4^k \le (2k+1)\binom{2k}{k}$ gives $2^k \le \binom{2k}{k} \le \binom{n}{k} = a$ (monotone in $n$). So $k \log 2 \le \log a$ and $\log 2 > 1/2$.
3. $\log a \le k \log n$: $\binom{n}{k} \le n^k$.
4. $\log n \le (\log k)^{6/5}$: take logs of the threshold, $(\log n)^{5/6} \le \log k$, and raise both sides to the power $6/5$.

## h_absorb (the implied constant is absorbed)
Given $C$, take $X_0 = \max(10^{25}, C^2)$ and $X \ge X_0$; write $r = X^{43/50}$.
1. Bracket: $X+1 \le 2X$, so $(X+1)^{6/5} \le 2^{6/5}X^{6/5} \le 4X^{6/5}$ and $1 + (X+1)^{6/5} \le 5X^{6/5}$; then $(5X^{6/5})^{43/60} = 5^{43/60} X^{43/50} \le 5r$.
2. Logarithm: $\log(X+1) = 2\log\sqrt{X+1} \le 2\sqrt{X+1} \le 2\sqrt{2X} \le 4\sqrt{X} \le 4r$, so $\tfrac65 \log(X+1) \le 5r$.
3. Size: $X = X^{7/50} r$ and $X^{9/10} = X^{1/25} r$; for $X \ge 10^{25}$ both $X^{7/50}$ and $X^{1/25}$ are $\ge 10$, so $10 r \le X$ and $10 r \le X^{9/10}$. Hence bracket $+ \tfrac65\log(X+1) \le 10r \le X$, the first claim.
4. Constant: $C \le \sqrt X \le r \le X^{9/10} - 5r =: y \le e^{y}$. For $C \le 0$ the second claim is trivial; otherwise $C e^{\text{bracket}} \le e^{y} e^{5r} = e^{X^{9/10}}$.

## h_adjacent (--h2--h1--h2: an adjacent collision is a member of Lind's family)
Let $\binom{n}{k} = \binom{m}{l}$ with $m+1 = n$, $l = k+1$, $2 \le k$, $2l \le m$.
1. Cancelling $\binom{m}{k} > 0$ from $\binom{m+1}{k}(m+1-k) = \binom{m}{k}(m+1)$ and $\binom{m}{k+1}(k+1) = \binom{m}{k}(m-k)$ gives the quadratic $(m+1)(k+1) = (m-k)(m+1-k)$.
2. With $X = 5k+4$ and $Y = 2(m-k) - k \ge 0$ this is the Pell equation $X^2 - 5Y^2 = -4$.
3. Descent: a solution with $Y \ge 2$ has $X \equiv Y \pmod 2$, and $(X', Y') = (\tfrac{3X-5Y}{2}, \tfrac{3Y-X}{2})$ is a smaller nonnegative solution with $(X, Y) = (\tfrac{3X'+5Y'}{2}, \tfrac{X'+3Y'}{2})$; so every solution is reached from $(1,1)$ by that step. The step carries $(L_{2j+1}, F_{2j+1})$ to $(L_{2j+3}, F_{2j+3})$ (with $L_r = 2F_{r+1} - F_r$), so $(X, Y) = (L_{2j+1}, F_{2j+1})$ for some $j$.
4. $L_{2j+1} \equiv 1 \pmod 5$ for even $j$ and $\equiv 4$ for odd $j$ (a two-step recurrence); $X = 5k+4$ forces $j = 2i+1$.
5. From $F_{r+s+1} = F_rF_s + F_{r+1}F_{s+1}$ and Cassini $F_{2i}^2 + F_{2i}F_{2i+1} - F_{2i+1}^2 = -1$: $L_{4i+3} = 5F_{2i}F_{2i+3} + 4$ and $F_{4i+3} = 2F_{2i+2}F_{2i+3} - 3F_{2i}F_{2i+3} - 2$, hence $k = F_{2i}F_{2i+3}$ and $n = m+1 = F_{2i+2}F_{2i+3}$; $i \ge 1$ because $k \ge 2$.
