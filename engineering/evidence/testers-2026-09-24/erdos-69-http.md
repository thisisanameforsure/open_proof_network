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
