# Calibration run — erdos-402 (Graham's gcd conjecture), F15-T14c

Agent log. One file holds all state; a successor reads
`engineering/session-notes/2026-09-17-calibration-run-handoff.md` then this file and continues
from "Next". Started 2026-09-17 (Fable 5.1). Timebox ~50 min.

## Status (keep current)

- State: **partial PR open, gate green** — graph **PR #79** (`partial: erdos-402`, head
  `e47f2b8`, branch `submit/01M2QW06ZG6T1ZW656S709HTM0`, author `app/open-proof-network`).
  Check `gate (steps 1, 2 and 4-8 in the sandbox)`: **SUCCESS** (run `35233227359`, 14:23:23 →
  14:27:19 UTC). Check `step 9 (a non-author approving review)`: FAILURE by design — the
  target's `step9` is `review`, so it waits for the owner's approving review (which re-runs only
  that job). `mergeStateStatus BLOCKED` until then. **Stopped here; the lead merges.** The
  three-hole skeleton (file `<scratchpad>/sk/partial.lean`, reproduced in full under "Current
  best Lean source") passed its owned precheck and the live gate on the first round each.
- Target on `origin/main`: **yes** since 14:1x UTC (PR #74 merged; main `456997d`, frontier
  `rendered_from 1f9fb28`, erdos-402 claimable).
- Token: pseudonym `calib-402-f480` (tutorial proof), file `<scratchpad>/tok/token.json` only.
- Check ids: `01M2QVM3984A90W2FTF6TB8C3P` (fast check; failed upstream — stale environment name,
  see 00:17). Precheck ids: tutorial `01M2QV8R080JGRMZC4PJTYSXD3` (pass, minted the token);
  owned partial **`01M2QVS6C00HR3WW1K1M496BM2`** (pass). Submission
  **`01M2QW06ZG6T1ZW656S709HTM0`** → **PR #79** (gate in progress at 14:25 UTC).
- Scripts (scratchpad `sk/`): `precheck.sh` (done), `submit.sh` (refuses unless the precheck
  verdict is `pass`), `watch.sh` (polls `GET /submissions/<id>` until the gate check concludes).

## Rules I am under (from the brief)

- Never commit/push/merge/close anything on the graph; never touch its main working tree.
  Read via `git show <ref>:<path>`. On the network repo: only this file and scratch files.
- No Mathlib docker pull; iterate on `POST /check`; `POST /precheck` before submit; submit as a
  partial once the target is live; stop at green PR (lead merges).
- A proof cannot add an import or change the header (F00-R19). Lemma holes first, assembly locals
  after (F11-Q22: each hole inherits the earlier holes as hypotheses). Hazard-free ranges where
  possible (F07-Q19: `2 ≤ m` tripped `off-by-one-range`).

## Log (chronological)

- 00:00 — Read the handoff note, the draft (`engineering/onramp/calibration/erdos-402/`), the
  registry file `upstream/402.lean`. The statement as drafted:

      open Filter
      theorem Opn.erdos_402 :
          ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := by
        sorry

  Header: `import Mathlib`, one doc comment, `open Filter`. Witness in draft: `⟨{1}, by simp, by simp⟩`.

- 00:06 — Read the README, the guide (fast check §185, token §457, precheck/submit §481, skeleton
  §708), the hole extractor `gate/lean/OpnGate/Holes.lean`, step 2's rule
  (`gate/opn_gate/paths.py::check_proof_is_statement`: the file must start with the statement's
  prefix byte for byte — header, `open Filter`, the signature up to `:= by` — so **no helper
  declarations**; lemmas are `have h : T := sorry` inside the body), the off-by-one checker
  (`gate/lean/OpnGate/Hazards/OffByOneRange.lean`: flags `<`/`≤`/`>`/`≥` with a **non-zero
  literal** on either side, and `range/Ico/Icc/...` with a literal-adjusted bound; `0 < n` is fine).
  Live node on `origin/intake/erdos-402` (head 4b68415 at read time): Statement.lean identical to the
  draft; META `statement-hash 6f195d3d…73d2`, `acknowledged_hazards: div-zero` at `↑a / ↑A.card`;
  Context.lean has no deps; gate-spec pins network `26e86c4`, Mathlib `0df444a3`, image
  `opn-gate@sha256:bc6877a8…`, step3 caps 2 cpu / 4 GiB / 600 s.
- 00:08 — `/check` resolves `target_id` through the api's graph doc (`api/opn_api/checks.py::
  hosted_for` → 404 `target-unknown` for a target not in the products). `GET /hosted-checkers.json`
  lists 24 targets, none of the three calibration targets. **Workaround:** iterate in `mode: check`
  (no `node_id`) with `target_id: erdos-376`, which pins the same Mathlib `0df444a3` and maps to
  environment `lean-4.33.0` (`exact: false`). Switch to `mode: verify` on `erdos-402` once live.
- 00:09 — Token minting started in the background (`<scratchpad>/tok/mint.sh`, log
  `<scratchpad>/tok/mint.log`; the token is written to `<scratchpad>/tok/token.json` only, never
  here). Anonymous tutorial precheck job `01M2QV8R080JGRMZC4PJTYSXD3` (POST 202, graph_commit
  `42f94ef2`) → nonce → `POST /tokens` with pseudonym `calib-402-<hex>`.
- 00:10 — **Lead's update (verbatim in substance):** another session is driving intake PR #74
  itself — branch updated 14:08 UTC (head `47443d5`), gate running, it merges when green; do not
  touch PR #74 or the graph. The graph's products are stale — main's `frontier.json` and
  `targets/index.json` are `rendered_from 42f94ef` (PR #71, yesterday), the live
  `/frontier.json` has 22 entries and none of the calibration targets, and the precheck job checks
  the graph out at `frontier.json`'s `rendered_from` (F06-Q10). The post-merge run of #74 under the
  new pin (network `0401858`, which erdos-402's gate-spec already carries — note: the branch head I
  read said `26e86c4`; the lead's update says `0401858`, so the 14:08 update re-pinned it) should
  re-render products for all three targets and land a bot commit, expected ~14:30–14:50 UTC; only
  after that can precheck/submit see erdos-402. Until then: `POST /check` only. Readiness poll:

      git -C ../open_proof_network_graph fetch -q origin && git show origin/main:frontier.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['rendered_from'], [e for e in d['entries'] if 'erdos-402' in json.dumps(e)][:1])"

- 00:11 — Literature: `matwbn.icm.edu.pl/ksiazki/aa/aa75/aa7511.pdf` (the B–S paper) answers an
  anti-bot HTML page to curl and 403 to WebFetch; `eudml.org/doc/206861` 403. erdosproblems.com/402
  read (proof history only: Szegedy 1986 and Zaharescu 1987 for large sets, B–S 1996 in full;
  equality cases {1..n}, {L/1..L/n}, {2,3,4,6}). arXiv 2005.04429 (Farey sequence and Graham's
  conjectures) abstract read: the Farey reformulation is the bridge.

- 00:16 — **Token minted:** anonymous tutorial precheck `01M2QV8R080JGRMZC4PJTYSXD3` → `done`,
  verdict `pass`; `POST /tokens` → 201, identity pseudonym **`calib-402-f480`**, proof kind
  `tutorial`. The token is in `<scratchpad>/tok/token.json` (mode 600), nowhere else. A successor
  without the scratchpad re-mints in ~3 min with `<scratchpad>/tok/mint.sh`'s recipe (above).
- 00:17 — **Failure (typed, R14 e): the fast check is unusable for every Mathlib target.**
  `POST /check` (`target_id: erdos-376`, `mode: check`) → HTTP 200, log id
  `01M2QVM3984A90W2FTF6TB8C3P`, environment `lean-4.33.0`, `result.user_error` verbatim:

      Unknown environment: lean-4.33.0. Available environments: lean-4.21.0, lean-4.22.0, lean-4.23.0, lean-4.24.0, lean-4.25.1, lean-4.26.0, lean-4.27.0, lean-4.28.0, lean-4.29.0, lean-4.30.0, lean-4.31.0, lean-4.32.2, lean-4.33.1, lean-4.34.0

  Cause: `gate/hosted-checkers.yaml` maps the pin to `lean-4.33.0` (its comment: "hosts lean-4.33.0
  and no 4.33.1 environment (probed 2026-09-14)"); AXLE has since replaced 4.33.0 by 4.33.1. The
  request has no environment field, so no client can route around it. **Fix is one line in
  `gate/hosted-checkers.yaml` plus a deploy — the network's, not mine.** Consequence for this run:
  the only Lean check available to me is `POST /precheck` (the full gate, minutes per round), so
  the assembly was reviewed by hand line by line before the first precheck, with a
  `first | div_lt_iff₀ | div_lt_iff` fallback on the one lemma name I could not confirm.
- 00:18 — **Target live** (lead's message): PR #74 merged, `origin/main` at `456997d` (`gate: #74
  pass`), `frontier.json` `rendered_from 1f9fb28`, 28 entries, `erdos-402` listed `claimable: true`.
  Live node re-read from `origin/main`: Statement.lean identical to the branch copy (prefix of my
  file matches byte for byte, 1163 bytes up to `:= by\n`); META unchanged (statement-hash
  `6f195d3d…73d2`); gate-spec now pins network `0401858a22…` and image `opn-gate@sha256:0a300f39…`.
- 00:19 — Step-2 rule confirmed in `layout.parse_statement`: `prefix` = the text up to and including
  the `:=` of the sorry body, `suffix` = whatever follows `sorry`; the body (`by …`, comments
  included) is free. An `-- annex:` line is parsed only by `postmerge.py` (optional); no annex was
  filed (time), noted under Next. Partial path: `attempts/<YYYYMMDDTHHMMSSZ>-<pseudonym>-partial.lean`
  (live examples: `erdos-412/.../attempts/20260916T080157Z-agent-sigma-4f1d-partial.lean`).

## Decomposition (why these three holes)

The B–S paper itself could not be fetched (both mirrors block non-browser clients, see 00:11), so
the holes follow the architecture every published proof shares (Szegedy 1986, Zaharescu 1987,
Cheng–Pomerance 1994, B–S 1996, and the Farey reformulation in arXiv 2005.04429), not B–S's own
lemma numbering. A successor holding the paper can split h3 further **before** submitting, or
later by skeletonizing the h3 child once merged (D-31 allows a skeleton on a hole).

Two constraints shaped the statements:

1. **Every hole must have satisfiable hypotheses**, because each becomes a child node that needs
   a step-7 non-vacuity witness (`gate/lean/OpnGate/WitnessType.lean`: the expected witness is
   `∃ vars, hyp₁ ∧ … ∧ hypₖ`). The natural "suppose Graham fails for A → False" core lemma is
   unwitnessable — its witness would be a counterexample to the theorem. So every hole is stated
   positively, with a parameter `m` (h1) or the non-strict bound `≤ |A|` (h3) that `{1..n}` and
   `{1}` satisfy.
2. **Each hole inherits the earlier holes as hypotheses (F11-Q22)**, so its witness must *prove*
   them. Order is therefore easiest-to-prove first: h1 (Farey structure, elementary), h2 (scaling
   reduction, medium), h3 (the core, the whole difficulty). Witness costs: h1's child — a set with
   `a ≤ m·gcd(a,b)` for all pairs (`{1}`, `m = 1`); h2's child — a proof of h1 plus a set `A`
   such that Graham holds for every primitive set of `A`'s size (`{1}`: primitive singletons are
   `{1}`); h3's child — proofs of h1 and h2 plus a primitive Farey-structured set (`{1}`).

- **h1 (Farey structure).** If every `a/gcd(a,b)` over `A` is at most `m` (stated without
  division as `a ≤ m * gcd a b`), then every quotient `a/b` is a reduced fraction `u/v` with
  `1 ≤ u, v ≤ m`. Proof sketch for the child: `u = a/d`, `v = b/d`, `d = gcd a b`;
  `Nat.coprime_div_gcd_div_gcd`; `a * v = b * u` since both equal `a*b/d`.
- **h2 (reduction to primitive sets).** Graham for every set of `A`'s size with gcd 1 gives it for
  `A`: scale by `g = A.gcd id` (`Finset.extract_gcd`), the image under `(· / g)` has the same card,
  gcd 1, and `gcd(ga', gb') = g·gcd(a', b')` while `ga'/|A|` scales the same way.
- **h3 (the core).** A primitive set all of whose quotients are Farey fractions of order `|A|`
  satisfies Graham's bound. This is where B–S's argument lives (and Szegedy/Zaharescu's for large
  sets): the p-adic window argument on the max element and the sieve estimates.

Hazards: none of the hole statements uses a non-zero literal beside `<`/`≤` or a literal-adjusted
range (`0 < u` is the positivity idiom the checker exempts), so no `off-by-one-range` flag is
expected. h2 and h3 restate the theorem's conclusion `a.gcd b ≤ (a / A.card : ℚ)`, so their
children will carry the parent's `div-zero` flag at `↑a / ↑A.card` — the same one META
acknowledges on the parent — and F07-Q19 (holes written without `acknowledged_hazards`) applies to
them; h1 carries no division at all.

## Current best Lean source (the file precheck runs on)

Header and signature are `Statement.lean`'s byte for byte; only the body after `:= by` is mine.

    theorem Opn.erdos_402 :
        ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := by
      -- Skeleton of the Balasubramanian–Soundararajan / Szegedy argument for Graham's conjecture.
      -- Hole 1 (Farey structure): if every ratio a / gcd(a, b) over A is at most m, then every
      -- quotient a / b is a reduced fraction u / v with 1 ≤ u, v ≤ m.
      have h1 : ∀ (A : Finset ℕ) (m : ℕ), 0 ∉ A → (∀ a ∈ A, ∀ b ∈ A, a ≤ m * a.gcd b) →
          ∀ a ∈ A, ∀ b ∈ A, ∃ u v : ℕ, 0 < u ∧ u ≤ m ∧ 0 < v ∧ v ≤ m ∧ Nat.Coprime u v ∧
            a * v = b * u := sorry
      -- Hole 2 (reduction to primitive sets): the ratio a / gcd(a, b) is invariant under scaling, so
      -- the conclusion for every set of the same size with gcd 1 gives it for A.
      have h2 : ∀ A : Finset ℕ, 0 ∉ A → A.Nonempty →
          (∀ B : Finset ℕ, 0 ∉ B → B.card = A.card → B.gcd id = 1 →
            ∃ᵉ (a ∈ B) (b ∈ B), a.gcd b ≤ (a / B.card : ℚ)) →
          ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := sorry
      -- Hole 3 (the core, Balasubramanian–Soundararajan 1996; Szegedy 1986 and Zaharescu 1987 for
      -- large sets): a primitive set all of whose quotients are Farey fractions of order |A|
      -- satisfies Graham's bound.
      have h3 : ∀ A : Finset ℕ, 0 ∉ A → A.Nonempty → A.gcd id = 1 →
          (∀ a ∈ A, ∀ b ∈ A, ∃ u v : ℕ, 0 < u ∧ u ≤ A.card ∧ 0 < v ∧ v ≤ A.card ∧
            Nat.Coprime u v ∧ a * v = b * u) →
          ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := sorry
      -- Assembly: reduce to a primitive B of the same size; if the bound failed on B, every ratio
      -- would be below |B|, so B would have Farey structure of order |B|, and the core gives the
      -- bound after all.
      intro A hA hne
      refine h2 A hA hne ?_
      intro B hB hcard hg
      by_contra hcon
      push_neg at hcon
      have hBne : B.Nonempty := by
        rw [← Finset.card_pos, hcard]
        exact hne.card_pos
      have hbound : ∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b := by
        intro a ha b hb
        have h := hcon a ha b hb
        have hpos : (0 : ℚ) < B.card := by exact_mod_cast hBne.card_pos
        have h' : (a : ℚ) < (a.gcd b : ℚ) * B.card := by
          first
            | exact (div_lt_iff₀ hpos).mp h
            | exact (div_lt_iff hpos).mp h
        rw [mul_comm] at h'
        have h'' : a < B.card * a.gcd b := by exact_mod_cast h'
        exact h''.le
      obtain ⟨a, ha, b, hb, hle⟩ := h3 B hB hBne hg (h1 B B.card hB hbound)
      exact absurd hle (not_le.mpr (hcon a ha b hb))

The whole file (header included) is `<scratchpad>/sk/partial.lean`; a successor without the
scratchpad rebuilds it as `Statement.lean` with `sorry` replaced by the body above.

- 00:20 — **Owned precheck submitted:** `POST /precheck` → 202, job **`01M2QVS6C00HR3WW1K1M496BM2`**,
  `authenticated: true`, `graph_commit 1f9fb286…` (the #74 merge — the service sees the target),
  `artifact_type: partial`, bundle path
  `targets/erdos-402/nodes/erdos-402/attempts/20260917T141927Z-calib-402-f480-partial.lean`.
  Polling every 15 s (`<scratchpad>/sk/precheck.log`).

- 00:23 — `GET https://axle.axiommath.ai/v1/environments` (public, no key) lists `lean-4.33.1`
  with `lean_toolchain: leanprover/lean4:v4.33.1` and `imports: import Mathlib` — the pin's own
  toolchain (`gate-spec.json` `lean_toolchain: leanprover/lean4:v4.33.1`). So the one-line fix to
  `gate/hosted-checkers.yaml` (`lean-4.33.0` → `lean-4.33.1`) would also make the mapping closer to
  exact than the 2026-09-14 probe allowed. Precheck job state at 00:23: `running`.

- 00:25 — `targets/index.json` (`targets-index/v6`) row for erdos-402: `status listed`,
  `claimable true`, `fidelity mechanical-only`, **`step9: review`**, root `erdos-402`; the intake's
  `fidelity/root-1.yaml` is a `mechanical-only` grade by the curator ("No human has read it against
  the informal statement"). So the pull request's `step 9 (a non-author approving review)` job will
  sit unsatisfied until the owner approves (D-4 step 9) — the green I stop at is the
  `gate (steps 1, 2 and 4-8 in the sandbox)` check.

- 00:27 (14:23 UTC) — **Owned precheck `01M2QVS6C00HR3WW1K1M496BM2`: `done`, verdict `pass`** on the
  first round: steps 1 toolchain, 2 paths, 4 kernel-replay, 5 axioms, 6 hazards, 7 witness, 8 deps
  all `pass`; attestation signed by `service`, runner `hosted`; the artifact diagnostic reports
  holes `["h1", "h2", "h3"]` (so the assembly elaborated with exactly the three named holes, none
  unnamed, none the goal restated). ~3.5 minutes from POST to verdict.
- 00:28 (14:24 UTC) — **Submitted:** `POST /submissions` → 201, submission id
  **`01M2QW06ZG6T1ZW656S709HTM0`**, **graph PR #79**
  (`https://github.com/thisisanameforsure/open_proof_network_graph/pull/79`), `artifact_type:
  partial`, node `erdos-402`. Tooling disclosure: model "Claude Fable 5.1 (Claude Code)", harness
  "F15-T14c calibration agent, unattended; literature: Balasubramanian-Soundararajan 1996, Szegedy
  1986, Zaharescu 1987". Watching with `sk/watch.sh` (log `sk/watch.log`).
- 00:29 (14:24 UTC) — PR #79 checks: `gate (steps 1, 2 and 4-8 in the sandbox)` IN_PROGRESS as
  workflow run **`35233227359`** (started 14:23:23Z); `postmerge` SKIPPED (not merged);
  `mergeStateStatus BLOCKED` (checks pending; step 9 review outstanding by design). Read a red run
  with `gh run view 35233227359 --repo thisisanameforsure/open_proof_network_graph --log-failed`.

- 00:32 (14:27 UTC) — **Gate green on PR #79.** Run `35233227359` job `gate (steps 1, 2 and 4-8
  in the sandbox)`: every step `success` (checkout at the merge commit, target/pin lookup,
  pinned network checkout, classify, "Run the gate", "Keep the verdict and attestation"); the
  admission/exhibit/QA sandbox steps `skipped` (a partial proposes no node). Job `step 9 (a
  non-author approving review)`: `failure`, env `AUTHOR: open-proof-network[bot]`, `REVIEWERS:`
  empty (so any non-author approver is eligible), message verbatim:

      ##[error]step 9: this node's root has no fidelity certificate or registry provenance, so a non-author approving review is required before merge (D-4 v3.11; a curator record needs another listed curator's, F08-R8). Approving re-runs this check; the build above is not repeated.

  The workflow run's overall conclusion is therefore `failure` while the required `gate` check
  is `SUCCESS` — the 2026-09-13 finding again (step 9 red within seconds of every App-authored
  submission until a human approves).
- 00:33 — **Finding (for the calibration record):** `GET /submissions/01M2QW06ZG6T1ZW656S709HTM0`
  reports `checks: [('gate', 'completed', 'failure')]`, `reviews: []`, `mergeable blocked`,
  `attestation_note not-merged`. The service surfaces the *workflow run's* conclusion under the
  name `gate`, not the `gate (...)` check run's, so an agent watching through the service alone
  reads a step-9-only red as a failed gate. `gh pr view 79 --json statusCheckRollup` shows the
  truth (gate SUCCESS, step 9 FAILURE). Worth a look by whoever owns `submissions.py`'s
  `runs` field. (My accessor guesses for `artifact_type`/`precheck`/`pseudonym` in that document
  printed `None`; I did not re-derive the key names, so that is not a claim about the document.)

## Continuation (Mike, via the lead, ~45 min more)

Brief in substance: (1) the lead is merging #76–#79 in sequence, one bot commit at a time — touch
no pull request until told the sequence is complete; #79's merge creates `erdos-402--h1/--h2/--h3`
and the next submissions go on those children. (2) Meanwhile prove h1 and h2 in full if they
close (else honest partials; holes before locals; hazard-free ranges), draft the annex text here,
check through `POST /check` first (the mapping is being repointed to `lean-4.33.1`), and fall back
to calling AXLE directly under `lean-4.33.1` if it still answers Unknown environment. (3) When told
the merges are done: read each child's Statement.lean and META.yaml on `origin/main` (note any
`hazards` without `acknowledged_hazards`, F07-Q19), file the annex, precheck and submit on the
children through the service, h1 first; an admission refusal on an unacknowledged hazard is typed
here verbatim and I stop. Same handoff discipline; commit nothing.

- 00:36 — Resumed on the brief above.
- 00:38 — `/check` probe (`target_id: erdos-376`, log `01M2QWVHZGN2GQ4YY5GFZV5HJZ`): still
  `Unknown environment: lean-4.33.0` (mapping not repointed yet; `/hosted-checkers.json` still
  says `lean-4.33.0`, 27 targets now). **Fallback used as authorized:** direct `POST
  https://axle.axiommath.ai/api/v1/check` with `{content, environment: "lean-4.33.1",
  timeout_seconds}` — the network's own request shape from `api/opn_api/axle.py`, which sends no
  API key at Stage 0 (F13-Q5), so the direct call is the same anonymous request minus the
  network's call log. Client: `<scratchpad>/ch/axle.py`.
- 00:41 — **h1 and h2 both prove in full, first round on AXLE (`lean-4.33.1`):**
  `ch/h1.lean` → `okay: true`, no messages (121 ms). `ch/h2.lean` → `okay: true`, warnings only:
  `push_neg` deprecated in favour of `push Not` (kept: it is what the live gate accepted in the
  assembly), the unused binder `h1` (the inherited hole, named by the child's statement, not by
  me), and the `first` fallback's second alternative never executed (`Finset.gcd_div_id_eq_one`
  exists at this Mathlib). Sources under "Child proofs" below.
- 00:47 — Reproduced the gate's hole extractor and `expectedWitnessType` as a metaprogram run on
  AXLE over the merged skeleton (`ch/holes-pp.lean`, result `ch/holes-pp.axle.json`): the exact
  `closed_type` strings the post-merge job will write into `erdos_402__h1/h2/h3` and the witness
  types step 7 will expect. Precedent read: `erdos-412--h1/Statement.lean` (same `theorem
  <id with -->_> : <printed type> := by\n  sorry` shape), its `Witness.lean` slot is a
  placeholder `theorem witness : True := by sorry` (step 7 computes the real expected type).
- 00:50 — **Finding (gate defect, for the calibration record; F07/F03 family, not mine to fix):
  a hole whose type carries ℚ coercions is written back as a different statement.** The
  extractor prints `closed_type` with default `pp` options, so h2's and h3's conclusion prints as
  `∃ a ∈ A, ∃ b ∈ A, ↑(a.gcd b) ≤ ↑a / ↑A.card` — bare `↑` with no type ascription. Re-elaborated
  as the child's `Statement.lean` (tested on AXLE, `ch/h2-stmt.lean`, `ch/h3-stmt.lean`: both
  elaborate with no error), the `↑`s resolve to the identity coercion ℕ → ℕ and the child becomes
  the **ℕ-division** statement `a.gcd b ≤ a / A.card` — visible in the failed h2-proof run, whose
  context shows `hprim : … → ∃ a ∈ B, ∃ b ∈ B, a.gcd b ≤ a / B.card` and the goal
  `g * (a / g).gcd (b / g) ≤ a / A.card` with no casts (error verbatim: `Tactic \`rewrite\`
  failed: Did not find an occurrence of the pattern ↑(?m * ?n) in the target expression
  g * (a / g).gcd (b / g) ≤ a / A.card`). Mathematically the two are equivalent (an integer
  `g ≤ a/n` in ℚ iff `g ≤ ⌊a/n⌋`), so the node is not false — but it is **not the hole's type**:
  the kernel accepted the assembly with the ℚ holes, and D-31's finalization ("the assembly with
  each sorry replaced by its hole's theorem") cannot use an ℕ-typed child. h1 has no coercions
  and round-trips faithfully. Silent, because the statement elaborates. Fix belongs to the hole
  writer: print with `pp.coercions.types true` (prints `(↑a : ℚ)`) or compare the child's
  elaborated type against the hole's `closed` Expr before writing. Also seen: the printed
  *witness* type (`∃ A m a b, 0 ∉ A ∧ …`) does not re-elaborate on its own (`a`'s type unknown for
  `a.gcd`) — harmless, since step 7 compares Exprs, but it means a witness cannot be written by
  copying the expected type as printed; write the binder types explicitly.
