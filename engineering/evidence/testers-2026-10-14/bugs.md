# Testers 2026-10-14: erdos-1094, consolidated and verified findings

Three black-box agents, 11:05Z to 11:35Z. Their logs are `A.md`, `B.md` and `C.md`. Every finding below was checked
by the lead against the graph history, the live service or the network source at `origin/main`. The local `main`
is 170 commits behind `origin` and was not used for this.

## What landed (as of 11:34Z)

Thirteen graph pull requests (#511–#523), none needing a human. Five had merged by 11:34Z; the other nine were
green or gating and waiting in the merge queue. All nine are on one target, so they merge one at a time.

| Agent | Merged | Waiting in the queue |
|---|---|---|
| A `t1014-x` | #511 annex (the van Doorn–Tang four-case map) | #519 skeleton on `--h2--h2--h2`, four holes, each "¬BHP ∨ one case of n"; #521 literature `known` (vdT 2026) |
| B `t1014-y` | #516 partial on `--h2--h1--h1`, making `--h2--h1--h1--h1` | #514, #515 partials (n/gcd(n,k) is prime); #517, #518 glosses; #520 annex |
| C `t1014-z` | #512 literature `known` on `--h2--h2--h1` (BHP 2001, p. 562); #513 literature `known` on `--h2--h1--h4` | #522, #523 skeletons (p = 3 split on both halves of the sieve) |

Mathematical value:
- **A's #519.** This is the start of the van Doorn–Tang port. Its assembly is fully proved, and each of its four
  holes is one range of n, so each is strictly narrower than the parent. The port survey (`A/port-survey-4.33.1.txt`)
  found 36 of their declarations failing at Lean 4.33.1, mostly "`ring_nf` made no progress" and `rw` misses. These
  need fixing one site at a time, not a rename.
- **C's #522 and #523.** These are real decompositions. p = 3 closes the cases with n mod 3 &lt; k mod 3, and what is
  left are two residue classes, each narrower than the parent. That the holes are true is checked numerically only,
  for k ≤ 600.
- **B's three partials.** Each proves a real lemma in the kernel: from k² ≤ n and minFac C(n,k) &gt; n/k, the number
  n/gcd(n,k) is prime. But each hole is its parent's statement with that consequence added as a hypothesis. Given
  the assembly, the hole is therefore *equivalent* to its parent, not easier, and B says so in the annex. See
  observation O1.
- **Literature proposals.** #512, #513 and #521 are proposals; each waits on a steward or curator to confirm from
  `/me/`. C read the BHP paper's PDF for #512. The reasoning behind #513 (a corollary of Konyagin through
  `--h2--h1--h1`) and #521 (vdT's Lean matches the node) is the agents' own, and they say so in the records.

## Ranked

1. **B1, MEDIUM. `holes[].became` is null for every merged partial on the live record.** Confirmed.
   - **Seen:** `GET /submissions/<id>` gives `became: null` for every hole of #508 and #510, merged this morning
     with all six holes on `main` for hours, and for #516. Yet `targets/erdos-1094/graph.json` (graph/v9) on `main`
     carries `decompositions: [{holes: [{name: h_gp, node: erdos-1094--h2--h1--h1--h1}]}]`.
   - **Cause:** `api/opn_api/pending.py::_decomposition_nodes` (F09-T72) matches a decomposition to its submission
     by the attestation's `artifact_hash`. It returns `{}` when that value is not a string.
     `gate/opn_gate/attestation.py:53-60` sets `artifact_hash` only for an alternate or for `Proof.lean`, so every
     partial's attestation carries `null`. That is all 13 partial attestations on the graph since #331, at every pin.
   - **Why the tests missed it:** they must have built an attestation with a hash. A fixture with more structure
     than the live record is the 2026-09-12 lesson again.
   - **Fix direction:** match on step 2's `partial-submission` diagnostic, whose `details.path` names the partial
     file and is already in every partial's attestation. Do not make the gate hash partials: `artifact_hash` on a
     partial would read as a proof (F03-Q7). Red test: a live-shaped attestation with `artifact_hash: null`.
   - **Who it hurts:** this is the field the 2026-10-09b tester asked for (C1). Today B read `became: null` two
     minutes after the merge and had to go and look on `main`.

2. **O1, observation (the owner's call, not a bug).** Some single-hole partials add a node equivalent to their
   parent. B's #514–#516 are honest and say so. But each adds a frontier node that is the parent problem plus a
   hypothesis the assembly proves. Under v3.35 such a hole meets the circularity exhibit, since the parent gives the
   hole trivially and the hole gives the parent through the assembly. So at most it would be *labelled* circular,
   and only once someone files the claim. The kernel-checked lemma is real progress. The extra frontier nodes are
   not. The guide could say plainly that a hole of the form "the parent plus a proved consequence" is a
   restatement, and that the lemma's value is in the assembly and the annex.

3. **F1, MINOR friction. The provenance field has two names across MCP write tools.** Confirmed.
   - **Code:** `submit_proof` forwards `tooling` (`api/opn_api/mcp/writes.py`, `present(... "tooling" ...)`), while
     `propose_literature` and `submit_informal_annex` take `model_and_tooling`.
   - **Effect:** C sent `model_and_tooling` to `submit_proof` and got `arguments-invalid`. The refusal opened
     nothing, and C recovered.
   - **Fix direction:** accept `model_and_tooling` as an alias, or name the right field in the refusal.

## Feature requests (verified as not bugs)

- **A claim outlives its merged partial (B).** By design: the guide's l.477 says the claim "expires on its own".
  The request is to release or flag it when the holder's work on that node merges.
- **One precheck per skeleton (A).** A hole's witness type is known only from a precheck, so carrying witnesses
  costs a second full precheck of about 5 minutes. Requested: a fast-check mode that reports holes and their
  witness types.
- **Checking a large outside development piecewise (A).** vdT's file is 330 kB, over the 200 kB cap, and 200-line
  chunks can time out.
- **Smaller ones:**
  - a warning when `check_lean` is near its 20 s budget (B: skeletons took 19–29 s);
  - `get_submission` for several ids in one call (C);
  - echo the numerical range of the parent's annex beside each hole in a precheck result (C).

## Not bugs

- **B: `POST /tokens` with an empty body hung for 120 s.** Re-run by the lead at 11:31Z: `400 pseudonym-invalid`
  in 0.53 s, and the same for `{}`. The stall was this laptop's connection.
- **All agents: calls stalling for 20–300 s.** The worst was C's TLS handshake timeout at 300 s on 11:27Z. The
  lead's curl probes at 11:04Z and 11:31Z connected in 0.16–0.5 s. This is the laptop's path to API Gateway, as
  recorded in the 2026-09-21 and 2026-10-08 entries.
- **B: `Nat.succ_mul_choose_eq` is gone at this pin.** That is a Mathlib rename (now `Nat.add_one_mul_choose_eq`),
  not the network.
