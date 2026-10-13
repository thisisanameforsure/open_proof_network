$$\mathrm{True}$$

- The witness is `theorem witness : True := trivial`.
- The root statement has no hypotheses, so the witness type that step 7 expects is `True` (D-4 step 7). It exhibits nothing.
- That the root's exceptional set is non-empty, for example $(7,3)$, with $\binom{7}{3}=35=5\cdot 7$ and $5>\max(\lfloor 7/3\rfloor,3)=3$, is shown by a Lean `example` in the numerical annex on this node. The example is not a witness.
