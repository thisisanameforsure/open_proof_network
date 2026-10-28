## The criterion

Statement: for every real number $x$, if for every $M$ there is $N \ge M$ such that $N!\,x$ is not an integer, then $x$ is irrational.

The proof argues by contradiction. Suppose $x$ is rational, $x = r$, and write $r = p/q$ in lowest terms with $q \ge 1$ (in Lean, $p$ is `r.num` and $q$ is `r.den`).

## A large enough N {steps: s1}

Apply the hypothesis with $M = q$. It gives some $N \ge q$ such that $N!\,r \ne m$ for every integer $m$.

## The denominator divides N! {steps: s2}

Since $1 \le q \le N$, $q$ divides $N!$ (Mathlib's `Nat.dvd_factorial`); write $N! = q\,k$ with $k$ a natural number.

## Clearing the denominator {steps: h1}

A rational number times its denominator is its numerator: $r\,q = p$ (Mathlib's `Rat.mul_den_eq_num`, cast to the reals).

## The contradiction {steps: close}

Take $m = k\,p$ in the choice of $N$. Then $N!\,r = q\,k\,r = k\,(r\,q) = k\,p = m$, an integer, which the choice of $N$ excludes. Substituting $N! = q\,k$, pushing the casts to the reals and taking $k$ times the identity $r\,q = p$ closes the equation. So $x$ is not rational.
