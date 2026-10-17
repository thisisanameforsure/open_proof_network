---
label: "Generalised window criterion for |B| > 200014"
supersedes: null
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$n = |B| > 200014:\quad \bigl(\exists\, a, b \in B:\ \gcd(a,b) \le \frac{a}{|B|}\bigr) \vee \Bigl(\exists\, p\ \text{prime}:\ n < p < 2n,\ 2(2n - p) \le n + 2,\ \forall \alpha < n,\ p < \alpha + n \Rightarrow \bigl(\exists\, q\ \text{prime}:\ n \le 3q,\ q \mid \alpha (p - \alpha)\bigr) \vee \bigl(\forall x < y,\ x y \mid \alpha \Rightarrow n x \le \alpha y\bigr)\Bigr)$$

For every finite set B of positive integers (0 ∉ B, B nonempty) whose elements have greatest common divisor 1, whose size |B| is neither a prime nor one more than a prime, in which a ≤ |B|·gcd(a, b) for all a, b ∈ B, and in which every prime power dividing an element is below |B|, and with more than 200014 elements, writing n = |B|: either some a, b ∈ B (possibly equal) have gcd(a, b) ≤ a/|B|, or there is a prime p with n < p < 2n and 2(2n − p) ≤ n + 2 such that every α < n with p − n < α either has a prime q with n ≤ 3q dividing α(p − α), or satisfies n·x ≤ α·y for all x < y with x·y dividing α. gcd(B) is the greatest common divisor of all elements of B; α, x, y, q range over ℕ, the subtractions are in ℕ but p < 2n and α < n < p keep 2n − p and p − α ordinary, and the one division is in ℚ.
