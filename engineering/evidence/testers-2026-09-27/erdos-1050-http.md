# erdos-1050 HTTP tester log
19:49:08Z start
19:49 GET / (0.48s) route index ok. GET problem page, docs (0.2-0.6s). submissions.json: open=[] (0.36s). claims.json: no active claims on erdos-1050 nodes. frontier: erdos-1050, h1-v2 ready; h2,h3,h4 needs-witness; spec-f2b55478 speculative/open; h1-v2--h1 circular.
19:49:43 POST /precheck tutorial-and-swap anon -> 202 in 4.0s, job 01M3J6N2YRH88VBYMEXWE3EZD6
19:50 POST /check mode=witness (no content) for h2,h3,h4: 200 in 6.6s/1.8s/1.5s. expected: h2=True; h3=exists Qc Qx Aq n, defs (rfl-able); h4 = h3's defs AND h3's conclusion (i.e. witnessing h4 = proving h3).
19:50 numeric check (python Fractions+mpmath, my own): h3 (d^2<=2^{3n^2}, d=lcm of denominators of Qx n, Aq n) and h4 (0<r, r^2 2^{4n^2}<=2^{2n+4}) both hold n=0..8 and odd n 9..21; log2 d / n^2 ~ 1.24 < 1.5. Decomposition looks sound numerically (not a proof).
19:51 POST /check mode=witness with content: h2 witness `True := trivial` -> okay, matches (1.5s). h3 witness `⟨_,_,_,0,rfl,rfl,rfl⟩` -> okay, matches (1.1s).
19:51:44 tutorial precheck done: pass (~2 min). (earlier log times approximate)
19:52:39 POST /claims h2,h3 -> 201 (0.25s each). POST /proposals/witness h2 -> 201 PR #205 preflight matched (5.0s); h3 -> 201 PR #206 matched (3.4s).
19:54:09 POST /annexes spec-f2b55478 (partial-fraction proof sketch, CC-BY-4.0) -> 201 PR #207 in 2.6s, hash fcdb7a3a0b0e...
19:54:56 numeric (mpmath pslq, mine): h2's RHS(n) is an integer combination b*S'-a for n=1..7 (relations found, coefficients growing ~1e48 at n=7) -> h2 numerically consistent, no defect.
19:56:02 POST /check verify skeleton on spec-f2b55478 (4 sorry haves: hres, hpf, hl, hr) -> elaborates, only sorry (6.3s)
19:56:57 /check verify skeleton v3: hl (step1) and hr (step2, incl. truncation case) PROVED by AXLE, no errors; remaining sorry: hres (residue identity), hpf (partial fractions).
19:58:07 /check verify v6: hpf (Lagrange partial fractions via Lagrange.eq_interpolate_of_eval_eq) PROVED; only hres (q-product residue identity) remains sorry.
19:59:07 POST /precheck partial on spec-f2b55478 -> 409 annex-pending (annex #207 not merged yet) 0.45s — clear message. Working on hres meanwhile.
20:00:30 /check (mode check, standalone lemmas) E1-E4 product-splitting lemmas for hres all elaborate.
20:00:56 /check verify FULL proof of spec-f2b55478 (hres proved via product splitting/reflection; hpf via Lagrange) -> okay:true, no errors, 1 deprecation warning (4.4s).
20:01:24 POST /claims spec-f2b55478 -> 201. POST /precheck proof spec-f2b55478 (token) -> 202 in 3.5s, job 01M3J7A3T08FR3H0W7BSJGMWE2, graph_commit 27f30428
20:03:50 #205 (h2 witness) merged; h2 ready_since 19:55:10Z. #206 (h3 witness) merged, waiting on products. #207 annex waiting branch-update. Released claims on h2,h3 (not proving them).
20:04:32 precheck spec-f2b55478 proof: done/pass (steps 1,2,4-8 pass), ~3.2 min.
20:04:50 POST /submissions proof spec-f2b55478 -> 201 PR #222 (3.0s)
20:05:26 POST /annexes on h3 (numerical evidence; naive lcm bound insufficient) -> 201 PR #223 (5.9s)
20:07:54 #222 gate green (~2.5 min), waiting_on branch-update (mergeable_state behind)
20:18 #207 (annex spec) merged. #222 gate green 20:07, waiting_on=merge, mergeable_state=unknown for 10+ min (queue of 15 open PRs). #223 waiting merge.
20:18 Other agent t0927-1050-mcp: #214 annex on h3, #215 speculative spec-440db0f9 (Gaussian 2-binomial integrality, ingredient for h3). Not racing: I leave h3/h4 alone.

## BUGS (running)
- 19:52 POST /tokens body: docs say "a pseudonym and the current dco version"; field names not shown in the section. `dco_version` -> 400 unknown-field (accepted: dco, proof, pseudonym); `dco: "<ver>"` -> 400 dco-not-accepted "(dco.accepted: true)". Works with dco:{accepted:true,version}. Minor doc gap; errors were clear.
- merge queue: #222 green at 20:07, still not merged at 20:18+ (waiting_on merge, mergeable_state unknown). Throughput issue (known).
- env: api.github.com tree listing 403 from my sandbox (session GitHub access) — my environment, not the network.
## FEATURES (running)
- h2's witness was `True := trivial` but h2 sat "needs a witness" for 3 days; gate could auto-fill a True witness slot.
- h4 shows "needs a witness ... anyone may do it" though its witness must prove h3's whole conclusion; the frontier/page should say "witness requires sibling hole h3's content".
- A way to list a node's annex/attempt files via the service (GitHub API is not reachable for everyone).
20:28 #222 and #223 still green-waiting (waiting_on=merge, mergeable_state=unknown); open queue = 13 PRs (211..223), ~2 merges per 10 min, so #222 likely merges ~21:00+. Stopping new work.
## Final state (as I leave, 20:29Z)
- #205 witness h2: MERGED (h2 ready since 19:55:10Z)
- #206 witness h3: MERGED
- #207 annex spec-f2b55478 (partial-fraction proof sketch): MERGED
- #222 PROOF spec-f2b55478 (precheck pass, gate green): waiting on merge queue
- #223 annex h3 (numerical evidence, naive bound insufficient): gate green, waiting on merge queue
Lean artifacts kept here: proof_full.lean (the submitted proof), t1.lean/t2.lean (lemma development).
22:01:21 (late) poll: see below
22:01 (late background poll) #222 proof of spec-f2b55478 MERGED (between 20:31 and 22:01). #223 still open (branch-update).
