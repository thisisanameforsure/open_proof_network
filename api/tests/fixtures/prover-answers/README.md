Prover answers for F17's import corpus (F17-T2, AC4).

Each `<case>.txt` is an answer as a prover returns it; `index.json` names the node it answers
(`tutorial` = propositional/tutorial-and-swap, `fact-pos` = onramp/euclid-primes/fact-pos) and
what `opn-prove import` must do with it: `proof` or `partial`, or the code it refuses with.

Written 2026-09-25 from the shapes the 2026-09-24 research found (docs/research_harnesses_2026-09.html,
part 2): the whole file echoed back; a proof plan and then a fenced `lean4` block (the prompt
DeepSeek-Prover-V2, Goedel-Prover-V2 and Pythagoras-Prover share), including that prompt's own
`import Mathlib` header; a bare tactic block; the exported definitions echoed back. They are
synthetic until F17-T8 captures real answers, which are added here, labelled by prover and date,
and red first.
