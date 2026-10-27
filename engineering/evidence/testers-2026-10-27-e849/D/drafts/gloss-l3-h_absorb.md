$$\forall C \in \mathbb{R}\ \ \exists X_0 \in \mathbb{R}\ \ \forall X \ge X_0:\quad \bigl(1 + (X+1)^{6/5}\bigr)^{43/60} \le X - \tfrac{6}{5}\log(X+1)\ \ \wedge\ \ C \cdot e^{(1 + (X+1)^{6/5})^{43/60}} \le e^{X^{9/10}}$$

Here $C$, $X_0$, $X$ are real numbers, $\log$ is the natural logarithm, and the powers are real powers (`Real.rpow`; a negative base gives Lean's conventional value, which never arises for $X \ge X_0 \ge 1$).

In words: for every constant $C$ and all sufficiently large $X$, the exponent $(1 + (X+1)^{6/5})^{43/60}$ is at most $X - \tfrac{6}{5}\log(X+1)$, and $C$ times its exponential is at most $e^{X^{9/10}}$. This is the step that absorbs the implied constant of the paper's bound into the exponent $9/10$ (with $X = \log\log a$).
