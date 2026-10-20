---
label: "BHP short-interval primes"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\exists C>0\ \ \exists k_0\in\mathbb{N}\ \ \forall k\ge k_0:\qquad \frac{C\,k^{21/40}}{\log k}\ \le\ \#\bigl\{p\text{ prime}:\ k<p<k+k^{21/40}\bigr\}$$

For one constant $C>0$ and all large $k$, the interval $(k,\,k+k^{21/40})$ contains at least $C\,k^{21/40}/\log k$ primes: the Baker–Harman–Pintz short-interval prime count. In the Lean the set is a finite set of integers $p$ in the open interval $(\lfloor k\rfloor,\lceil k+k^{21/40}\rceil)$ filtered by $0<p$, $|p|$ prime and $k<p<k+k^{21/40}$ over the reals, which is exactly the primes of that real interval; its cardinality is cast to $\mathbb{R}$, $k^{21/40}$ is a real power and $\log$ is the natural logarithm.
