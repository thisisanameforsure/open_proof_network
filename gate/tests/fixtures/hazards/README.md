# Hazard fixtures (F02-T1, T2)

One standalone, Lean-core-only statement per checker, each exhibiting exactly its own hazard and
no other (F02-AC10); `Clean.lean`, whose divisions, bounds, predecessor and binders are all safe
(no findings); and `NegLiteral.lean`, a ℤ division by `-3` that `div-zero` accepts as
syntactically non-zero while `int-trunc` flags the rounding. `expected.json` names each hazard
file's theorem and the one finding it must produce — `checker` and `location` (the
pretty-printed subterm, or the binder name for `unused-binder`, F02-Q4); messages are free text
and not golden. The files are elaborated as modules `Hazards.<Stem>`.
