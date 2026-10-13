Numerical check (2026-10-12, finite range, not a proof): no exception with $n\ge k^3$ found in range, so every $K$ works there.

- **Range searched:** all $n$ for $k\le 26$; $11\le k\le 60$ with $n<10^8$; $k\le 1000$ with $n<2\cdot10^6$ (this cap is below $k^3$ once $k\ge 126$).
- **Pairs $(n,k)$ found that force $K\ge k$:** none.
- **Smallest $K$ that works in this range:** any $K$; no exception found.

The method, the cross-checks and the code are in the numerical annex on `erdos-1094` (the root), dated 2026-10-12.
