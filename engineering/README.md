# engineering/

How this repo gets built. Nothing here describes what the network is or how contributors use it
once it exists — that is `docs/architecture_decisions_v_3_11.html`, and it governs where the two
disagree.

```
engineering/
  CLAUDE.md        # the build protocol for Claude sessions (imported by the root CLAUDE.md)
  specs/           # the spec site: constitution, conventions, index, one spec per feature
  evidence/        # captured verification output, one directory per feature
```

Rules of the split:

- Build docs **cite** architecture decisions by D-number. They never restate or override one.
- A build spec that cannot follow a decision logs the deviation in the spec as a proposed
  overturn; the decision itself changes only through the architecture doc's own process.
- Tooling that git and make expect at the root (`Makefile`, `.githooks/`, `.claude/`) stays at
  the root but is build-time only.
