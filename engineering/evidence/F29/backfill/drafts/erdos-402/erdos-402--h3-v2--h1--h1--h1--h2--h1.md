---
label: "Window primes for 10 ≤ n ≤ 228"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$\forall n \in \mathbb{N},\ 10 \le n \le 228:\ \exists\, p\ \text{prime}:\ n < p < 2n,\ 2(2n - p) \le n + 2,\ \forall \alpha < n,\ p < \alpha + n \Rightarrow \bigl(\exists\, q\ \text{prime}:\ n \le 3q,\ q \mid \alpha (p - \alpha)\bigr) \vee \bigl(\forall x < y,\ x y \mid \alpha \Rightarrow n x \le \alpha y\bigr)$$

For every n from 10 to 228 there is a prime p with n < p < 2n and 2(2n − p) ≤ n + 2 such that every α < n with p − n < α either has a prime q with n ≤ 3q dividing α(p − α), or satisfies n·x ≤ α·y for all x < y with x·y dividing α. All variables range over ℕ; the subtractions are in ℕ but p < 2n and α < n < p keep 2n − p and p − α ordinary.
