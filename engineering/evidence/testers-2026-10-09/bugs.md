# Testers 2026-10-09: erdos-1094, consolidated and verified findings

Two black-box agents worked through MCP from 12:40Z to 13:40Z. Their logs are `A.md` and `B.md`. Every finding
below was checked by the lead against the graph history, the live service or the network source.

## What landed

Fifteen graph pull requests merged, none needing a human: A: #462, #466, #468, #469, #475, #476. B: #461, #463,
#464, #465, #467, #470–#473. #474 was a deliberate wrong-direction circularity probe, which B withdrew.
- New nodes: `--h2--h1` (k² ≤ n < k³, follows from Konyagin's bound), `--h2--h2` (n ≥ k³, the sharper open part),
  `--h3--h1--h1` (k even) and `--h3--h1--h2` (k, n odd).
- The two assemblies are kernel-checked, and neither creates a circular hole. On `--h3--h1`, the case p = 2 is
  proved in the assembly.
- Two literature proposals (`--h3` known, `--h2--h1` known) and one (`--h2` open) wait on a steward or curator.
- Yesterday's P1 (fresh hole cannot be prechecked) is confirmed fixed live: B prechecked a 15-minute-old hole and
  it reached step 4.

## Ranked

1. **B1, MEDIUM. A wrong-direction circularity claim opens a pull request.** Confirmed.
   - **Code:** `post_defect_claims` → `preflight_exhibit(relational=True)` returns `skipped` without compiling
     anything (`api/opn_api/checks.py`, `found = None if relational`).
   - **Gate:** refused #474 `circular-direction` 3.5 min later, so nothing reached the record.
   - **Status:** F13-Q23 lists circularity exhibits as "still reaching the gate", so this is a known gap, not a
     regression.
   - **Why it ranks first:** the owner's Q22 principle ("no pull request for what the service can refuse first")
     applies to it.
   - **Description:** the `file_defect_claim` tool description says "the reverse is refused circular-direction"
     beside "the exhibit is compiled first", which reads as an immediate refusal. The receipt's `skipped` carries
     no reason.
   - **Fix options:**
     - (a) Run the direction check before the PR opens. The gate's check compares the exhibit's declared type
       against hole → ancestor.
     - (b) At minimum, say in the tool description that circularity exhibits are checked only by the gate, and
       give `skipped` a reason.
2. **B3, MINOR–MEDIUM. A fresh hole's products name a commit that does not hold the hole.** Confirmed.
   - **Record:** `get_node erdos-1094--h2--h1` gives `context.rendered_from` `93c88d5`, which has no `--h2--h1`
     directory. The bot commit `54630ba8` wrote it.
   - **Guide:** line 74 tells HTTP clients to read files on the raw host at `frontier.json`'s `rendered_from`.
     For every freshly written hole that read is a 404 until the next merge on the target re-renders.
   - **Relation to yesterday's P1:** this is the part P1's fix (F06-T14) left alone. Precheck was fixed by pinning
     differently, but the published pointer was not.
   - **Fix direction:** name the commit that carries the products, or have the guide say "read at `main`'s sha".
3. **B4, MINOR. `PROTOCOL_VERSION` is stuck at 3.28; the decisions doc is at v3.35.** Confirmed.
   - **History:** `gate/opn_gate/products.py:61`. Every application from v3.21 to v3.28 bumped it, and v3.29–v3.35
     did not.
   - **Where it shows:** `info.json` (a graph product) and the MCP `serverInfo` version both publish it, so the
     record says 3.28.
   - **Fix:** a version bump with the three product goldens regenerated (the 3.21/3.22 precedent), live at the
     next re-pin.
4. **A1, MINOR. The queue block says `stale: false` for a listing read before the PR existed.** Confirmed.
   - **Record:** #468 was created at 12:56:21Z. Its `get_submission` queue reads
     `read_at 12:56:08Z, position null, of 1, stale false`.
   - **Cause:** staleness measures the listing's age, not whether the listing predates the pull request.
   - **Fix direction:** stale when `read_at` < the PR's `created`, or a reason beside `position: null`.
5. **B2, MINOR (documentation). The call log's `okay` is the checker's, not the caller's.** By design but not
   written down.
   - **Code:** `gate_verdict`'s docstring says "the checker's own `okay` stays verbatim in `result` and in the call
     log", so `get_check` shows `okay: true` for a check whose answer was `okay: false` (sorry-present).
   - **Guide:** never says so.
   - **Fix:** log both (`okay` and `checker_okay`), or one guide sentence.

## Not bugs

- **A2:** the `-- hole:` line in the `Witness.lean` of the four holes written 2026-10-08. F07-T75 (`dc81e38`) fixed
  the writer, and today's two holes are clean. Records are not rewritten (derive, never rewrite), so this is legacy
  data.
- **D1:** `approach-record/v1` requires `contributor`, which the service sets. The schema describes the stored record,
  not the request. At most a guide sentence: `get_schema` returns record schemas.
- **D2:** no `Mcp-Session-Id`. The server is stateless by design, and A read it that way. The guide could say that
  `initialize` once is enough.
- **D3:** `list_frontier` filter `target` vs `target_id`. Tester error, and the refusal names the fields.
- **A3, A4, E1–E3:** the laptop's environment. Stalls of 20–116 s were all in TCP connect (19/35/67/75 s, macOS SYN
  retransmits), while the service answered in 0.5–6 s. `timeout` and `sympy` are missing locally.

## Features (from A.md, B.md)

- A signal that a merged node now exists (no more polling `get_node` for about 6 min).
- A partial's receipt naming the node ids its holes will get.
- An option to queue a precheck refused `products-pending` instead of resending it by hand.
- `include: []` on `get_node` is mentioned only in the MCP appendix.
- Collect postmortems' missing-lemma requests across nodes.
- `skipped` pre-flights should carry a reason (B1).
