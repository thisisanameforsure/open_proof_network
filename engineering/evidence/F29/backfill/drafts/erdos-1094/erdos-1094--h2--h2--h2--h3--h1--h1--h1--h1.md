---
label: "a small integer linear relation on 2r points"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists a:\{0,\dots,2r-1\}\to\mathbb{Z}:\quad \sum_{i}a_i w_i u_i^{\,j}=0\ (j<r),\qquad \sum_{i}a_i w_i u_i^{\,r}\ne 0,\qquad |a_i|\le\Bigl(\frac{256\,M}{r}\Bigr)^{r-1}W$$

For every $r\ge 1$, with $s=2r$, every real $M\ge s-1$ and $W\ge 1$, every strictly increasing $u:\{0,\dots,s-1\}\to\mathbb{Z}$ with $0\le u_i\le M$ and every $w:\{0,\dots,s-1\}\to\mathbb{N}$ with $0<w_i\le W$, there are integers $a_i$ whose weighted moments $\sum_i a_iw_iu_i^{\,j}$ vanish for every $j<r$ but not for $j=r$, with the displayed bound on each $|a_i|$. The index set is Lean's `Fin s`; the sums, the comparisons and $u_i^{\,j}$ are over the reals after casting, and $r-1$ is a natural exponent.
