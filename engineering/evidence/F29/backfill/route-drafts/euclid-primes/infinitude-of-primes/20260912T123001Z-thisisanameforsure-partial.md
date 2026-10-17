---
kind: partial
node: infinitude-of-primes
module: attempts/20260912T123001Z-thisisanameforsure-partial.lean
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
Euclid's argument: a prime divisor of n! + 1 exceeds n, because every k ≤ n divides n! and nothing but 1 divides two consecutive numbers.

The holes are `dvd_fact` (every 1 ≤ k ≤ n divides n!), `prime_divisor` (every m ≥ 2 has a prime divisor), `dvd_consecutive` (a common divisor of m and m + 1 is 1) and `fact_pos` (n! > 0). The assembly takes a prime p dividing n! + 1 and, if p ≤ n, derives p ∣ n! and p = 1, contradicting primality.
