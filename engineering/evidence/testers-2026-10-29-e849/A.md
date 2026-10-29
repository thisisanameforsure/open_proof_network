# A — near-diagonal shapes and the open core (pseudonym t1029e-a)

## Log

- 13:09Z read brief, prior README, BBdW 2017 (arXiv 1707.06893). BBdW Thm 2.2: shapes (n−1,k+2), (n−2,k+1) "settled in [17]" = Stroeker–de Weger, Solving elliptic Diophantine equations: the general cubic case, Acta Arith. 87 (1999) 339–365.
- 13:09Z tutorial precheck for token: job 01M63WFCNG8N891HA47PTV2DK4 (nonce kept in scratch only).
- 13:10Z math: C(n,k)=C(n−1,k+2) ⇔ (with y=n−k−2) y(y+1)(y+2) = (y+k+2)(k+1)(k+2); C(n,k)=C(n−2,k+1) ⇔ y(y+1)(y+2) = (y+k+2)(y+k+1)(k+1). Each a plane cubic (genus 1) — the "general cubic" case of Stroeker–de Weger. Plan: partial per shape reducing to that cubic's integral-point statement, elementary binomial algebra proved.

- 14:50Z (2,5): literature drafts extended to Yamada and BMSST nodes (4 records in A/literature-drafts.json). Prime-interval partial for --h2--h1--h4--h2--h3--h2 mocked against #1172's precheck closed_type: compiles (A/gap-mock.lean in scratch; final file written when the node lands).

