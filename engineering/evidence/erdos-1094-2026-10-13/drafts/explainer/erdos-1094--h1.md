## Overview

$$\forall k\ge 1:\quad k^2\le n,\ \ \operatorname{lpf}\tbinom{n}{k}>\lfloor n/k\rfloor \implies n<k!+k.$$

So for each $k$ the set is bounded, hence finite. This is Erdős's observation, with an explicit bound. Write $t=\lfloor n/k\rfloor$ and $m=kt$, the largest multiple of $k$ not above $n$. Every prime factor of $m$ is at most $t$, so $\gcd\bigl(m,\binom{n}{k}\bigr)=1$. But $m$ is one of $n,n-1,\dots,n-k+1$, whose product is $k!\binom{n}{k}$. Hence $m\mid k!$, so $m\le k!$, and $n<m+k\le k!+k$.

## The hypotheses {steps: s1}

Fix $k\ge 1$ and $n$ with $k^2\le n$ and $\operatorname{lpf}\binom{n}{k}>t$, where $t=\lfloor n/k\rfloor$ (Lean's `n / k`). It suffices to show $n<k!+k$, because $\{n : n<k!+k\}$ is finite.

## Sizes of t and m {steps: hkt htpos hm_le hm_gt}

From $k^2\le n$ we get $k\le t$, so $t>0$. And $m=kt$ satisfies $n-k<m\le n$.

## No small prime divides the coefficient {steps: hnd}

If a prime $p\le t$ divided $\binom{n}{k}$, then $\operatorname{lpf}\binom{n}{k}\le p\le t$, against the hypothesis.

## m is coprime to the coefficient {steps: hcop}

A prime $p\mid m=kt$ divides $k$ or $t$. Then $p\le k\le t$, or $p\le t$. By the previous step $p\nmid\binom{n}{k}$, so $\gcd\bigl(m,\binom{n}{k}\bigr)=1$.

## m divides k! times the coefficient {steps: hm_dvd}

$n^{\underline{k}}=n(n-1)\cdots(n-k+1)=k!\binom{n}{k}$; Mathlib calls this `Nat.descFactorial`. Since $n-k<m\le n$, we have $m=n-j$ with $0\le j<k$, so $m$ is one of the factors.

## The bound {steps: hm_fact hle close}

From $\gcd\bigl(m,\binom{n}{k}\bigr)=1$ and $m\mid k!\binom{n}{k}$ we get $m\mid k!$, so $m\le k!$. With $n<m+k$ this gives $n<k!+k$; Lean closes the arithmetic with `omega`.
