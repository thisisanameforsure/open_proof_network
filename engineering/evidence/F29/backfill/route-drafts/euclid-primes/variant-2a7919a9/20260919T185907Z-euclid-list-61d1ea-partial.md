---
kind: partial
node: variant-2a7919a9
module: attempts/20260919T185907Z-euclid-list-61d1ea-partial.lean
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
A prime larger than the sum of the list cannot be a member of it, since every entry is at most the sum.

The holes are `bound` (every x in l satisfies x ≤ l.sum) and `euclid` (a prime p > l.sum). The assembly takes that prime and refutes membership by the bound.
