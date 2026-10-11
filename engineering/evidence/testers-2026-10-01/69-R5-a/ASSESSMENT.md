# erdos-69, the signed-family route: assessment for the owner (69-R5-a, 2026-10-01)

**Verdict: admit the definitions (Defs-v2) now. Do not wait for a number theorist to admit them; do get one to read
h4e before the network describes this target as close.** After today the whole route rests on two open statements,
and only one of them (h4e) carries real risk.

Why the answer changed since 69-R4-b:

| hole of h4 | 69-R4-b | now |
|---|---|---|
| h4a, h4b, h4c (the tables cancel; something survives) | proved | proved |
| h4g (the parameters fit) | open, "believed" | **proved**, one theorem, fast-checked (`H4g.lean`) |
| h4d (large primes) | open, "believed" | **proved exactly as stated**, from the Mertens node's statement and h4b (`H4d.lean`, six declarations, fast-checked, no sorry). No change of quantitative shape was needed |
| h4f (the model decays) | truth unknown | not proved; I have a complete elementary argument (`H4E-H4F-NOTES.md` §1): h4c + Mertens + the proved node spec-e0b917d1 + the Chinese remainder theorem, no sieve. It needs rate 64^-M; the statement allows 100^-M; exact computation at M = 2 and M = 4 shows about 11^-M and no bad prime. I believe it is true as stated |
| h4e (small primes behave independently) | truth unknown | still unverified. It is a Kubilius-model statement for about 6^M·(M + log log log z) linear forms at once. The stated bound on A is consistent with what a fundamental lemma of that dimension gives, with a factor (100/6)^M to spare, and I found no regime where it fails. But I cannot cite a theorem that states it, and no computation can reach its hypothesis (z ≥ 10^685 at M = 2) |

So the kernel-checked chain is now: root ⇐ bridge ⇐ h1, h2, h3 (proved), h4 ⇐ h4a, h4b, h4c, h4d, h4g (proved) +
**h4e, h4f** (open). The existential over parameters hides nothing: in the regime h4g picks, h4f's demand
(log log z ≳ 64^M) is met, h4e needs A ≈ 100·M·6^M, and h4d's cost C(3/4)^M(1 + log A) still tends to 0 (§2 of the notes).

What "admit" risks and does not risk. The definitions cannot make the root wrong; three proved lemmas (h4a–h4c) vouch
that the tables are the intended ones. The risk is reputational, not logical: if h4e is false in its frozen shape, the
record holds a dozen proved lemmas under a hole that never closes. Two things reduce that risk, and both must be done
BEFORE the skeleton merges, because statements are immutable:

1. **Freeze the relaxed h4e, not 69-R4-b's.** Allow A ≤ K'·100^M·(1 + log₂log₂ z)² instead of
   K'·100^M·(1 + log₂log₂log₂ z). It is implied by the old statement, h4g is still true with it (`H4g-relaxed.lean`,
   proved) and the assembly still closes (`H4Skeleton-R5.lean`, checked). The relaxed form is within reach of an
   elementary Brun-type truncation; the original needs a dimension-uniform fundamental lemma that Mathlib lacks.
2. **Thread the Mertens statement as an explicit hypothesis** of h4, h4d and h4f (`Bridge-R5.lean`,
   `H4Skeleton-R5.lean`, both checked). A gate-written hole has `deps: []`, so a hole cannot cite spec-7d098d5c;
   the dependency has to enter at the proposed bridge node and travel down in the statements.

The header question (69-R4-b's blocker): confirmed, and it is worse than stated. (a) A hole carries its parent's
library and `Defs.*` imports and nothing else (every hole on euclid-primes; `POST /check` in verify mode answers
`imports-differ` when a partial adds `import Defs.Fact`). The root imports Mathlib only, so nothing beneath the root
can name the definitions. (b) The root's declared deps are its two old holes and can never change, so a root partial
cannot cite the proved node spec-84446025 either, which `BridgeRoot.lean` needs. A way through with what exists:
propose the bridge as a **`resolves` variant** (`POST /proposals/variant`) whose header imports `Defs.Construction`,
with deps spec-84446025, spec-e0b917d1, spec-7d098d5c, and with 69-R4-b's root assembly as its `relation_proof`
(`Relation.lean`: `theorem relation : <bridge> → <root>`, fast-checked). Its holes then inherit the definitions.
Kernel-wise that proves the root. Whether a proved `resolves` variant marks the target resolved, or the root then
still needs its own `Proof.lean` (which it could not write, for reason (b)), is a product rule I could not read
from the guide: please settle it with network PR #26, before READY.md's step 2.

What this is not. It is not the Tao–Teräväinen proof (they need a two-point correlation estimate; this route makes
the large primes cost (3/4)^M·log A and so needs none — h4d is now the checked form of that claim). If h4e holds,
the network would have an independent and simpler proof of a 2025 theorem. That is exactly why a number theorist
should read `H4E-H4F-NOTES.md` §2 (one page) — the question to put is narrow: "is the Kubilius model valid for
κ ≍ 6^M·log log log z shifted linear forms with s = log T / log z ≍ κ (or ≍ κ·log log z), uniformly in κ?"

Cost of going on: h4f is perhaps 600–1000 lines of Lean (CRT product formula over a primorial period); h4e relaxed
is larger (a truncated expansion plus a moment bound; no deep input) and is the place the route can still fail.
Every proof over 200000 heartbeats must be a partial with holes (h4d is: five lemmas), which multiplies queue time.
