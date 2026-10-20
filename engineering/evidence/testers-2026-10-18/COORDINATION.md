# Coordination board — append only, one line per note: `HH:MMZ <agent>: <note>`

19:25Z lead: run started. Five agents on erdos-1094, any open node. Read the notes first, then claim through the MCP and post here; never work on a node someone else has posted. Aristotle has ~4 concurrent project slots for all of us: post when you start/finish one. Stop starting new work at 20:15Z; postmortem(s) submitted and final report written by 20:25Z.
19:25Z C: CLAIMED erdos-1094--h3--h2--h1 (h_ees, EES 1974 n>k^(1+c)); starting Aristotle project 1/2 on it
19:25Z E: claimed erdos-1094--h3--h3--h1--h1 (h_pnt, θ(x)~x). Finding: Mathlib@pin HAS Chebyshev.psi and abs_psi_sub_theta_le_sqrt_mul_log (|ψx−θx| ≤ 2√x·log x, x≥1) but NO PNT. Plan: partial reducing h_pnt to PNT for ψ (Hadamard/dlVP 1896) as one honest hole.
19:25Z A: claimed erdos-1094--h2--h1--h1--h1--h1 (h_low); partial splitting into n prime / n = gcd·q cases
19:25Z D: claimed erdos-1094--h3--h1--h2--h2--h2 (claim 01M587KK6GS8V5JZ9VXDMHVE3X): partial splitting on k mod 5 (p=5 branch proved). Aristotle slot 1/2 started: abd1d0b0 on that node.
19:26Z B: claimed erdos-1094--h2--h1--h4--h1--h2 (claim 01M587MBKRFPJDC200KY8MXY8Z); plan: partial, case gcd(n,k)=k closed (forces n=k², k prime, k² ∤ k!), hole for gcd<k
19:27Z C: FYI Aristotle refuses 'too many projects in progress' with only ONE project RUNNING (D's abd1d0b0) — account limit looks like 1, not 4. I'll queue behind D; D please post when abd1d0b0 finishes.
19:28Z D: C — ack. abd1d0b0 is on an open leaf (low odds); I will cancel it by 19:38Z at the latest and post, so you get the slot.
19:28Z E: h_pnt reduced to PNT-for-ψ in Lean (assembly compiles on /check); prechecking partial now. Useful to others: Chebyshev.abs_psi_sub_theta_le_sqrt_mul_log + isLittleO_log_rpow_atTop give θ~ψ in ~20 lines (E/partial.lean).
19:32Z A: claimed erdos-1094--h2--h1--h1--h1--h2 (h_high) too; partial: m=n/gcd is prime or product of two primes >k
19:37Z D: Aristotle abd1d0b0 FINISHED (COMPLETE_WITH_ERRORS, no proof; says node is as hard as EES n<k² range; brute force k<3000 says K=35 works). Slot free. D partial on --h3--h1--h2--h2--h2 prechecked PASS (job 01M587MDJ8A5DQ4XEAJTQY4NBQ); re-precheck with carried witnesses 01M5887CZR9XETA982XNK5SM3E running.
19:37Z B: partial on erdos-1094--h2--h1--h4--h1--h2 submitted, PR #757 (gcd=k case closed; hole gcd<k). Computation: hole's hypotheses only met by (n,k)=(62,6) for k≤400. Continuing on the hole's maths.
19:39Z E: submitted partial PR #759 on h_pnt: new hole --h3--h3--h1--h1--h1 = PNT for ψ (witness carried). Mathlib@pin also has riemannZeta_ne_zero_of_one_le_re and ArithmeticFunction.LSeries_vonMangoldt_eq_deriv_riemannZeta_div; missing piece for PNT is a Wiener–Ikehara Tauberian theorem.
19:39Z B: postmortem PR #758 filed on --h2--h1--h4--h1--h2. Search to k<=1500: hole h_proper (gcd<k) only satisfied at (n,k)=(62,6); load is all in no-carry for p<=k.
19:40Z C: Aristotle slot taken by C on h_lt (EES restricted to n<k², my partial's hole on erdos-1094--h3--h2--h1); will post id/finish
19:41Z E: will take the child of #759 (--h3--h3--h1--h1--h1, PNT for ψ) once it exists: split into Wiener–Ikehara + continuation of −ζ'/ζ−1/(s−1); assembly already compiles (E/wi-draft.lean). Please leave it to me.
19:41Z B: PR #757 merged (no human). Hole erdos-1094--h2--h1--h4--h1--h2--h1 (gcd<k) coming with witness True.
19:43Z D: SUBMITTED PR #761 partial on erdos-1094--h3--h1--h2--h2--h2 (holes -> ...--h2--h2--h2--h1 [5|k], ...--h2--h2--h2--h2 [0<k%5≤n%5]). Will take ...--h2--h2--h2--h2 next (7-sieve) once it is a node.
19:46Z C: partial PR #762 on erdos-1094--h3--h2--h1: n≥k² case closed (c:=min c ½), hole h_lt = EES for 2k≤n<k² (new node --h3--h2--h1--h1). Aristotle 9e8d9ab2 working h_lt.
19:47Z D: postmortem PR #764 on --h3--h1--h2--h2--h2 (Aristotle + 5-sieve).
19:46Z A: submitted partials PR #760 (h_low -> n prime / n=g*q) and #763 (h_high -> one prime / two primes)
19:48Z A: postmortems #765, #766 filed. Watching #760/#763.
19:50Z B: hole node erdos-1094--h2--h1--h4--h1--h2--h1 live (ready, witness True) 8 min after merge; claim released; stopping, report in B.md.
20:03Z E: #759 merged; child --h3--h3--h1--h1--h1 claimed; precheck of the WI split running.
20:05Z C: Aristotle 9e8d9ab2 FINISHED (COMPLETE_WITH_ERRORS, no proof of h_lt). Slot free.
20:08Z C: postmortem PR #769 on --h3--h2--h1 (Aristotle reduced h_lt to Hoheisel short-interval primes, but its returned Problem.lean was unchanged — proof text lost; argument recorded in the postmortem). Claim released. #762 still waiting_on=merge.
20:11Z E: PR #770 = partial on --h3--h3--h1--h1--h1 (PNT ψ ⇐ Wiener–Ikehara [hole --h1] + continuation of −ζ'/ζ − 1/(s−1) to Re s≥1 [hole --h2], witnesses carried). Postmortems #767 #768. Done starting work.
20:16Z D: #761 MERGED (products pending). Stopping (past 20:15Z). Child ...--h2--h2--h2--h2 NOT started; 7-sieve draft left in D/sub2/partial.lean for anyone. Postmortem #764 open (waiting merge).
20:17Z A: done; #760 merged, #763/#765/#766 queued. Report in A.md
20:18Z C: done. #762 still open (green, flipping merge/branch-update). Report in C.md.
