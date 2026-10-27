## Overview

The statement is a real-analysis inequality with no arithmetic content: for every constant $C$ and all sufficiently large $X$, $(1 + (X+1)^{6/5})^{43/60} \le X - \tfrac{6}{5}\log(X+1)$ and $C e^{(1 + (X+1)^{6/5})^{43/60}} \le e^{X^{9/10}}$. It is the step that absorbs the implied constant of the paper's distance bound into the exponent $9/10$. Three private lemmas precede the theorem and are no steps of the outline; throughout, $r := X^{43/50}$. `e849_absorb_pow` ($X \ge 1$): $(1 + (X+1)^{6/5})^{43/60} \le 5r$, since $X + 1 \le 2X$ gives $(X+1)^{6/5} \le 4 X^{6/5}$, so $1 + (X+1)^{6/5} \le 5 X^{6/5}$, and $(5X^{6/5})^{43/60} = 5^{43/60} X^{43/50} \le 5r$. `e849_absorb_log` ($X \ge 1$): $\tfrac{6}{5}\log(X+1) \le 5r$, since $\log(X+1) = 2\log\sqrt{X+1} \le 2\sqrt{X+1} \le 4\sqrt{X} \le 4r$ (using $\log y \le y - 1 < y$ and $\sqrt{X} = X^{1/2} \le X^{43/50}$). `e849_absorb_big` ($X \ge 10^{25}$): $10 r \le X$ and $10 r \le X^{9/10}$, since $X = X^{7/50} r$, $X^{9/10} = X^{1/25} r$, and $X^{e} \ge 10$ whenever $25 e \ge 1$.

## Choosing the threshold {steps: hXb hXC hX1 hX0 hr0 hA hL s8 hCr}

Given $C$, the threshold is $X_0 := \max(10^{25}, C^2)$, so that for $X \ge X_0$ both $X \ge 10^{25}$ and $C^2 \le X$ hold; in particular $X \ge 1$ and $r \ge 0$. The three private lemmas are instantiated at $X$ (`hA`, `hL`, `hB1`, `hB2`), and $C \le r$ is derived: $C \le |C| = \sqrt{C^2} \le \sqrt{X} \le r$.

## The two claims {steps: s10 s11}

The first claim, $(1 + (X+1)^{6/5})^{43/60} \le X - \tfrac{6}{5}\log(X+1)$, is linear arithmetic from the bounds $5r$, $5r$ and $10r \le X$. For the second, write $A$ for the bracket and $y := X^{9/10} - 5r$. Then $C \le r \le y$ (from $10r \le X^{9/10}$), hence $C \le y + 1 \le e^{y}$ (Mathlib's `Real.add_one_le_exp`), and $e^{A} \le e^{5r}$ by monotonicity of the exponential; multiplying, $C e^{A} \le e^{y} e^{5r} = e^{X^{9/10}}$ (when $C \le 0$ the left side is at most $0$ and the claim is immediate).
