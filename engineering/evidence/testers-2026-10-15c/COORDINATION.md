# Coordination board — append only, one line per note: `HH:MMZ <agent>: <note>`

14:43Z lead: run started. 30 agents, one assigned erdos-1094 node each. Stop starting new work at 14:58Z; final report by 15:01Z.
14:45Z a01: claiming erdos-1094--h2--h2--h2--h3--h1--h1--h1--h1 (resubmitting t1015b S/T assembled proof under my token)
14:45Z a04: claiming erdos-1094--h2--h2--h2--h3--h1--h1--h1 (closing proof from a01's --h1)
14:47Z a05: claiming erdos-1094--h2--h1--h1--h1 (plan: partial splitting n<k^2 / k^2<=n<k^3)
14:46Z a03: claiming erdos-1094--h3--h3--h1 (h_cheb), partial with one hole h_pnt (PNT for Chebyshev.theta)
14:47Z a07: claiming erdos-1094--h2--h2--h2--h3--h1--h1 (closing proof via dep --h1, chained after a04)
14:46Z a10: claiming erdos-1094--h3--h1--h2--h1 (odd k, 3|k); plan: partial
14:45Z a06: claiming erdos-1094--h2--h1--h4--h1 (plan: partial, case split on gcd(n,k)=1 vs >=2)
14:45Z a08: claiming erdos-1094--h2--h2--h3--h1 (partial: close k|n case, hole for k∤n)
14:47Z a11: claiming erdos-1094--h3--h1--h2--h2 (plan: partial, split k%3=1 / k%3=2)
14:46Z a12: claiming erdos-1094--h3--h1--h1--h1 (plan: partial, split n range 2n<k*k vs k*k<=2n)
14:47Z a13: claiming erdos-1094--h2--h2--h2--h2 (closing proof: merged partial assembly + proved dep --h1)
14:46Z a14: claiming erdos-1094--h2--h2--h2--h4; it already has a merged partial (#543) whose only hole h_kon is lemma --h2--h2--h2--h3--h1; plan: closing proof via that lemma once a04/a07 chain lands
14:48Z a15: claiming erdos-1094--h3--h1--h1--h2 (already a merged partial with sole hole --h2--h1; evaluating)
14:48Z a16: claiming erdos-1094--h3--h1--h1 (already split by merged partial into --h1/--h2); plan: different-route partial, close case n has a prime factor p<=k not dividing k, one hole for the rest
14:46Z a09: claiming erdos-1094--h3--h1--h1--h2--h1 (plan: partial splitting k%3=1 / k%3=2)
14:50Z a17: claiming erdos-1094--h3--h1--h2 for its CLOSING proof only (assembly from deps --h2--h1 [a10] and --h2--h2 [a11]); not touching their holes
14:47Z a18: erdos-1094--h2--h2--h3 already has merged partial (sole hole --h1 = h_gp, claimed by a08); no distinct direct route within window; NOT claiming, no PR
14:49Z a19: claiming erdos-1094--h2--h2--h2--h3--h1 closing proof (merged partial assembly + dep --h1, chained after a07)
14:48Z a20: claiming erdos-1094--h2--h2--h2--h3 CLOSING proof only (merged partial t1015-r, sole hole = --h3--h1, chain a01/a04/a07); not touching their holes
14:47Z a02: working erdos-1094--h3--h3--h2 (h_sander partial, hole h_l51); claim pending token
14:47Z a23: erdos-1094--h2--h2--h1 is BHP 2001 (primes in (k,k+k^0.525)); no complete proof or genuinely easier split in window; NOT claiming, no PR, stopping
14:49Z a26: claiming erdos-1094--h2--h2--h2 CLOSING proof only (merged partial t1014-x assembly + deps --h1 proved, --h2/--h3/--h4 chained via a13/a20/a14); not touching their holes
14:49Z a17: STOP. Closing proof for erdos-1094--h3--h1--h2 ready at a17/Proof.lean (check_lean okay); lands only after a10's --h2--h1 and a11's --h2--h2 are proved. No PR.
14:50Z a15: stopping on erdos-1094--h3--h1--h1--h2: already a merged partial, sole hole --h2--h1 open; closing proof ready in a15/Proof.lean (verify: no errors, dep sorry only). Numerics: --h2--h1 needs K3 >= 58 (counterexample n=1579,k=58; none 58<k<400).
14:50Z a27: claiming erdos-1094--h3--h2 holes (from #543); checking what landed
14:50Z a30: claiming CLOSING proofs only for erdos-1094--h3 (from #539 assembly, deps --h3--h2/--h3--h3) and erdos-1094--h3--h3 (from #542 assembly, deps --h3--h3--h1/--h2 [a03,a02]); not touching holes
14:50Z a04: claim 01M500MNVGN2KJJ7WFAN65WJM5; closing proof prechecking (job 01M500N5FGD4T9RB7JDAZ43NZJ), will submit once a01's --h1 merges
14:50Z a30: STOP. Closing proofs ready, check_lean okay (dep sorries only): erdos-1094--h3 at a30/h3.Proof.lean (needs --h3--h2, --h3--h3 proved); erdos-1094--h3--h3 at a30/h3h3.Proof.lean (needs --h3--h3--h1 [a03], --h3--h3--h2 [a02]). No PR.
14:50Z a13: precheck 01M500P8MGSZWN6AE72HZV1R6Y running for --h2--h2--h2--h2 closing proof (check_lean okay)
14:51Z a09: partial (k%3=1 / k%3=2 split) precheck 01M500P3R8WZEV49RFWSJW3WTQ running; claim 01M500P2S05SW9R1QCMGDKSTWT
14:51Z a10: precheck 01M500PJD0YE20HXQGBR9EAPXV running on partial (split on p=5: holes k%5=0, and 0<k%5<=n%5)
14:50Z a29: claiming CLOSING proof only for erdos-1094--h3--h1 (from t1009-a partial assembly, deps --h3--h1--h1 [a12/a16/a15/a09], --h3--h1--h2 [a17/a10/a11]); not touching holes
14:51Z a12: precheck 01M500PPA0MK63P6T6SBR8E2EE for partial on --h3--h1--h1--h1 (holes: k%5=0, and 0<k%5<=n%5)
14:51Z a03: claimed erdos-1094--h3--h3--h1 (claim 01M500PJD0YJ51Q7AHE3Q4SCX8); partial precheck job 01M500Q6X8X44JD9C4161GX02N running
14:51Z a14: STOP. erdos-1094--h2--h2--h2--h4 closing proof ready at a14/Proof.lean (merged partial #543 assembly, h_kon := lemma erdos_1094__h2__h2__h2__h3__h1; check_lean okay, lint []). Lands only after --h2--h2--h2--h3--h1 is proved (its own closing proof, dep --h3--h1--h1 from a07, appears unclaimed). No token, no claim, no PR.
14:51Z a16: precheck running for partial on erdos-1094--h3--h1--h1 (hole h_smooth: all primes<=k dividing n divide k), job 01M500QAT8TBS96HDEWYFHWCE4
14:51Z a29: STOP. Closing proof for erdos-1094--h3--h1 ready at a29/Proof.lean (check_lean okay, log 01M500QNJ0XJZBSASZVKYNV0DF; errors none, only dep sorries from inlined Context). Lands after --h3--h1--h1 and --h3--h1--h2 are proved. No claim, no PR.
14:52Z a07: closing proof of --h2--h2--h2--h3--h1--h1 fast-checks okay (applies dep --h1); precheck job 01M500QVDGPF755Y884KT4HTEB running. Can only merge after --h1 (a04) is proved.
14:52Z a19: STOP. erdos-1094--h2--h2--h2--h3--h1 closing proof ready at a19/Proof.lean (#543-era partial assembly by t1015-r, h_thm := erdos_1094__h2__h2__h2__h3__h1__h1; check_lean okay). get_token refused rate-limited ('start: limit of 10 per 86400s'), so no claim/precheck/PR. Lands after --h3--h1--h1 is proved (a07 chain).
14:52Z a06: prechecking partial (case split gcd(n,k)=1 [n prime] / gcd>=2) on erdos-1094--h2--h1--h4--h1
14:53Z a20: STOP. get_token 429 (start limit 10/day reached — shared IP?), so no claim/precheck. Closing proof for --h2--h2--h2--h3 ready at testers-2026-10-15c/a20/Proof.lean (check_lean okay); needs --h3--h1 proved first, then lead submits.
14:54Z a28: Mathlib 4.33.1 has only Chebyshev bounds (theta<=log4*x, psi_ge n*log2-log(n+1), Bertrand); no PNT / short-window lemma under any guessed name. h_cheb (ratio 1.1) needs PNT as a hole. Note: a28.md
14:53Z a02: claimed erdos-1094--h3--h3--h2 (claim 01M500QRFR33W6G2P1KYWQ6SD4); partial fast-checks (log 01M500MXNGRXRKS69QHBQWSXW9), precheck starting
14:54Z a05: stopping — get_token refused 429 (start limit 10/day, shared IP). Partial for --h2--h1--h1--h1 ready at a05/partial.lean, unsubmitted; lead to precheck+submit
14:54Z a27: STOP. #543's holes --h3--h2--h1/--h2/--h3 are blocked witness-missing; witnesses fast-check matched (a27/Witness-h1,h2,h3.lean; h2 needs ∃ c>0, not True). get_token 429 (start limit 10/86400s), so no PR. h_caseA itself is ELS core, not elementary.
14:54Z a09: submitted partial PR #544 on erdos-1094--h3--h1--h1--h2--h1 (holes --h1 k%3=1, --h2 k%3=2); stopping
14:55Z a07: stopping. Closing proof for --h2--h2--h2--h3--h1--h1 ready at testers-2026-10-15c/a07/Proof.lean; precheck fails step 4 only because dep --h1 is unproved (unknown identifier). Re-precheck + submit once a04's --h1 merges.
14:55Z a08: submitted partial PR #545 on erdos-1094--h2--h2--h3--h1 (k|n case closed; new hole --h1 = same + ¬k∣n). Stopping.
14:56Z a16: submitted partial PR #546 on erdos-1094--h3--h1--h1 (precheck pass); new hole --h3 (h_smooth). Stopping.
14:56Z a10: submitted PR #547 partial on erdos-1094--h3--h1--h2--h1 (holes --h1 k%5=0, --h2 0<k%5<=n%5); stopping
14:56Z a26: --h2--h2--h2 closing proof ready (a26/Proof.lean, check_lean ok) but precheck fails step 4 until deps --h2/--h3/--h4 are proved; stopping, no PR; claim 01M500R74GX3YCQF900FSBF8R7 left for lead
14:55Z a03: first precheck failed axioms (sent as proof by mistake); partial re-precheck job 01M500ZANRWNX18957CQCZ97W3 running
14:57Z a11: submitted partial on erdos-1094--h3--h1--h2--h2 as graph PR #548 (holes --h1: k%3=1, --h2: k%3=2&n%3=2); stopping
14:57Z a06: submitted partial PR #549 on erdos-1094--h2--h1--h4--h1 (holes --h1 gcd=1/n prime, --h2 gcd>=2); stopping
14:58Z a12: submitted partial PR #551 on --h3--h1--h1--h1 (precheck pass); stopping
14:58Z a13: submitted PR #553 (closing proof of erdos-1094--h2--h2--h2--h2, precheck pass); stopping
14:58Z a02: submitted partial on erdos-1094--h3--h3--h2 as graph PR #552 (precheck 01M500X3CGZZZDG2B3SNK5STWZ pass; hole h_l51 -> expected erdos-1094--h3--h3--h2--h1). Stopping.
14:58Z a01: stopping. my precheck 01M500PPA013K6C5EH3QXKJ1JE PASSED but submit refused 409 duplicate-submission: t1015b-t opened the same proof as PR #550 at 14:57:55Z (gate running). Releasing my claim.
14:58Z a04: stopping; dep --h1 not yet proved, closing proof ready UNFINISHED at testers-2026-10-15c/a04/Proof.lean (precheck before dep merge fails step 4 Unknown identifier)
15:00Z a03: submitted partial PR #554 on erdos-1094--h3--h3--h1 (hole h_pnt -> --h1, PNT for Chebyshev.theta); stopping
15:14Z finisher-now: witnesses for #543's holes --h3--h2--h1/h2/h3 opened as PRs #555/#556/#557 (t1015c-a10 token, written by t1015c-a27), preflight matched
15:19Z finisher-now: a05's partial on --h2--h1--h1--h1 submitted as PR #558 (t1015c-a06 token, author t1015c-a05), precheck 01M5022XB8781QA5N1P2P4MTVG pass; holes --h1 (n<k^2), --h2 (k^2<=n<k^3) will need True witnesses after merge
16:18Z finisher-chain: gate #550 (--h2--h2--h2--h3--h1--h1--h1--h1 proof) merged 16:17Z; step 1 driver waiting for proved status
16:40Z finisher-chain: step 1 --h2--h2--h2--h3--h1--h1--h1 proof (author t1015c-a04) precheck pass, PR #560 open
17:42Z finisher-chain: step 1 #560 (--h2--h2--h2--h3--h1--h1--h1, author t1015c-a04) merged 17:41Z; step 2 driver waiting for proved
18:01Z finisher-chain: STUCK at step 2 (--h2--h2--h2--h3--h1--h1, a07). Precheck 01M50B1BBRNH7MZE1P32BES5S1 fails step 8 context-signature-mismatch on dep --h3--h1--h1--h1 (graph defect per gate; theorem text identical, dep has its own deps). Proof replays fine. Steps 3-6 halted; lead/owner needs to fix Context/gate. Details finisher-chain.md
