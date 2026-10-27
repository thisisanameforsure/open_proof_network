## Overview

The statement says that every adjacent-row collision $\binom{n}{k} = \binom{n-1}{k+1}$ in the half triangle ($2 \le k$, $2k \le n$, $2(k+1) \le n-1$) is a member of Lind's family: $(n, k) = (F_{2i+2}F_{2i+3}, F_{2i}F_{2i+3})$ for some $i \ge 1$. This is the classification of Lind (1968) and Singmaster (1975), also in Tovey (1985). Eight private lemmas precede the theorem and are no steps of the outline; the theorem's own steps instantiate them. In order: `e849_adjacent_iff`, for $k \le m$, $\binom{m+1}{k} = \binom{m}{k+1}$ holds exactly when $(m+1)(k+1) = (m-k)(m+1-k)$ (cancel $\binom{m}{k} > 0$ from $\binom{m+1}{k}(m+1-k) = \binom{m}{k}(m+1)$ and $\binom{m}{k+1}(k+1) = \binom{m}{k}(m-k)$); `e849_adjacent_pell`, that quadratic is the Pell equation $X^2 - 5Y^2 = -4$ in integers with $X = 5k+4$ and $Y = 2(m-k) - k$; `e849_pell_parity`, a solution has $X \equiv Y \pmod 2$; `e849_pell_descent`, a solution with $X \ge 0$ and $Y \ge 2$ comes from a smaller non-negative solution $(X', Y') = (\tfrac{3X - 5Y}{2}, \tfrac{3Y - X}{2})$ by the step $(X, Y) = (\tfrac{3X' + 5Y'}{2}, \tfrac{X' + 3Y'}{2})$; `e849_pell5_induction`, hence every non-negative solution is reached from $(1, 1)$ by that step, and the step carries $(L_{2j+1}, F_{2j+1})$ to $(L_{2j+3}, F_{2j+3})$ (with $L_r = 2F_{r+1} - F_r$), so every non-negative solution is $(L_{2j+1}, F_{2j+1})$ for some $j$; `e849_cassini`, $F_{2i}^2 + F_{2i}F_{2i+1} - F_{2i+1}^2 = -1$; `e849_lucas_step` and `e849_lucas_mod5`, $L_{2j+1} \equiv 1 \pmod 5$ for even $j$ and $\equiv 4 \pmod 5$ for odd $j$; and `e849_lind`, the identities $L_{4i+3} = 5F_{2i}F_{2i+3} + 4$ and $F_{4i+3} = 2F_{2i+2}F_{2i+3} - 3F_{2i}F_{2i+3} - 2$ (from $F_{r+s+1} = F_rF_s + F_{r+1}F_{s+1}$ and Cassini).

## From the collision to the Pell equation {steps: hkm hq hp hY0}

After introducing the four numbers and the hypotheses, the two equalities $l = k + 1$ and $m + 1 = n$ are substituted, so the collision reads $\binom{m+1}{k} = \binom{m}{k+1}$ with $k \le m$ (`hkm`, from $2(k+1) \le m$). The first private lemma turns it into the quadratic $(m+1)(k+1) = (m-k)(m+1-k)$ (`hq`), and the second into the Pell equation $(5k+4)^2 - 5\,(2(m-k) - k)^2 = -4$ (`hp`); the second coordinate $Y = 2(m-k) - k$ is non-negative because $2k \le m$ (`hY0`).

## Every solution is a Lucas–Fibonacci pair {steps: key s6}

The descent principle is applied to the predicate "$(X, Y) = (L_{2j+1}, F_{2j+1})$ for some $j$": it holds at $(1, 1)$ (with $j = 0$) and is preserved by the ascent step, so it holds at $(5k+4,\ 2(m-k) - k)$ (`key`); taking the witness apart gives $j$ with $5k + 4 = L_{2j+1}$ and $2(m-k) - k = F_{2j+1}$ (`hX`, `hY`).

## The index is odd, and Lind's parametrisation {steps: s7 s8 hk hn hk' hn'}

Since $5k + 4 \equiv 4 \pmod 5$ while $L_{2j+1} \equiv 1 \pmod 5$ for even $j$, the index $j$ is odd: $j = 2i + 1$ for some $i$, which is substituted. The identities of `e849_lind` at $i$ then read $5k + 4 = 5F_{2i}F_{2i+3} + 4$ and $2(m-k) - k = 2F_{2i+2}F_{2i+3} - 3F_{2i}F_{2i+3} - 2$; linear arithmetic (`linarith`) over the integers gives $k = F_{2i}F_{2i+3}$ and $m + 1 = F_{2i+2}F_{2i+3}$, which are cast back to natural numbers (`hk'`, `hn'`).

## Closing {steps: s13 s14}

The witness $i$ is supplied with the two equations and the two substituted equalities ($m + 1 = n$ and $l = k + 1$ hold by `rfl` after the substitutions). It remains that $i \ge 1$: if $i = 0$ then $k = F_0 F_3 = 0$, contradicting $2 \le k$ (`simp`, then `omega`); otherwise $i > 0$ is the hypothesis of the case.
