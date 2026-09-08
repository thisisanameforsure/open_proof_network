# Hazard fixtures (F02-T1, T2)

One standalone, Lean-core-only statement per checker, each exhibiting exactly its own hazard and
no other (F02-AC10), plus `Clean.lean`, whose divisions and ranges are all syntactically safe
(no findings). `expected.json` names each file's theorem and the one finding it must produce —
`checker` and `location` (the pretty-printed subterm, F02-Q4); messages are free text and not
golden. The files are elaborated as modules `Hazards.<Stem>`.
