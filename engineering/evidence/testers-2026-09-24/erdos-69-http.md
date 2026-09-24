# erdos-69 tester (plain HTTP) — 2026-09-24

Start: 2026-09-24T12:25:13Z. Stop new work at 13:20Z.

## Log

- 12:25:13Z `curl https://openproofnetwork.org/problems/erdos-69/` → 200; `curl https://api.openproofnetwork.org/health` → 200.
- 12:25Z Read the problem page. 11 statements; open ones: `erdos-69` (root), `erdos-69--h2-v2`, `erdos-69--h2-v2--h1-v2`, `erdos-69--h2-v2--h1-v2--h4`. Everything else proved or superseded. Page is clear about which statement is which and what "superseded" means.
- 12:26Z Read `/docs/` (AGENTS.md rendered). No local Lean in this container (`which lean lake elan` → nothing), so the git path is out; HTTP path only, with `POST /check` (AXLE) for iteration.
- 12:26Z `GET /frontier.json` → rendered_from `ac45b22a…`; the four erdos-69 entries all claimable, **no active claims** (so the "other agent" had not claimed yet).
- 12:26Z Read prior work through raw.githubusercontent at the rendered commit: approach record `20260923T145333Z-t0923-69-b.yaml` (outcome blocked) and the annex on h4 (`1a02e7ac…md`): h4 is *equivalent* to the target (for each b, h4 at b ⇔ b·S ∉ ℤ). I re-derived that myself and agree: with N = 0, (b·A mod 2^k)/2^k → frac(b·S), so h4 is just irrationality restated. Known proofs: Tao–Teräväinen 2025 (unconditional), Pratt 2024 (prime k-tuples). Neither is in Mathlib.
- 12:26:47Z `POST /precheck` tutorial node (no token) → 202 in 5.9 s, job queued. Done/pass at ≈12:28:50 (≈2 min). Steps listed 1,2,4,5,6,7,8 (no 3 on the hosted runner — expected per guide? guide does not say step 3 is omitted from the precheck step list; minor).
- 12:29:00Z `POST /tokens` (tutorial proof) → 201, pseudonym `agent-e69h-0d8d`. Smooth.
- 12:29:08Z `POST /claims {node_id: erdos-69--h2-v2--h1-v2--h4, ttl_hours: 1}` → 201 in 0.48 s.
- Observation (not a bug, a wish): h4's frontier entry says attempts=0, refuted_route_classes=[] although an annex (and the parent's postmortem) already establish that h4 is circular. A prover filtering on the frontier fields alone would see a fresh, never-tried hole. Only the annex_present flag hints otherwise.
- Observation: `CONTEXT.json` for h4 says `rendered_from 9ac359a4…` while frontier.json says `ac45b22a…` — two products, two commits. Probably fine (CONTEXT.json only re-rendered when the node changes) but not explained in the guide.
- 12:29:47Z `POST /check` (mode check, target erdos-69, no node) with `decide` on ∑_{j<4} ω(1+j)·2^(3−j) = 7 → 200 in 0.8 s, okay=false, clear Lean error ("decide failed … did not reduce"). My mistake (ω is not kernel-reducible), not the network's. Fast check is genuinely fast (≈1–3 s); very pleasant.
- 12:30Z Two more `/check` calls: ω 2, ω 3, ω 4 via `cardDistinctFactors_apply_prime(_pow)` and the full b = 1 instance of h4's conclusion (N = 0, k = 4: A = 7, 7 + log2 5 + 1 < 16) → okay=true, lint=[]. So h4 is decidable **for each fixed b** by a window computation, but not uniformly — see the annex's equivalence.
- 12:30:50Z `/check` with node_id h4 and the statement body `intro hL hsplit hpos hlog b hb; done` → 200 in 2.9 s, prints the goal cleanly; `inlined_defs` = the node's Context. Good.
- 12:31:20Z `POST /postmortems` on h4 (route_class computational, outcome refuted-route, failure_class route-dead-ends, with terminal goal state) → 201 in 3.5 s, **graph PR #175**, path `attempts/20260924T123120Z-agent-e69h-0d8d.yaml`.
  - **My mistake**: the postmortem's detail cites `log_id 01M39P9DK0HFD11SNDB2RA968W "and the following call"` as the check that elaborated the b = 1 instance. That log id is the *first* call, the failing `decide`; the passing call was two calls later and I did not print its log_id. The mathematical claim is correct (and re-checkable in 1 s), but the citation is imprecise. Postmortems may never be edited, so this stays; recorded here. Wish: `/check` answers could echo a stable hash of the checked text so a record can cite the text, not a call.
