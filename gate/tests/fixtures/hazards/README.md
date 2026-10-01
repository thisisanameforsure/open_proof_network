# Hazard fixtures (F02-T1, T2)

One standalone, Lean-core-only statement per checker, each exhibiting exactly its own hazard and
no other (F02-AC10); `Clean.lean`, whose modulos, bounds, predecessor and binders are all safe
(no findings); `NegLiteral.lean`, a ℤ division by `-3` that `div-zero` accepts as
syntactically non-zero while `int-trunc` flags the rounding; `ArrowType.lean`, a function type
that is not an unused binder (F02-T8); and `NatDivCast.lean`, the `NatDiv.lean` division with its
operand cast to ℤ, which `nat-div` must not flag (F02-T9). `expected.json` names each hazard
file's theorem and the one finding it must produce — `checker` and `location` (the
pretty-printed subterm, or the binder name for `unused-binder`, or the identifier for
`auto-implicit`, F02-Q4); messages are free text and not golden. The files are elaborated as
modules `Hazards.<Stem>`. Since F02-T9 every `/` on ℕ is a `nat-div` finding, so the fixtures
that need a safe ℕ divisor for `div-zero`'s sake use `%`, which `div-zero` reads the same way.
