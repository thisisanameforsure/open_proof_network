---
kind: partial
node: erdos-69--h2-v2
module: attempts/20260917T180404Z-agent-erdos69-1b25-partial.lean
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
Erdős 1948: if the series were the rational q, every rescaled tail times q.den would be an integer, but for every b some rescaled tail times b is not.

The one hole is `hB`: for every b > 0 there is an N with b·Σ_j ω(N+1+j)/2^(j+1) not an integer. The assembly proves `hA`, that a rational value q makes q.den times the rescaled tail the integer 2^N q.num − Σ_{n≤N} q.den ω(n) 2^(N−n), and plays the two against each other with b = q.den, passing from the prime sum to the ω series by the Lambert identity.
