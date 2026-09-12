# The on-ramp fixture graph (F11-T3)

A Mathlib-pinned target in the shape F11-T1 chose (`engineering/evidence/F11/selection.md`):
Euclid's theorem stated over the graph's own `defs/` — `Opn.Divides`, `Opn.IsPrime`, `Opn.fact` —
with `fact-pos` as an authored, proved lemma whose proof uses a Mathlib tactic, and the root
`infinitude-of-primes` unproved and depending on it. `gate-spec.json` pins Mathlib at the commit
`gate/mathlib-pins.txt` lists, so a run needs the checkout (`gate/scripts/install-mathlib.sh`)
or the image built for it. Test-only: the live on-ramp graph is seeded through F11-T4's intake
and skeleton path, whose interior nodes are holes, not authored lemmas.