- 12:31:38Z `GET /submissions/<id>` for PR #175 → gate `in_progress`, `waiting_on: gate`, `attestation_note: no-attestation-for-mode`. Clear.
- 12:32:03Z Claim edge cases (all as the guide says, messages good):
  - superseded `erdos-69--h1` → 409 `node-not-open`, names replacement `erdos-69--h1-v2`. 
  - proved `erdos-69--h1-v2` → 409 `node-not-open`, status proved.
  - ttl 1000 → 400 `ttl-above-cap` (cap 168). no token → 401. unknown node → 404 `node-unknown` with a helpful "merged in the last few minutes" note. bogus precheck job → 404 `job-unknown`.
  - **Bug (minor, reproduced once)**: claiming h4 a *second time with the same token* → 201 and a second active claim; `/frontier.json` then listed `agent-e69h-0d8d` twice on h4 (`[(agent-e69h-0d8d, 13:29:08), (t0924-69m-8709, 13:31:48), (agent-e69h-0d8d, 13:32:05)]`). Expected: 409 "you already hold a claim" or an idempotent extension of the existing one. Released the duplicate at 12:32:14Z (200). A second DELETE of the same claim → 200 again with the same body (idempotent; fine, though 404/410 would tell a script its id was stale).
- 12:32Z The other agent (`t0924-69m-8709`) claimed h4 at 12:31:48Z, 2.5 minutes after my claim and 30 s after my postmortem opened. Racing is allowed; noting that we are both on the one open hole because it is the only open non-root work on this target.
- 12:32:36Z `/check` verify mode on h4 with `exact ⟨0, 4, sorry⟩` → okay=false, lint `sorry-present` with a good message; result echoes the goal at the sorry. Also AXLE's Mathlib style linter warns that `erdos_69__h2_v2__h1_v2__h4` "contains '__'" — noise on every gate-generated hole name that a contributor cannot fix (wish: the service filters `linter.style.nameCheck`).
- 12:32:4xZ `/check` witness mode on h4 with no content → 200 okay=true, prints expected type. Fine.
- 12:33–12:36Z Decided to make the annex's "h4 ⇔ target" argument machine-checked rather than leave it prose. Found in the guide (Skeletonization section, then `/docs/defect-claim.html`) that exactly this has a mechanism: a **`circular-decomposition` defect claim** (defect-claim/v3, D-16 v3.21) with `ancestor` and a one-theorem exhibit `<ancestor> → <hole>`; once merged the hole leaves the frontier as `circular`. Wrote it through `/check`:
  - 12:33:4xZ helper `∃ k, b(k+1) < c·2^k` — first try wrong `simpa` shape (my mistake), second okay (`log_id 01M39PGP0GYZABDFBYWRQW503N`).
  - 12:34:19Z the converse (b·S ∉ ℤ ⇒ h4 at b, N = 0) — **elaborated on the first try except one no-op `simp`**; 12:34:30Z okay (`01M39PJ1YRCGT4B7ESYSAE7VGC`).
  - 12:36:04Z assembled one theorem `erdos_69_h4_circular : (root statement) → (h4 statement)`; index-shift step failed (my mistake), fixed; 12:36:24Z **okay=true** (`01M39PNGA0VCMVPT829BRKPQYQ`). Summability of the tail comes for free from `hpos` (a non-summable tsum is 0), and the root's `ω (n+2)/2^(n+2)` is the N = 0 tail after dropping ω 1 = 0.
  - Every `/check` answer came back in 1–3 s. This is the best part of the network for an outsider with no local Lean.
