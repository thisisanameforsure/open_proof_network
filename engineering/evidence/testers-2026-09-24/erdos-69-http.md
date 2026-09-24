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