## Findings
- 13:11Z token minted (one, kept in scratch). Claims 01M63WN768EP4251V8GPR4C90X (--h2--h1--h4--h2--h1), 01M63WN85G45MNM8WJSWECQXC1 (--h2--h1--h4--h2--h2), ttl 4h.
- 13:11Z read Stroeker–de Weger 1999 (https://matwbn.icm.edu.pl/ksiazki/aa/aa87/aa8743.pdf) §7.1: Theorem 3 (eq. (39), C(n,k)=C(n−1,k+2), u=k, v=n; 8 integral points, rank 1, trivial torsion) and Theorem 4 (eq. (40), C(n,k)=C(n−2,k+1); 9 points incl. (1,6), rank 1, torsion order 2). Checked by hand: (39) = n(k+1)(k+2) − (n−k)(n−k−1)(n−k−2), (40) = n(n−1)(k+1) − (n−k)(n−k−1)(n−k−2).
- 13:13Z wrote A/shape12-partial.lean (hole h_sdw3 = SdW Thm 3 over ℤ) and A/shape21-partial.lean (hole h_sdw4 = SdW Thm 4); fast check (mode check, node_id): both compile, only sorry-present. Witness type probed with check_lean witness mode + statement: `∃ u v : ℤ, (39)` matches; witness ⟨0,0, by norm_num⟩ (files A/s12-partial.1.witness, A/s21-partial.1.witness).
- 13:14Z prechecks: s12 job 01M63WRASRAG3G2HW7JT1RS4DK, s21 job 01M63WRFP0G9S2Y27W80GYDFC8 (ts 20261029T131800Z in paths).
- 13:17Z s12 precheck PASS (all steps, witness checked). SUBMITTED #1166 (submission 01M63WYYQ0P9K8TQQMBW5RS82P), partial on --h2--h1--h4--h2--h1, hole h_sdw3 → expected --h2--h1--h4--h2--h1--h1 (SdW 1999 Thm 3, witness carried).
- 13:19Z s21 precheck PASS. SUBMITTED #1167 (submission 01M63X1MN0T7C1XR6R3YGZW9S3), partial on --h2--h1--h4--h2--h2, hole h_sdw4 → expected --h2--h1--h4--h2--h2--h1 (SdW 1999 Thm 4), witness carried.
- 13:19Z open core angle: Yamada, Necessary conditions for binomial collisions, arXiv:2002.07043 (2020), Thm 1.1: C(2N+δ,N−M)=C(2N+L,N−K), 0≤M<K<N/2, M≤0.735K ⇒ L > N(1.3132 log²(2N) − 2.00271); proof uses N ≥ 500000 (from BBdW). Plan: partial on the core with two holes: h_yamada (corollary L ≤ N impossible, in ℕ, N ≥ 500000) and h_rest (core ∨ Yamada region). Witness of a collision-hypothesis hole is impossible, so the Yamada hole is stated with ≠ in the conclusion.
- 13:21Z wrote A/core-yamada-partial.lean (+ A/core-partial.1.witness, .2.witness): partial on the core --h2--h1--h4--h2--h3 with holes h_yamada (Yamada Thm 1.1 corollary, L ≤ N case, ℕ) and h_rest (core conclusion ∨ Yamada window: N=⌊m/2⌋ ≥ 500000, N < 2k, 1000(N−l) ≤ 735(N−k), m < n ≤ 3N). Assembly fast-checks first try. Precheck job 01M63X5QGGFJTVYCSJ8WNTMD8R. Caveat for the record: Yamada is an arXiv preprint (2020), no journal version found.
- 13:23Z–14:40Z LOST: the laptop lost network (urlopen Errno 51 "Network is unreachable", then Errno 8 DNS failures) and the session resumed at 14:40Z; ~75 min gone. Not the service.
- 14:40Z core precheck 01M63X5QGGFJTVYCSJ8WNTMD8R PASS (both carried witnesses checked). #1166 and #1167 MERGED.
- 14:42Z SUBMITTED #1172 (submission 01M641RJQG3KX16NVJ2GZH9R6G), partial on the core: h_yamada → --h2--h1--h4--h2--h3--h1, h_rest → --h2--h1--h4--h2--h3--h2.
- 14:46Z #1166/#1167 holes audited by me on main: both Statement.lean say exactly the have (ready). Taking (2,5) for B: claim on --h2--h1--h1--h3; source BMSST 2008 Thm 2.
- 14:45Z (2,5) partial A/pair25-partial.lean fast-checks (only hole sorry); precheck 01M641WNK0WSH2RB3GHP8HJJQF. Literature drafts for my two SdW holes in A/literature-drafts.json, to file in a quiet window.
- 14:48Z (2,5) precheck PASS; SUBMITTED #1174 (submission 01M64259YR0JKTGDT7V5YHT2KR), hole h_bmsst2 → --h2--h1--h1--h3--h1 (BMSST 2008 Thm 2), witness carried.
- 14:48Z next angle on the core (on #1172's h_rest once rendered): elementary prime-interval lemma, fast-checked fully proved (okay true, no lint): 2k ≤ n, 2l ≤ m, p prime, m < p, n−k < p ≤ n ⇒ C(n,k) ≠ C(m,l) (p | C(n,k) by Nat.Prime.dvd_choose_add; p ∤ C(m,l) | m!). Remaining core then: collisions where (max(m, n−k), n] holds no prime — the prime-gap regime that Yamada and others work in.

### F-A1 (feature request) Level n+1 waits for level n's render — still present, prior #3
- 14:42Z #1172 submitted; its hole --h2--h1--h4--h2--h3--h2 is the parent of my next partial (prime-interval split, already fast-checked against the precheck's `closed_type` at 14:50Z). I cannot precheck it until #1172 merges, renders and the bot commit lands. Expected: let a precheck target a hole named by a passing partial precheck (`expected_node_id`), as prior #3 asked. Cost: the next level idles ≥ 15 min.

### F-A2 (docs/feature) A hole's `-- claim:` cannot carry a long parent conclusion
- 14:20Z writing h_rest (core ∨ Yamada window) and the prime-interval hole: the hole's conclusion is the parent's 15-way disjunction plus one case. The claim must be one `$…$` (prior #8), so I wrote "(the parent's cases) ∨ …" in TeX. The gloss filed from it is therefore not the full statement. Expected: a way for a claim to say "parent ∨ X" by reference, or the guide to say how to gloss a hole that weakens its parent by one disjunct. Cost: small; a steward reading the gloss alone sees an abbreviation.

### F-A3 (environment, not the service) 75-minute outage
- 13:23Z–14:40Z `urlopen error [Errno 51] Network is unreachable`, then `[Errno 8] nodename nor servname provided`. B and C report the same window. The service kept merging (#1166 merged 13:22Z, #1167 13:27Z). Recorded so nobody reads the gap as service latency.
- 14:55Z (3,6) partial A/pair36-partial.lean (hole h_sdw36, SdW Acta Arith 87 §7.1 / Math Comp 68 Thm B36) fast-checks after one sign fix in the linear_combination; precheck submitted.
- 14:56Z next partial for --h2--h1--h4--h2--h3--h2 rebuilt: proved separation lemma + hole h_nagura (Nagura 1952: prime in (x, 6x/5) for x ≥ 25) + hole h_rest2 (parent ∨ (n > 10^6 ∧ 6m ≤ 5n ∧ n ≤ 6k)); mock against #1172's closed_type compiles. Postmortem drafts in A/postmortem-drafts.json.
- 15:01Z (3,6) precheck accepted after products-pending retries: job 01M642WH40ZVHAFQR67GXEDQF2.
- 15:01Z audited #1172's holes on main (gate: #1172 pass 15:00:27Z): --h3--h1 (h_yamada) and --h3--h2 (h_rest) say exactly the haves; both ready.
- 15:02Z A/rest-nagura-partial.lean (+ .1/.2 witness) on --h2--h1--h4--h2--h3--h2: proved separation lemma, holes h_nagura, h_rest2; fast check clean except holes; precheck 01M642XEDGTP6VRKPQ304GPMR7.
- 15:05Z (3,6) precheck PASS; SUBMITTED #1178 (submission 01M643495GPVE4MC4G2SF6CSF5), hole h_sdw36 → --h2--h1--h1--h7--h1.
- 15:07Z rest/Nagura precheck PASS; SUBMITTED #1180 (submission 01M6437218QW0655DE940P5F77): h_nagura → --h3--h2--h1, h_rest2 → --h3--h2--h2 (both witnesses carried).
- 15:08Z next level ready for --h3--h2--h2 (after #1180 renders): same separation lemma with Schoenfeld 1976 (prime in (x, x + x/16597) for x ≥ 2010759.9, quoted in Dusart arXiv:1002.0442 §6.1.3); remaining: n > 4021520 ⇒ m > 16597n/16598 or k < n/16598. Mock against #1180's closed_type compiles.

### F-A4 (bug, still present, prior #2) A precheck on an untouched node is refused while any node of the target awaits render
- 14:55Z precheck of a partial on --h2--h1--h1--h7 (nothing open on it) answered `409 products-pending`: "graph commit 187981e1b884… changed erdos-849's nodes after 4f771bb8ade8…, the commit that wrote its products". Accepted only at 15:01Z after six 60 s retries. Cost ~6 min. Repro: precheck any partial on a target within minutes of another partial's merge.

### F-A5 (observation) A single lane serialises every partial on a target
- 15:09Z #1180 sits 4th of 4 in the erdos-849 lane (#1175, #1178, #1179 ahead), so a next level on its hole cannot start before ~15:45Z. Three agents' independent partials on disjoint subtrees wait on one another. Feature request: lanes per subtree, or let a partial whose holes are disjoint from others' merge without the strict up-to-date round.
- 15:16Z filed literature records (known): #1181 (--h2--h1--h4--h2--h1--h1, SdW Thm 3), #1182 (--h2--h1--h4--h2--h2--h1, SdW Thm 4), #1183 (--h2--h1--h4--h2--h3--h1, Yamada), #1185 (--h2--h1--h1--h3--h1, BMSST Thm 2). Still to file: (3,6) hole and Nagura hole once they exist.
- 15:16Z postmortems filed: #1187 (--h2--h1--h4--h2--h1, blocked/missing-library), #1191 (--h2--h1--h4--h2--h2). Core postmortem waits for the last split.
- 15:21Z #1180 is 4th in lane (would render ~15:55Z, too late for a next level). Built A/rest-nagura-schoenfeld-partial.lean (+ .1–.3 witnesses): same node, Nagura AND Schoenfeld holes in one partial. Plan: once its precheck passes, withdraw #1180 (my own, unmerged) and submit this in its place. Precheck refused 409 products-pending at 15:20Z; retrying.
- 15:33Z superset precheck 01M644CW00Q775VGS1S49APTSP PASS (h_nagura, h_schoenfeld, h_rest2 → --h3--h2--h1/--h2/--h3), but #1180 has meanwhile reached position 1 and is in its gate. Withdrawing it now would waste its round, so I do NOT withdraw; the superset is NOT submitted (it would be a second route on the same node). Instead: Schoenfeld split on #1180's --h3--h2--h2 once rendered (A/rest-schoenfeld build via mkschoen.py), if it renders before 16:00Z.

### F-A6 (bug) Appends overtake a partial that is first in the lane and keep sending it back to "behind"
- #1180 (partial, --h2--h1--h4--h2--h3--h2) was position 1, `waiting_on: gate`, from 15:33Z. While it gated, 18 appends on erdos-849 merged past it in two batches (#1181–#1188 at 15:36:12–42Z, #1189–#1198 at 15:41:05–30Z). At 15:43:53Z it reads `mergeable_state: behind`, `waiting_on: gate`, a new gate in progress, still position 1. The guide says: "While a pull request's updated gate runs, it holds the queue on its target: nothing there is merged past it, so it cannot be overtaken." Cost: #1180 not merged by 15:45Z, so its child cannot render before 16:00Z and my last planned partial (Schoenfeld split) is left for the lead. Repro: put a partial first in a target's lane, then file a batch of appends on that target.

### F-A7 (protocol gap) An append filed in a quiet window merges whenever the actor reaches it
- I filed four literature records and two postmortems at 15:16Z when every merged partial had its bot commit. They merged at 15:36Z and 15:41Z, i.e. after #1178 (merged 15:25Z, bot 15:40Z) and #1179 (merged 15:30Z, no bot commit by 15:43Z). So the brief's quiet-window rule cannot be kept by the filer: timing of the filing does not control timing of the merge. Feature request: let an append carry "merge only while no partial/proof on this target awaits its bot commit", or have the actor hold appends itself (prior #1).
- 15:47Z #1180 MERGED (15:47:20Z). Its child --h3--h2--h2 cannot render and precheck before 16:00Z; the Schoenfeld split is left for the lead (files below). Audited #1178's hole --h2--h1--h1--h7--h1: exact, ready.

## Final report (A, t1029e-a)

### 1. Landed (all through the MCP)
| PR | kind | node | what | state |
|---|---|---|---|---|
| #1166 | partial | --h2--h1--h4--h2--h1 (shape (n−1,k+2)) | assembly proved; hole --h1 = Stroeker–de Weger 1999 Thm 3 (integral points of cubic (39)) | merged, bot 13:31Z |
| #1167 | partial | --h2--h1--h4--h2--h2 (shape (n−2,k+1)) | assembly proved; hole --h1 = SdW 1999 Thm 4 (cubic (40)) | merged, bot 13:36Z |
| #1172 | partial | --h2--h1--h4--h2--h3 (open core) | holes --h1 = Yamada 2020 Thm 1.1 (L ≤ N case), --h2 = core minus Yamada's window | merged, bot 15:00Z |
| #1174 | partial | --h2--h1--h1--h3 (pair 2,5) | hole --h1 = BMSST 2008 Thm 2 (C(Y,2)=C(X,5) over ℤ) | merged, bot 15:14Z |
| #1178 | partial | --h2--h1--h1--h7 (pair 3,6) | hole --h1 = 15u³−15u = v³−4v²+3v integral points (SdW Acta Arith 87 §7.1 / Math Comp Thm B36) | merged, bot 15:40Z |
| #1180 | partial | --h2--h1--h4--h2--h3--h2 | separation lemma proved in Lean (prime in (max(m,n−k), n] ⇒ no collision); holes --h1 = Nagura 1952, --h2 = core with 6m ≤ 5n ∧ n ≤ 6k (n > 10^6) set aside | merged 15:47Z, bot 15:59Z |
| #1181, #1182, #1183, #1185 | literature (known) | SdW Thm 3, SdW Thm 4, Yamada, BMSST nodes | | merged 15:36Z |
| #1187, #1191 | postmortem | the two shape nodes (blocked, missing-library) | | merged 15:36Z/15:41Z |
| #1215, #1216, #1217 | literature ×2, postmortem | --h2--h1--h1--h7--h1, Nagura node, the core | | filed 16:02Z |
Every carried witness checked at precheck; all gate-written holes audited (by me and by C): exact.

### 2. Unfinished business for the lead
- **Schoenfeld split of --h2--h1--h4--h2--h3--h2--h2** (the newest core): `A/rest-schoenfeld-partial.lean` + `A/rest-schoenfeld-partial.1.witness`, `.2.witness`, built against the node as on main, fast check clean but for its two holes; precheck 01M646757G66B16VGQ1NK4321K (my token, started 15:59Z) — not submitted because it is past 16:00Z. Holes: h_schoenfeld (∀ x ≥ 2010760, ∃ prime p, x < p ∧ 16597p < 16598x) and h_rest3 = parent ∨ (4021520 < n ∧ 16598m ≤ 16597n ∧ n ≤ 16598k). Needs a submitter with a passing precheck of their own. Verify the Schoenfeld 1976 theorem number before citing one (I cite it via Dusart arXiv:1002.0442 §6.1.3).
- **Superset precheck 01M644CW00Q775VGS1S49APTSP** passed but was deliberately NOT submitted (would be a second route on --h3--h2). Ignore.
- Last appends filed 16:02Z after gate: #1179 pass: literature #1215, #1216, core postmortem #1217 — check they merged.
- All five of my claims released at 16:03Z.

### 3. Findings, most important first
F-A6 (appends overtake a gating partial at lane position 1), F-A7 (quiet-window rule cannot be kept by the filer), F-A4 (prior #2 products-pending on untouched nodes), F-A1 (prior #3 next level waits for render), F-A5 (one lane serialises disjoint subtrees), F-A2 (claim line cannot carry a long parent conclusion), F-A3 (laptop network outage 13:23–14:40Z, not the service).

### 4. Twice as productive
Being able to precheck against a hole that a passing precheck named (prior #3), and a lane that does not let appends push a gating partial back to "behind": together these cost me the last level of the core (Schoenfeld) and ~40 minutes of idle waiting across four levels. The 75-minute laptop outage cost more than either, and nothing in the network could have helped that.
- 15:59Z gate: #1180 pass; audited #1180's holes --h3--h2--h1 (Nagura) and --h3--h2--h2 (rest): exact, ready. Schoenfeld partial built (A/rest-schoenfeld-partial.lean + 2 witnesses), fast check clean but for its holes, precheck 01M646757G66B16VGQ1NK4321K accepted 15:59Z. NOT submitted: past 16:00Z.
- 16:02Z after gate: #1179 pass (replayed, 16:01:33Z): filed literature #1215 (--h2--h1--h1--h7--h1), #1216 (Nagura node), postmortem #1217 (core --h2--h1--h4--h2--h3). Done.