- Doc note: the circularity mechanism is only discoverable deep in the Skeletonization section and on a separate page; the `/docs/` guide's "defects/" row still says only "append … a defect claim (D-16)". The `POST /defect-claims` body is not in AGENTS.md at all (only its MCP name); I found it on `/docs/defect-claim.html`. `POST /defect-claims {}` answers a clear 400 `defect-class` listing the classes.
- 12:36:47Z `POST /defect-claims {stmt_ref: erdos-69--h2-v2--h1-v2--h4, class: circular-decomposition, ancestor: erdos-69, line: 9, exhibit: <one theorem, root → h4>}` → 201 in 3.9 s, **graph PR #187**.
- 12:36:59Z PR #175 (postmortem) **merged** without anyone touching it (5.5 min from filing). 
  - **Bug (minor, reproduced on two PRs)**: `GET /submissions/<id>` returns `pull_request.runs[].jobs` while the PR is open but *omits the `jobs` key* once it is closed/merged; a client that reads `r['jobs']` (as I did) crashes on a merged submission. Expected: the same shape in both states (empty list if unknown).
  - `pull_request.mergeable_state` reads `"unknown"` on a merged PR — harmless but meaningless.
- 12:40:06Z PR #187 gate **success** (~3 min, including the sandbox elaboration of the exhibit); `waiting_on: branch-update`.
- 12:40:26Z Second exhibit, root → `erdos-69--h2-v2--h1-v2` (N = 0; summability derived from the root itself, since the tsum of a non-summable series is 0, which is not irrational) → okay on the first try (`01M39PWWMGWNEG9QPQG75NNW9Y`).
- 12:40:39Z `POST /defect-claims` circular-decomposition on `erdos-69--h2-v2--h1-v2` (ancestor erdos-69, line 8) → 201 in 5.2 s, **graph PR #194**. That node's own postmortem (agent-e69w-9550, 2026-09-18) already called the N = 0 route circular in prose; this makes it a checked record.
- Judgment, **not filed**: `erdos-69--h2-v2` (h1 → Irrational ∑ 1/(2^p−1)) is also no easier than the root once h1 is known, so a third circularity claim would type-check. I did not file it: that would take every open non-root statement of the target off the frontier while another agent is working here, and the Lambert-series reformulation is the textbook first step of the known proof, so calling that hole "circular" is a curator's call rather than a mechanical fact.
- 12:41:09Z Released my h4 claim (`DELETE /claims/<id>` → 200). Work on h4 is done: postmortem merged, circularity claim gated green.
- 12:41–12:51Z Both #187 and #194 gate-green but `waiting_on` flips `branch-update` ↔ `merge` every 30–90 s for 10+ minutes. `GET /submissions.json` at 12:51:20Z shows **26 open PRs** (#177–#202, several testers at once), so this is the strict up-to-date queue serialising merges, not a hang. Wish: `/submissions/<id>` could say the queue position ("3rd to merge") instead of a state that looks like thrashing.
- 12:51Z **My mistake (duplicate work)**: the queue shows the other agent (`t0924-69m-8709`) had filed circular-decomposition claims at 12:33:53Z on `erdos-69--h2-v2--h1-v2` (#179, ancestor `erdos-69--h2-v2`) and at 12:33:56Z on `erdos-69--h2-v2` (#180, ancestor the root), plus an annex on the root (#186). My #194 (same node as #179, ancestor the root) duplicates #179. I had checked claims (none on that node) but not `submissions.json` before filing. Read their records through raw.githubusercontent at the PR heads. My #187 (h4) is not duplicated. The other agent *did* make the call on `erdos-69--h2-v2` that I declined above.
  - Network wish (would have prevented it): `POST /defect-claims` could answer with a warning when an open claim of the same class on the same node is already in the queue; and claims only cover proving, so there is no way to say "I am filing a defect on X".
  - There is no route to withdraw a submission (`/` lists none), so #194 will merge as a duplicate unless a curator closes it.
- 12:53:09Z `GET /frontier.json` (rendered_from `4a7d60a4…`) → h4 **gone** from the frontier; the other agent's h4 claim gone with it; my postmortem not visible anywhere because the entry is gone.
- 12:54:09Z `POST /claims` h4 → 409 `node-circular`: "a merged circularity claim (D-16) proves a node above it implies it … under nodes/…--h4/defects/". I first read this as a bug because my #187 was still open (`/submissions/<id>` → open, merged=false) and the committed `frontier.json`/`graph.json` **at the very commit the service names as `rendered_from` (4a7d60a)** still listed h4 as ready with cause null.
- 12:55:34Z Resolved from the site's h4 page: the claim that took it off is **the other agent's**, `defects/20260924T123205Z-t0924-69m-8709.yaml`, filed 12:32:05Z and already merged (its PR, presumably #176, had left the queue by 12:51). So the 409 is **correct**, and **my #187 duplicates it** (filed 4.5 min later). With #194 duplicating #179, both of my circularity claims are duplicates. My own failure: I checked claims before filing but never `submissions.json` or the node's `defects/`, and the frontier at 12:36 still showed h4.
  - What *is* confusing (network, minor): the service's `/frontier.json` says `rendered_from: 4a7d60a` while the committed `frontier.json` *at 4a7d60a* says `rendered_from: 7543e7a` and still lists h4. The service is evidently deriving from the tree at 4a7d60a (where the defect had merged) rather than serving the committed products; the field name makes the two look like the same thing. Wish: call the service's field `read_at` or document the overlay.
  - Also note the claims registry: my h4 claim and the other agent's coexisted for 3 min while *they* had already filed a circularity claim on the node; a claim note ("filing a defect", free text) would have told me.
- Environment, not network: two `Connection reset by peer` on `api.openproofnetwork.org` (12:52:07Z, 12:55:2xZ); the local agent proxy reported `ws_closed_mid_exchange` on its own tunnel. Retries succeeded.
- 12:56:04Z Site h4 page shows my postmortem: "Attempts 1 recorded. Routes refuted: computational. Failure classes: route-dead-ends 1." Good. It stays visible on the node page even though h4 has left the frontier.
- 12:56–13:05Z #187 and #194 sit at `waiting_on: merge` (gate green) for 12+ minutes. `submissions.json` at 13:05:31Z: still 26 open, head of queue #179; only #178 merged since 12:54. **Throughput ≈ one merge per 5–10 min with 26 queued** means about 2–4 hours for a green, no-build append to land during a busy hour. Two more transient non-JSON/`Connection reset` responses (12:58:00Z, 13:02:58Z) that the agent proxy attributes to its own tunnel.

## Summary

Start 12:25:13Z; summary written 13:06Z. Plain HTTP only, no local Lean; every Lean check through `POST /check` (AXLE).

### What landed
- **Graph PR #175, merged 12:36:59Z** — typed postmortem on `erdos-69--h2-v2--h1-v2--h4` (`attempts/20260924T123120Z-agent-e69h-0d8d.yaml`; route_class computational, outcome refuted-route, failure_class route-dead-ends, with the real terminal goal). The site now shows the hole's refuted route.
- **Graph PR #187** (open, gate green, in the merge queue) — circular-decomposition defect claim on h4, ancestor `erdos-69`, exhibit `erdos_69_h4_circular : root → h4`. **Duplicates** the other agent's claim (`20260924T123205Z-t0924-69m-8709.yaml`), which merged first.
- **Graph PR #194** (open, gate green, in the merge queue) — circular-decomposition claim on `erdos-69--h2-v2--h1-v2`, ancestor `erdos-69`. **Duplicates** the other agent's #179 (ancestor `erdos-69--h2-v2`).
- Token `agent-e69h-0d8d` via the tutorial precheck; claim on h4 taken 12:29, released 12:41.

### What I proved (checked by AXLE only: non-authoritative, no gate run except inside #187/#194's green gates)
- `h4_at_one`: h4's conclusion at b = 1 (N = 0, k = 4).
- The converse of the skeleton's assembly: b·S ∉ ℤ ⇒ h4 at b. Assembled into one theorem, **root → h4**, which the sandbox gate elaborated green in #187. So the annex's "h4 is equivalent to the target" is now a kernel-typed fact, not only prose.
- root → `erdos-69--h2-v2--h1-v2` (gate green in #194).
- **No progress on the mathematics of Erdős 69 itself.** Every open statement under the root is a restatement of irrationality. The honest remaining route is Tao–Teräväinen 2025 (unconditional), which is not in Mathlib and far beyond an hour.

### Bugs and friction, priority order (network's)
1. **Merge-queue throughput** (13:05Z): gate-green appends wait 12+ min at `waiting_on: merge`, with 26 PRs queued and about one merge per 5–10 min. `waiting_on` flips `branch-update` ↔ `merge` in a way that looks like thrashing. Wish: queue position in `/submissions/<id>`.
2. **No duplicate warning for defect claims / no way to signal "filing a defect on X"** (12:36Z, 12:40Z): claims cover proving only, and `POST /defect-claims` accepts a same-class claim on a node that already has one merged (h4) or queued (#179). There is also no route to withdraw a submission. Both of my circularity claims are duplicates as a result (I share the blame: I did not check `submissions.json`/`defects/` first).
3. **Same pseudonym can hold two active claims on one node** (12:32:05Z, reproduced once): the second `POST /claims` → 201, and the frontier lists the pseudonym twice.
4. **`/frontier.json`'s `rendered_from` means something different from the committed file's `rendered_from`** (12:53Z): the service said 4a7d60a and omitted h4, while the committed frontier at 4a7d60a (rendered_from 7543e7a) still listed h4. Correct behaviour (the service derives from the newer tree), but it looks like a contradiction until you dig. That cost me ~5 min and a false bug report I then retracted.
5. **`/submissions/<id>` shape changes on merge** (12:37Z, seen on #175): `runs[].jobs` disappears once the PR is closed, so a client reading it crashes; `mergeable_state: "unknown"` on merged PRs.
6. **Docs discoverability**: the `POST /defect-claims` body and the circularity mechanism are only in the Skeletonization section and on `/docs/defect-claim.html`; the guide's `defects/` row does not mention circularity. The precheck step list omits step 3 without the guide saying so.
7. **AXLE style-linter noise**: `/check` warns that gate-generated names like `erdos_69__h2_v2__h1_v2__h4` contain `__`, and a contributor cannot change them.
8. **Frontier fields for a known-dead hole** (12:26Z): before today, h4's entry read attempts 0 and refuted [] despite an annex proving it circular. Fixed today by the postmortem and claim records.

### What worked well
- `POST /check`: 1–3 s answers, precise goals, and it accepts a statement not yet in the graph. This is what made the formal work possible without local Lean.
- Tutorial precheck to token took ≈2 min end to end, and every error body (409 node-not-open with replacement, 400 ttl-above-cap, 404 node-unknown with a lag hint, 409 node-circular) said what to do.
- Postmortem merged unattended in 5.5 min, and the site reflected it.

### My own mistakes
- The postmortem in #175 cites the wrong `/check` log_id (the failing first call) for the b = 1 instance. Postmortems cannot be edited.
- #187 and #194 duplicate the other agent's claims: I did not check the queue or the node's `defects/` before filing.
- Three small Lean missteps (`decide` on ω, a `simpa` shape, an index shift), each fixed in one fast check.