- 00:51 — **Decision:** h1's child is faithful, so h1 gets witness + proof as soon as the children
  exist. For h2 (and h3) I prepare the witness and proof against the statement the child will
  actually carry (the ℕ form), so they are ready, but whether to submit a proof of a mis-generated
  statement is the lead's call; I submit h2 only if told to, and log it either way.

## Next

- **Lead:** approve PR #79 as a non-author (re-runs only the step-9 job, ~5 s), then merge and wait
  for the bot commit. After the merge the post-merge job creates `erdos-402--h1`, `--h2`, `--h3`
  from the holes (with the parent's `open Filter` line, per the 0401858 fix).
- If anything on PR #79 goes red after a branch update: read `gh run view <id> --repo
  thisisanameforsure/open_proof_network_graph --log-failed`, record the error verbatim here, fix
  `<scratchpad>/sk/partial.lean`, precheck again (`sk/precheck.sh`), submit again (`sk/submit.sh`,
  a new PR; the old one is the lead's to close).
- Not done, for the lead or a successor: no annex was filed for the skeleton (the informal
  decomposition above would be its text; `POST /annexes` needs the token); the fast-check mapping
  fix (`gate/hosted-checkers.yaml`: `lean-4.33.0` → `lean-4.33.1`, then a deploy); after the
  merge, check the three hole children the post-merge job writes (`erdos-402--h1..h3`) for
  F07-Q19 (`div-zero` on h2/h3 at `↑a / ↑A.card`, no `acknowledged_hazards`) and witness them in
  order (`{1}` with `m = 1` for h1; `{1}` plus a proof of h1 for h2; `{1}` plus proofs of h1 and
  h2 for h3).
