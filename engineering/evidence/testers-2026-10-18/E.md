# E (t1018-e) log
- 19:20Z start; cloned graph into E/graph; read AGENTS.md, GR-OUTLINE.
- 19:22Z tutorial precheck job 01M587E9906631WNF5RY0RKN9C (receipt E/tut-pre.json)
- 19:25Z token minted (identity 01M587K4HR082P8NF0QA8Z4SHE, E/tok-res.json, token in E/token). Claim 01M587KCBRJEK9J6W46S6G8VZJ on erdos-1094--h3--h3--h1--h1 (h_pnt).
- 19:25Z /check probe: Mathlib has Chebyshev.psi, theta_le_psi, abs_psi_sub_theta_le_sqrt_mul_log; no PNT lemma. Plan: partial with hole = PNT for ψ.
- 19:28Z partial (h_pnt ⇐ PNT for ψ + Mathlib's |ψ−θ|≤2√x log x, √x log x=o(x) via isLittleO_log_rpow_atTop) passes /check verify (only sorry warning); E/partial.lean, E/chk-res.json. POST /precheck sent; >120 s without a response (bg).
- 19:34Z precheck 01M587W4MGJH2BDKSP91H38BM1 PASS (E/pre1-res.json); hole h_psi → erdos-1094--h3--h3--h1--h1--h1, expected_witness ∃ε>0. Re-prechecking with carried witness.
- 19:38Z precheck 01M58844G09SR2AW5HKJCZT0AR PASS with carried witness checked. 19:39Z submitted partial: submission 01M588CTT873MZK06G30P67VAN, graph PR #759 (E/sub.json). Child erdos-1094--h3--h3--h1--h1--h1 = PNT for ψ.
- 19:41Z drafted second-level partial for the coming child (PNT for ψ ⇐ Wiener–Ikehara + continuation of L(Λ,s)−1/(s−1)); assembly compiles on /check (E/wi-draft.lean). Waiting for #759 to merge so the child exists.
- 19:56Z child erdos-1094--h3--h3--h1--h1--h1 live (#759 merged 19:47Z, products ~9 min later). 20:02Z claim 01M589PQMGC43E4ZYH7JXW28AD. First precheck refused 400 partial-unlabelled: '· -- label:' on the bullet line not recognised (E/pre3 first response, in log); moved labels to own lines. Precheck 01M589R7FRZZTE4RPYQ7YT6N0F (E/partial2.lean).
- 20:06Z precheck 01M589R7FRZZTE4RPYQ7YT6N0F PASS (holes h_wi→…--h1--h1--h1--h1--h1--h1, h_ext→…--h2, witness True). Re-precheck with both witnesses carried: 01M589ZB1064N0D1FXAPCYA3R5. 20:07Z postmortems PR #767 (h_pnt), #768 (PNT for ψ).
- 20:11Z precheck 01M589ZB1064N0D1FXAPCYA3R5 PASS, both witnesses checked. Submitted partial 01M58A8490VAJ9Q7795JP3AHK5, graph PR #770. Released claim on h_pnt. Stopping new work.

## Final report (E, t1018-e), 20:13Z

**1. Outcome**
- Graph PR #759: partial on `erdos-1094--h3--h3--h1--h1` (h_pnt, θ(x) = x + o(x)). MERGED 19:47Z. Proves θ ~ x from ψ ~ x using Mathlib's `Chebyshev.abs_psi_sub_theta_le_sqrt_mul_log` and `isLittleO_log_rpow_atTop`. One hole: PNT for ψ, now node `erdos-1094--h3--h3--h1--h1--h1` (ready, witness carried).
- Graph PR #770: partial on `erdos-1094--h3--h3--h1--h1--h1` (PNT for ψ). OPEN, gate running at 20:12Z. The assembly proves ψ ~ x from two cited holes with carried witnesses: `h_wi`, the Wiener–Ikehara Tauberian theorem in Korevaar's continuous-boundary form, and `h_ext`, the continuous extension of L(Λ,s) − 1/(s−1) to Re s ≥ 1.
- Postmortems: #767 (h_pnt) and #768 (PNT for ψ), both open, waiting on `merge`.
- Board finding (19:25Z): the pinned Mathlib has ψ, θ, |ψ−θ| ≤ 2√x log x, ζ ≠ 0 on Re ≥ 1, the residue of ζ at 1, and L(Λ) = −ζ'/ζ. It has no PNT and no Wiener–Ikehara.

**2. Bugs**
- B1 (doc/rule mismatch): `POST /precheck` answered `400 partial-unlabelled` for holes inside the guide's own "give each hole its own scope" bullet pattern when the label was written on the bullet line: `    · -- label: Wiener–Ikehara Tauberian theorem` followed by `-- claim:` lines and then `have h_wi …`. Expected: the comment block above the `have` contains a `-- label:` line, so it is accepted. Actual: "no `-- label:` line in the comment block directly above its `have`", h_wi line 23 and h_ext line 33 (E/partial-unlabelled-response.json). It was accepted once the bullet line carried a different comment and the label moved to its own line. The guide never shows the two rules together. Cost: one round trip, no precheck spent.
- B2 (environment, already known): the first `POST /precheck` failed with `curl: (28) Failed to connect … after 150009 ms`, and a later connect took 15.2 s. This is the laptop-to-API-Gateway path, not the service.

**3. Feature requests**
- Show the bullet-scoped-holes example in the Skeletonization section with its `-- label:`/`-- claim:` lines in place. Both rules apply to every multi-hole partial, and the example as written fails the label rule if you copy it.
- Let a carried witness be prechecked in the same run that reports `expected_witness`, for example by accepting `-- hole: h, witness: auto` for the trivial `True` and `∃ε>0` cases. Each of my partials needed two prechecks (~4 min each) only to attach the witness the first one printed.
- Have `POST /submissions/<id>` say when a child becomes addressable. The wait from merge to the child existing was 9 min (19:47 → 19:56), and only polling `holes[].became` showed it.

**4. What cost the most time**
Waiting. Each precheck took ~3.5–4 min (four of them), and the gap from merge to the child node existing was ~9 min. The Lean took about 10 minutes in total, because `/check` returned answers in seconds and the Mathlib names were probed first.
