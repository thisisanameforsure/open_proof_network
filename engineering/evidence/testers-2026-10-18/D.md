# D (t1018-d) log
19:20Z cloned graph into D/graph, read AGENTS.md (opn-prove, tokens, submit, postmortem). MCP helper D/mcp.py.
19:21Z tutorial precheck job 01M587D45GAV3NTZS0YKH40QCJ (receipt D/tut-precheck.json) to mint token.
19:25Z token for t1018-d minted (identity 01M587KJ787XDNHKCJ2KF2K8RX). Claimed erdos-1094--h3--h1--h2--h2--h2 (claim 01M587KK6GS8V5JZ9VXDMHVE3X).
19:24Z Aristotle project abd1d0b0-d6dd-4427-874d-55d4b449e66d on that node (D/ar1/). Partial draft D/sub1/partial.lean: holes h_k5_zero (k≡0 mod 5), h_k5_le (0<k%5≤n%5); n%5<k%5 branch closed with p=5. Fast check: only sorry warnings (D/sub1/check1.json).
19:36Z precheck 01M587MDJ8A5DQ4XEAJTQY4NBQ PASS (D/sub1/pre1-result.json). Holes -> expected nodes ...--h2--h2--h2--h1 (h_k5_zero), ...--h2 (h_k5_le); expected_witness True. Note: first labels refused 400 partial-unlabelled (needs -- approach/licence/label/claim, claim wholly in $..$).
19:36Z re-precheck with carried witnesses: job 01M5887CZR9XETA982XNK5SM3E (D/sub1/bundle2.json).
19:37Z Aristotle abd1d0b0 COMPLETE_WITH_ERRORS, unchanged file; summary in D/ar1/show.txt (claims brute force: only k<=35 exceptions for k<3000 in this class).
19:40Z re-precheck 01M5887CZR9XETA982XNK5SM3E PASS, both carried witnesses checked:true (D/sub1/pre2-result.json).
19:40Z submit_proof first try: client TCP connect timeout (Errno 60) after ~2 min; get_my_submissions showed nothing opened; retry 19:43Z ok.
19:43Z SUBMITTED PR #761 (submission 01M588M65GZK29SD1VTPT3H3KG), receipt D/sub1/submitted.json.
19:47Z postmortem PR #764 (D/pm1.yaml, D/pm1-submitted.json). Draft 7-sieve partial for child --h2 in D/sub2/partial.lean (fast check: sorry-only warnings).
19:57Z #761 gate green since ~19:48Z, waiting_on=merge behind #760 (also green/merge); mergeable_state unknown. D/sub1/state-1956.json
20:16Z #761 MERGED (waiting_on products, holes became null so far; D/sub1/state-final.json). Postmortem #764 open, waiting_on merge. Stopped: past cutoff, the 7-sieve partial on the child (D/sub2/partial.lean, fast-checked) was not started because the child node did not exist yet.

## FINAL REPORT (D, t1018-d)
1. Outcome: PR #761, a partial on erdos-1094--h3--h1--h2--h2--h2, MERGED with no human. It sieves by 5: the n%5<k%5 case is closed with p=5, and two holes go to ...--h1 (5|k) and ...--h2 (0<k%5<=n%5) with carried witnesses True. Postmortem PR #764 is open. Aristotle project abd1d0b0 returned COMPLETE_WITH_ERRORS with the file unchanged; its outside-Lean brute force suggests K=35 for this class. Nothing was fully proved.
2. Bugs:
 a. Aristotle concurrency is 1 project, not 4 (C saw "too many projects in progress" while only abd1d0b0 ran, board 19:27Z). The brief and the guide both imply more.
 b. The partial-label rule fails one error at a time. First refused: no approach/licence/label/claim. Second refused: the claim is not wholly `$...$`, because prose outside the dollars is rejected. It cost one round trip each (D/sub1/pre1.json history). Expected: one message listing every rule, with an example claim line.
 c. Laptop-to-API path: a get_precheck TLS handshake timed out (19:3xZ, traceback in background output). submit_proof failed with TCP connect Errno 60 after about 2 min (19:40Z), and get_my_submissions confirmed nothing had opened. curl connect afterwards took 0.17 s. This looks like the known laptop path, not the service.
 d. While queued, get_submission showed waiting_on=merge with mergeable_state "unknown" on a green gate for about 17 min (19:48 to 20:05Z, position 1 to 2). Then the branch was updated and the gate re-ran. It merged around 20:10Z. Not a defect as such, but slow (D/sub1/state-1956.json).
3. Feature requests:
 - Allow preparing a precheck for a hole's child before the parent merges (precheck against expected_node_id). This would have let me chain the 7-sieve inside the hour.
 - Have /check validate the partial-label comments too, so the format is caught in seconds and not by a precheck submission.
 - Expose Aristotle's concurrency limit, or a status call, through opn-prove.
4. Biggest time cost: waiting on the merge queue (about 25 min from submit to merge), then products. That left no room for a second level.
