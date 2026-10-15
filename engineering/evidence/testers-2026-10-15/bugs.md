# Testers 2026-10-15: erdos-1094 with helper lemmas and the 1000k cap, consolidated and verified findings

Three black-box agents, MCP only, 01:56Z to 02:56Z, on network 7e153a12 (F00-T11, F02-T15, F13-T36), graph re-pin
232e76e96. Logs are `P.md`, `Q.md` and `R.md`. The lead checked every claim below against the graph at `edadad318`.

## What landed

Four graph pull requests, all merged with no human.

| PR | Agent | Node | Kind | Result |
|---|---|---|---|---|
| #527 | P `t1015-p` | `--h2--h2--h2--h2--h1` (vdT `med_card_bound`) | complete proof | merged 02:13:08Z; attestation passes every step; node `proved` |
| #528 | R `t1015-r` | `--h2--h2--h2--h3` (vdT mediumlarge, ¬BHP ∨ case) | partial | merged 02:27:58Z; hole `h_kon` became `--h2--h2--h2--h3--h1` (`konyagin_application`) |
| #529 | Q `t1015-q` | `--h2--h2--h2--h4` (vdT large, ¬BHP ∨ case) | partial | merged 02:39:52Z; hole `h_kon` recorded as a **lemma** on `--h3--h1`, not a new node |
| #530 | R | `--h2--h2--h2--h3--h1` | partial | merged 02:50:21Z; hole became `--h2--h2--h2--h3--h1--h1` (`konyagin_thm`) |

Where the van Doorn–Tang branch now stands:
- **The small case** (`--h1`) has been proved since yesterday.
- **The medium case** (`--h2`) has every hole proved, but the node itself still reads `ready`. A partial's
  parent closes only when someone submits its closing proof, naming the proved hole. Nobody has yet. This is the
  cheapest next proof on the target.
- **The mediumlarge and large cases** (`--h3`, `--h4`) now rest on one node, `konyagin_thm`
  (`--h2--h2--h2--h3--h1--h1`), through `konyagin_application`. This is vdT's lattice argument, about 136
  declarations and 208 kB.

## Did the change work

Yes. Helpers were decisive, and the cap was needed once.

| Agent | Largest declaration | Before the change |
|---|---|---|
| P, `med_card_bound` chain | `medFiber_card_le` 91,348; the theorem 1,820 | 328k inlined, over the 200k cap |
| Q, large-case chain (26 helpers) | `large_r_data` 95.3k; the theorem 776 | not attempted yesterday |
| R, `konyagin_application` as one helper | 271k | over the old cap; fits the new one |

`private noncomputable def` passed the helper rule, as it should. No agent hit `helper-forbidden` by mistake.

## Ranked

1. **K1, guide gap. Where the helper block goes, when the statement opens with a module doc.** The rule is right:
   the block goes after the file's header, so above a hole's `/-! … -/` module doc it diverges. R hit
   `header-diverges` there. The guide says "directly before the statement's theorem", which is true but does not
   say the header includes the module doc. One sentence fixes it.
2. **K2, guide gap. `expected_new` is a plan, re-checked at merge.** Q's receipt planned `--h4--h1` as new. The
   post-merge job matched it to R's node, which had merged in between, and recorded it as a lemma. That outcome
   was right. Q spent time worrying about a duplicate, and R predicted one. F13-Q36 already says the receipt
   *expects* while `became` *reports*; the skeleton section could say it where agents read it.
3. **K3, friction. The fast check cannot see a large development whole.** vdT's `konyagin_thm` is 208 kB, over the
   200 kB limit, and chunks of about 13 kB hit the 20 s budget. P and Q both asked for a "check one declaration
   with everything earlier assumed" mode or a library prefix by hash. A precheck has no such limit, but costs 4–6
   minutes a round.
4. **K4, friction. A claim on a held node returns 201** with the holder under `others` (Q, P). This is by design,
   since claims are advisory. Two agents claimed a node already posted on the board, and both released it at
   once. Asked: a warning in the answer.
5. **K5, observation, not verified.** Q reports three blocked holes (`--h2--h2--h3--h1`, `--h2--h1--h1--h1`,
   `--h2--h1--h4--h1`) whose witness slots are `True := by sorry`, so proposing `trivial` would unblock each.
   These are yesterday's B partials. The lead has not checked the witness types.

## The lead's own errors

- The brief named `../testers-2026-10-14/A/port-survey-4.33.1.txt`, which exists in the shared checkout but not in
  the worktree the agents read (Q). P's chunk survey of `konyagin_thm` at 4.33.1 now replaces it.

## Not findings

- **Slow calls of 40–133 s, one TLS handshake timeout, and P's local stall from 02:26Z to 04:09Z.** These come from
  the laptop's path and session. P's claim was released late because of the stall, and nothing was started after it.
- **One `504 check-timeout` on a `heartbeats: true` check (Q).** The same request passed a minute later.
