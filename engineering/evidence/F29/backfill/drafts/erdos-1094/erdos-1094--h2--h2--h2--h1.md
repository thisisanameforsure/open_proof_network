---
label: "small range 2k < n ≤ k^(2−21/40)/2"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\neg\,\text{BHP}\ \ \lor\ \ \exists k_0\in\mathbb{N}\ \forall k\ge k_0\ \forall n\in\mathbb{Z}:\ \ 2k<n\le\tfrac12\,k^{2-21/40}\ \Longrightarrow\ \exists p\text{ prime},\ k<p<k+3k^{21/40},\ \ p\mid\prod_{i=1}^{k}(n-i)$$

Either the Baker–Harman–Pintz short-interval prime count fails, or for all large $k$ and every integer $n$ with $2k<n\le\tfrac12 k^{2-21/40}$, some prime $p$ in $(k,\,k+3k^{21/40})$ divides $(n-1)(n-2)\cdots(n-k)$. Here BHP is the Baker–Harman–Pintz short-interval prime count $\exists C>0\ \exists k_0\ \forall k\ge k_0:\ C\,k^{21/40}/\log k\le\#\{p\text{ prime}:k<p<k+k^{21/40}\}$, the primes counted as the integers of the interval $(\lfloor k\rfloor,\lceil k+k^{21/40}\rceil)$ that are positive, prime in absolute value and lie strictly between $k$ and $k+k^{21/40}$ over the reals. $n$ ranges over $\mathbb{Z}$ and the product $\prod_{i=1}^{k}(n-i)$ is taken in $\mathbb{Z}$; the bounds on $n$ and $p$ are over the reals with $21/40$ a real exponent, and $\log$ is the natural logarithm.
