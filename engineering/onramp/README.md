# The on-ramp target's inputs (F11-T4)

What the curator hands `opn-gate intake new`, and what is submitted after the intake merges.
Nothing here is the record: the graph repository is (D-35). These are the inputs, kept so the
seeding is rebuildable and reviewable.

- `target.yaml` — D-6's five artifacts for `euclid-primes` (F11-R1).
- `root/infinitude-of-primes/` — the root node: statement over `Defs.IsPrime` carrying
  `Mathlib.Tactic` for provers (F11-Q16), no dependencies yet, a real witness.
- `defs/` — `Divides`, `IsPrime`, `fact` (F11-T1).
- `submissions/annex-<sha256>.md` — Euclid's argument as the D-31 annex, front matter included;
  submitted as an append on the root after the intake merges; the file's name is its hash.
- `submissions/skeleton-partial.lean` — the skeleton (D-12 #5) citing that annex: four `have`
  holes (the four lemmas of the selection record) and the assembly in Lean core; submitted as
  a partial through the service; when it merges the holes become `skeleton-hole` children.

The sequence, in the curator's hands (each step is a pull request the gate checks):

    # 0. the graph re-pinned to a network commit with the intake mode and the Mathlib image
    #    (gate/tools/pin_image.py; F10's sitting)
    # 1. intake — writes the target on a branch and prints the push and PR commands
    uv run python -m opn_gate.cli intake new euclid-primes --graph ../open_proof_network_graph \
        --from engineering/onramp/target.yaml --root engineering/onramp/root/infinitude-of-primes \
        --defs engineering/onramp/defs --author thisisanameforsure --branch intake/euclid-primes --sandbox
    # 2. merge the intake PR (mode intake: the root and the defs are admitted in the sandbox)
    # 3. submit the annex (append) and merge it; then the skeleton as a partial:
    #    POST /precheck and POST /submissions with artifact_type partial and the bundle
    #    {"targets/euclid-primes/nodes/infinitude-of-primes/attempts/<ts>-<pseudonym>-partial.lean": ...}
    # 4. merge it: the post-merge job applies the children (F07-R6) and renders the products
    # 5. opn-gate fidelity euclid-primes root screened-and-signed --by <a non-author> --evidence ...
    #    opn-gate intake post euclid-primes --venue ... --url ...; opn-gate intake activate euclid-primes
