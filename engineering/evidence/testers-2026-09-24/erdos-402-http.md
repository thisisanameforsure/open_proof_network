# Tester log — erdos-402 via plain HTTP (2026-09-24)

Start: 2026-09-24T12:25:25Z. Stop new work at 13:20Z; log final by 13:25Z.
Entry point: https://openproofnetwork.org/problems/erdos-402/ (HTTP API only, no MCP).

## Timeline

- 12:25:25Z — reachability: problem page 200, `https://api.openproofnetwork.org/health` 200.
- 12:26Z — read problem page. 13 statements: root `erdos-402` open (needs the full Graham/Balasubramanian–Soundararajan theorem), holes h1, h2-v2 proved, h3-v2 open (essentially the whole difficulty), variants card_two & max_coprime proved; open variants card_three/four/five, large_prime (`variant-a874fe93`), minFac (`variant-3377fd96`).
  Plan: the large_prime and minFac variants have elementary proofs (a = max / the prime; a/gcd(a,b) is a nontrivial divisor). Check claims first.
- 12:26Z — `GET /frontier.json`: no active claims on any erdos-402 node (h3-v2 has history_count 1). Tutorial node is not on the frontier (proved), so I found it via raw `targets/index.json` → `targets/tutorial/nodes/tutorial-and-swap/Statement.lean` (the guide only shows a `grep` over a clone; for an HTTP-only agent, the tutorial node's id/path is not stated on the HTTP path — minor friction, **network/guide**).
- 12:26:20Z — `POST /precheck` tutorial proof (no token) → 202 queued, job 01M39P32F0R8BNKEQHNWTMXR5B.
- 12:27:09Z — `POST /check` mode verify on `variant-3377fd96` (minFac variant) with my proof → `okay: true`, lint [], 262 ms total at AXLE. Only warnings: `push_neg` deprecated (AXLE's Lean 4.33.1 Mathlib).
- 12:27:20Z — `POST /check` verify on `variant-a874fe93` (large_prime) → `okay: true`, lint [] (same argument, specialised via `Nat.Prime.minFac_eq`).
  Math: pick x with minFac x ≥ n. If some b has gcd(x,b) < x then x/gcd(x,b) is a divisor of x above 1, so ≥ minFac x ≥ n. Else x divides every element, A ⊆ x·[1, max/x], so n ≤ max/x and (max, x) works.
- 12:28Z — `POST /check` verify on `variant-6bd06d63` (card_three) → okay true, lint [] on first attempt.
- 12:29:11Z — tutorial precheck `done pass` (~2m50s after submission).
- 12:29:23Z — `POST /tokens` (tutorial proof, pseudonym `t0924-402-http`) → 201.
- 12:29:24Z — `POST /claims` ttl 2h on variant-3377fd96, variant-a874fe93, variant-6bd06d63, variant-780e7ade → 201 each.
- 12:29:3xZ — authenticated `POST /precheck` for minFac (job 01M39P8YY8NM…) and large_prime (01M39P99P0R3…) → 202; each request took several seconds.
- 12:30:00Z — **third `POST /precheck` (card_three) failed at the transport: `curl: (35) Recv failure: Connection reset by peer`**. Retried at 12:30:06Z → 202 (job 01M39P9Z5G5T…). Not reproduced; could be the proxy in this container rather than the service.
- 12:30:30Z — card_four (`variant-780e7ade`): first `/check` failed only on `Unknown constant Nat.dvd_sub'` (my mistake: lemma renamed in current Mathlib); with `Nat.dvd_sub` → okay true. The `/check` answer was clear and fast (1.7 s); the `tool_messages.infos` goal dump at the error was useful.
- 12:31:36Z — claimed `variant-bc28297c` (card_five) → 201.
- 12:31:40Z — card_five proof → `/check` okay true on first attempt. Argument: with M = max A, any b with M/gcd(M,b) ≤ 4 is one of M/2, M/3, 2M/3, M/4, 3M/4; four distinct such values always contain (3M/4, M/3), (3M/4, 2M/3) or (2M/3, M/4), whose gcd is M/12 (gcd divides u−2v, u−v, 3v−u resp.); otherwise A∖{M} fits in a 3-element set (pigeonhole via `Finset.card_le_three`).
- 12:31:5xZ — authenticated prechecks queued for card_four (01M39PD1SRFD…, 3.3 s to answer) and card_five (01M39PD6P01Z…, 5.8 s to answer). The three from 12:29–12:30 still `running` at 12:31:57Z.
- 12:33:06Z — `POST /submissions` minFac (precheck pass) → 201, **graph PR #177**; 12:33:10Z card_three → 201, **graph PR #178** (3.7–3.9 s each).
- 12:33:30Z — `GET /frontier.json`: another tester, `tester-402-mcp`, holds claims on *exactly* the same five variants I claimed at the same minute. Claims are advisory and racing is allowed, so nothing went wrong, but: the frontier shows no claim creation time, so neither of us could tell who came first. **Wish:** `claims.active[].created` on the frontier, and the claim response could warn "N other active claims on this node".
- 12:34Z — the three prechecks queued at 12:29–12:31 were still running at 12:33 (≈3–4 min each, consistent with the guide).
- 12:36Z — next: a card_six variant (proposal + proof). Checked by brute force in Python that for n = 6 (and 7) every (n−1)-subset of {jM/k : k < n} has a pair with a/gcd ≥ n, so the same method works; generating the Lean case tree with a script.
- 12:34:41Z — large_prime precheck pass → `POST /submissions` → **graph PR #183** (PR numbers 179–182 went to others in the meantime).
- 12:35–12:37Z — card_six via a generated case tree (by_cases on which of the values jM/k are present). First version: `/check` answered `okay: false` with **`(deterministic) timeout ... maximum number of heartbeats (200000)`** — the whole proof is one declaration, so the budget is cumulative. My attempts to raise it with a tactic-level `set_option maxHeartbeats N in` had **no effect** (limit stayed 200000, even with the tactic block properly nested) — so a long case-bash proof has no escape hatch inside Proof.lean. Not sure whether this is AXLE's or Lean's behaviour; the gate may differ. Restructured (one `have` per winning pair and per value, leaves only `exact`): card_five 3.8 s → 1.3 s, card_six **okay true in 5.6 s**.
- 12:37:40Z — card_seven with the same generator (282 leaves, 2663 lines): `/check` okay true, 10.9 s of the 20 s budget. n = 8 would likely not fit the fast check's budget; not attempted.
- 12:38:0xZ — `POST /proposals/variant` card_six (relation `partial`, relation_proof root → variant, witness `{1..6}`, div-zero acknowledged) → 201, node `variant-e6d83e6d`, **graph PR #188**, `witness_preflight: matched`; card_seven → 201, node `variant-a3b3cb8f`, **graph PR #190**, matched.
- 12:38:26Z — prechecks for card_four and card_five: done pass. Submitted: card_four → **graph PR #191**, card_five → **graph PR #192**.
- 12:38:26Z — `GET /submissions/177|178|183`: gate success, `waiting_on: merge`, `mergeable_state: unknown`. #188/#190 gate in progress.
- 12:39:30Z — `GET /submissions/178` → **`curl: (35) Recv failure: Connection reset by peer`** (second transport reset in 10 min; others in the same loop fine). Not reproduced on retry.
- 12:39:57Z — `POST /annexes` on root `erdos-402` (CC-BY-4.0): the max-element finite-check method, why it cannot reach the root, and pointer to Balasubramanian–Soundararajan (1996) for the general case → 201, **graph PR #193**. Caveat on my own wording: the annex title says "machine-checked for |A| = 3…7"; 3–5 passed the hosted precheck, 6–7 had only passed AXLE's fast check when I wrote it.
- 12:39Z — none of #177/#178/#183 merged yet: gate green, `waiting_on: merge`; the queue also holds others' PRs (#175, #176, #179–#182).
- 12:40Z — `GET /submissions.json`: `tester-402-mcp` submitted proofs of minFac (#181) and large_prime (#182) a minute after my #177 and a few seconds before my #183, and proposed its own variant (#189). Different Lean texts, so no `duplicate-submission`; the loser of each race becomes an alternate. **Wish:** `GET /submissions/<id>` for a proposal shows only ids, not the proposed statement, so I could not check whether #189 duplicates my #188/#190 without going to GitHub.
- 12:40:59Z — proposals #188/#190 gate: success; #190 `clean`/`merge`, #188 `behind`/`branch-update`. My proofs #177/#178 now `behind`/`branch-update`.
- 12:41:10Z — precheck against the pending node `variant-e6d83e6d` → 409 `node-pending`, as the guide says. Small inconsistency: the 409 said `waiting_on: gate` while `GET /submissions/188` 11 s earlier said `branch-update` (probably just moved on in between).
- 12:41–12:45Z — watched my 8 PRs with a 45 s poll. Only one PR in the whole queue (#176) merged between 12:40 and 12:45; 21 open service PRs (#177–#197) remain, mine first in line (#177). All mine are green and cycling `branch-update` → `merge`. At this rate (one merge per ≈3–5 min, oldest first, strictly serial) proposal #188 is ~11 merges back, i.e. it will not merge within my hour, so the card_six/card_seven *proofs* (checked, ready) cannot even be prechecked before I stop (`node-pending`). **Biggest friction of the session:** the serial merge queue, not the gate. **Wish:** allow precheck of a proof against a *pending* proposal's node (the statement is fixed once the proposal's gate is green), so both can be queued together.
- 12:42:58Z — one poll of `GET /submissions/190` returned something that was not JSON (my parser printed `err`); next poll fine. Transient, not reproduced.
- 12:45:31Z — tried card_eight on `/check` (1157-leaf tree, 657 kB) → 413 `content-too-large` "content is 656745 bytes; the limit is 200000" in 0.26 s. Clear, correct message (the limit is not in the guide's `/check` paragraph, though). The generated-case-tree method stops at |A| = 7 here.
- 12:47:32Z — #177 green, oldest open, `waiting_on: merge`, `mergeable_state: unknown` for ~6 min (held, I assume, by #176's post-merge job, as the guide describes); then `gate` again after a branch update (12:49).
- **12:52:47Z — graph PR #177 MERGED: `variant-3377fd96` (minFac variant) proved**, 19m41s after submission, no human involved. Nothing on my side to do.
- 12:55:36Z — 3 min after the merge, `variant-3377fd96` still on `/frontier.json` (products not yet rendered; within the guide's 3–6 min). 12:58:34Z — gone from the frontier; `GET /submissions/177` now carries the attestation (`verdict: pass`, `trust_base: kernel`, submitter `t0924-402-http`, my tooling disclosure).
- 12:54–12:58Z — my poller got a non-JSON/failed read three more times (#193 once, #177 and #178 in the same poll); every manual retry answered 200 in <1.2 s. Intermittent transport trouble between this container and the service (same class as the two `Connection reset by peer` earlier); cannot tell from here whether it is the service or my proxy.
- **13:01:16Z — graph PR #178 MERGED: `variant-6bd06d63` (card_three) proved** (28 min after submission; 8.5 min after #177).
- 13:07:25Z — queue: 26 open service PRs; oldest #179 (another tester's) has been at the head since ~13:01. #188 is 10th in line; I will stop before it merges.

- 13:12:38Z — final poll: #177 and #178 merged; #183, #188, #190, #191, #192 and #193 open with gate success, cycling branch-update/merge. Only #179 merged between 13:01 and 13:12. Stopping new work here. My claims on variant-a874fe93, variant-780e7ade and variant-bc28297c stay until they expire at 14:29–14:31Z, because their PRs are still open. The log is also on draft PR #14 in the network repo.

- Post-session note, 14:14:27Z (no new work done after the 13:20 stop): #181, #182 and #183 had also merged. #183 is my large_prime proof, merged after the other tester's #182, so presumably kept as an alternate. Proposal #188 (card_six, `variant-e6d83e6d`) merged and was waiting on `products`. #190, #191, #192 and #193 were still queued. #188 merged about 96 min after it was proposed. The card_six proof from the appendix can now be prechecked, once products render; I did not submit it, because it came after my time limit.

## Summary

(State as of the final poll recorded just above this section.)

### What landed

| Graph PR | Kind | Node | State at stop |
|---|---|---|---|
| #177 | proof | `variant-3377fd96` (minFac: some x ∈ A has `A.card ≤ x.minFac`) | **merged 12:52Z, proved, attested** |
| #178 | proof | `variant-6bd06d63` (card_three) | **merged 13:01Z, proved** |
| #183 | proof | `variant-a874fe93` (large_prime) | open, green, in merge queue; `tester-402-mcp`'s #182 is ahead of it, so mine will probably become an alternate |
| #191 | proof | `variant-780e7ade` (card_four) | open, green, queued |
| #192 | proof | `variant-bc28297c` (card_five) | open, green, queued |
| #188 | variant proposal (`partial`, with relation proof) | `variant-e6d83e6d` (card_six) | open, green, queued |
| #190 | variant proposal (`partial`, with relation proof) | `variant-a3b3cb8f` (card_seven) | open, green, queued |
| #193 | annex (CC-BY-4.0) | root `erdos-402` | open, green, queued |

### What I proved

- Machine-checked by the gate (hosted precheck pass; #177 and #178 also merged): Graham's gcd statement when A contains an x with minFac x ≥ |A|, when A contains a prime p ≥ |A|, and when |A| = 3, 4 or 5.
- Only through AXLE's fast check, `okay: true` (not prechecked, because the nodes are still pending): |A| = 6 and |A| = 7, as generated case trees (1245 and 2663 lines). **Handoff:** once #188/#190 merge, fetch each node's `Statement.lean` (the service adds the Context import), replace the `sorry` body with the generator's output (script in the appendix: `python3 gen2.py 6` / `7`), then precheck and submit. The same method stops at |A| = 7: |A| = 8 is 657 kB, over `/check`'s 200 kB limit, and would probably hit the 200000-heartbeat cap as well.
- No progress on the root or on `erdos-402--h3-v2`. The hole h3-v2 carries the whole analytic difficulty (Balasubramanian–Soundararajan); I explain this in the annex and did not attempt it, so I filed no postmortem. What I have is partial variants, not a step towards the root.

### Bugs and friction, most important first (network unless marked)

1. **Serial merge queue dominates the wall-clock time.** Green PRs waited 20–28 min to merge (#177: submitted 12:33, merged 12:52; #178: 12:33 → 13:01), and six of my eight green PRs had still not merged at the end of my hour. Proposals block their own proof: a precheck against a pending node gives 409 `node-pending`, so a new variant plus its proof needs two full trips through the queue. Wish: allow a precheck against a proposal whose gate is green, or fast-track appends and proposals.
2. **Heartbeat cap with no escape hatch inside Proof.lean.** The fast check fails a long proof with `(deterministic) timeout … maxHeartbeats (200000)`, counted over the whole declaration. A tactic-level `set_option maxHeartbeats N in` had no effect (reproduced twice). Because helper declarations are refused, a legitimately long case analysis can only be made cheaper. The guide should say so. I don't know whether the gate uses the same limit.
3. **Intermittent transport failures**: `curl: (35) Connection reset by peer` on `POST /precheck` (12:30:00Z) and `GET /submissions/178` (12:39:30Z), plus about 6 failed or non-JSON reads in the 45 s poller (12:42–13:07Z). Every retry succeeded. Could be this container's proxy; not attributable from outside.
4. **Duplicate work by design.** `tester-402-mcp` claimed the same five variants in the same minute and raced two of my proofs (#181 vs #177, #182 vs #183). Claims are advisory and the frontier shows no claim creation times, so neither of us could see who was first. Wish: `created` on each active claim, and a warning in the `POST /claims` response when others already hold active claims.
5. **HTTP-only path: finding the tutorial node.** The guide finds it with `grep` over a clone. It is not on `/frontier.json` (it is proved), so an HTTP-only agent has to guess `targets/tutorial/nodes/tutorial-and-swap` from the raw repository. Wish: name it in `GET /` or `/info.json`.
6. `GET /submissions/<id>` for a proposal does not show the proposed statement, so I could not tell whether another tester's variant (#189) duplicated mine without going to GitHub.
7. Minor: the `node-pending` 409 said `waiting_on: gate` while `GET /submissions/188` 11 s earlier said `branch-update` (it probably changed in between). `/check`'s 200 kB content limit is not in the guide; the 413 message itself is clear.

**What worked well:** the fast check (0.3–11 s, exact environment `lean-4.33.1`, goal dump at errors); tutorial token in under 3 min; prechecks in about 3–4 min; `witness_preflight: matched` on proposals; merges needed no human.

**My own mistakes:** used the old `Nat.dvd_sub'` name (one failed check); the first card_six tree was too expensive (heartbeats); the annex title says "machine-checked for |A| = 3…7" although 6 and 7 had only passed the fast check at that point.

## Appendix: case-tree generator (`python3 gen2.py N` prints the proof body for card N)

```python
import sys
from fractions import Fraction as F
from math import gcd

n = int(sys.argv[1])
M = "A.max' hne"
vals = sorted(
    {F(j, k) for k in range(2, n) for j in range(1, k)}, key=lambda f: (f.denominator, f.numerator)
)
L = 1
for v in vals:
    L = L * v.denominator // gcd(L, v.denominator)


def form(v, x):
    return f"{v.denominator} * {x} = {v.numerator} * {M}"


def win(p, q):
    a, b = int(p * L), int(q * L)
    if a < b:
        a, b, p, q = b, a, q, p
    g = gcd(a, b)
    return (p, q) if a // g >= n else None


def bezout(a, b, g):
    # find c,d >=0 with c*b - d*a = g or d*a - c*b = g
    for c in range(0, 60):
        for d in range(0, 60):
            if c * b - d * a == g:
                return ("cv", c, d)
            if d * a - c * b == g:
                return ("du", c, d)
    raise Exception


out = []
I = "  "


def emit(s, ind):
    out.append(I * ind + s)


emit(f"intro A hA hn", 1)
emit("have hpos : 0 < A.card := by omega", 1)
emit("have hne : A.Nonempty := Finset.card_pos.mp hpos", 1)
emit("have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by", 1)
emit("intro a b h", 2)
emit("rw [le_div_iff₀ (by exact_mod_cast hpos)]", 2)
emit("exact_mod_cast h", 2)
emit(f"have hM : {M} ∈ A := Finset.max'_mem A hne", 1)
emit(f"have hMpos : 0 < {M} := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))", 1)
disj = " ∨ ".join([f"({M}).gcd x * {n} ≤ {M}"] + [form(v, "x") for v in vals])
emit(f"have aux : ∀ x ∈ A, x < {M} →", 1)
emit(disj + " := by", 3)
emit("intro x hx hlt", 2)
emit("have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx))", 2)
emit(f"obtain ⟨k, hk⟩ := Nat.gcd_dvd_left ({M}) x", 2)
emit(f"obtain ⟨j, hj⟩ := Nat.gcd_dvd_right ({M}) x", 2)
emit(f"have hgpos : 0 < ({M}).gcd x := Nat.gcd_pos_of_pos_right _ hxpos", 2)
emit(f"by_cases hkn : {n} ≤ k", 2)
emit("· left", 2)
emit(f"  calc ({M}).gcd x * {n} ≤ ({M}).gcd x * k := Nat.mul_le_mul_left _ hkn", 2)
emit(f"    _ = {M} := hk.symm", 2)
emit("· right", 2)
emit("  have hjk : j < k := by", 2)
emit("    by_contra hh", 2)
emit("    push_neg at hh", 2)
emit(f"    have : ({M}).gcd x * k ≤ ({M}).gcd x * j := Nat.mul_le_mul_left _ hh", 2)
emit("    omega", 2)
emit("  have hj1 : 1 ≤ j := by", 2)
emit("    rcases Nat.eq_zero_or_pos j with h | h", 2)
emit("    · subst h", 2)
emit("      omega", 2)
emit("    · exact h", 2)
ks = list(range(2, n))
emit("  have hk' : " + " ∨ ".join(f"k = {k}" for k in ks) + " := by omega", 2)
emit("  rcases hk' with " + " | ".join("rfl" for _ in ks), 2)
for k in ks:
    js = list(range(1, k))
    emit("  · have : " + " ∨ ".join(f"j = {j}" for j in js) + " := by omega", 2)
    if len(js) == 1:
        emit("    subst this", 2)
        emit("    omega", 2)
    else:
        emit("    rcases this with " + " | ".join("rfl" for _ in js) + " <;> omega", 2)
emit(f"have hle : ∀ x ∈ A, x ≠ {M} → x < {M} :=", 1)
emit(f"fun x hx hxM => lt_of_le_of_ne (Finset.le_max' A x hx) hxM", 2)
emit(f"have he : (A.erase ({M})).card = {n - 1} := by", 1)
emit(f"rw [Finset.card_erase_of_mem hM, hn]", 2)
emit(f"by_cases hw : ∃ x ∈ A, x < {M} ∧ ({M}).gcd x * {n} ≤ {M}", 1)
emit("· obtain ⟨x, hx, -, h⟩ := hw", 1)
emit("  exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩", 1)
emit(f"have forms : ∀ x ∈ A, x ≠ {M} →", 1)
emit(" ∨ ".join(form(v, "x") for v in vals) + " := by", 3)
emit("intro x hx hxM", 2)
emit("rcases aux x hx (hle x hx hxM) with h | h", 2)
emit("· exact absurd ⟨x, hx, hle x hx hxM, h⟩ hw", 2)
emit("· exact h", 2)
emit("have gdvd : ∀ u v c d : ℕ, u.gcd v ∣ c * v - d * u := fun u v c d =>", 1)
emit("Nat.dvd_sub (Dvd.dvd.mul_left (Nat.gcd_dvd_right u v) c)", 2)
emit("  (Dvd.dvd.mul_left (Nat.gcd_dvd_left u v) d)", 2)
emit("have gdvd' : ∀ u v c d : ℕ, u.gcd v ∣ d * u - c * v := fun u v c d =>", 1)
emit("Nat.dvd_sub (Dvd.dvd.mul_left (Nat.gcd_dvd_left u v) d)", 2)
emit("  (Dvd.dvd.mul_left (Nat.gcd_dvd_right u v) c)", 2)
m = n - 2
names = ["p", "q", "r", "s", "t", "w"][:m]
emit(
    f"have subm : ∀ {' '.join(names)} : ℕ, (∀ x ∈ A, x ≠ {M} → "
    + " ∨ ".join(f"x = {nm}" for nm in names)
    + ") → False := by",
    1,
)
emit(f"intro {' '.join(names)} h", 2)
emit(f"have hs : A.erase ({M}) ⊆ {{{', '.join(names)}}} := by", 2)
emit("intro x hx", 3)
emit("rw [Finset.mem_erase] at hx", 3)
emit("have := h x hx.2 hx.1", 3)
emit("simp only [Finset.mem_insert, Finset.mem_singleton]", 3)
emit("exact this", 3)
cardlem = {
    3: "Finset.card_le_three",
    4: "Finset.card_le_four",
    5: "Finset.card_le_five",
    6: "Finset.card_le_six",
}[m]
emit(f"have := (Finset.card_le_card hs).trans {cardlem}", 2)
emit("omega", 2)
for i, v in enumerate(vals):
    emit(f"have f{i} : ∀ x, {form(v, 'x')} → x = {M} * {v.numerator} / {v.denominator} := by", 1)
    emit("intro x h", 2)
    emit("omega", 2)
used = {}


def pairlemma(p, q, pn, qn):
    key = (p, q)
    if key not in used:
        used[key] = f"w{len(used)}"
    return used[key]


cnt = [0]


def rec(i, present, absent, ind):
    # present: list of (v,name)
    for p, pn in present:
        for q, qn in present:
            if p != q and win(p, q) == (p, q):
                wn = pairlemma(p, q, pn, qn)
                emit(f"exact {wn} {pn} h{pn} {qn} h{qn} h{pn}' h{qn}'", ind)
                cnt[0] += 1
                return
    if i == len(vals):
        cnt[0] += 1
        emit("exfalso", ind)
        pv = [pp for pp, _ in present]
        # p : Fin m → ℕ
        items = [f"{M} * {v.numerator} / {v.denominator}" for v in pv]
        while len(items) < m:
            items.append("0")
        emit(f"refine subm {' '.join('(' + it + ')' for it in items)} ?_", ind)
        emit("intro x hx hxM", ind)
        emit("rcases forms x hx hxM with " + " | ".join("h" for _ in vals), ind)
        for v in vals:
            if v in pv:
                idx = pv.index(v)
                inner = f"f{vals.index(v)} x h"
                t = inner
                if idx < m - 1:
                    t = f"Or.inl ({t})"
                for _ in range(idx):
                    t = f"Or.inr ({t})"
                emit(f"· exact {t}", ind)
            else:
                emit(f"· exact absurd ⟨x, hx, h⟩ hN{vals.index(v)}", ind)
        return
    v = vals[i]
    nm = f"u{i}"
    emit(f"by_cases hE{i} : ∃ y ∈ A, {form(v, 'y')}", ind)
    emit(f"· obtain ⟨{nm}, h{nm}, h{nm}'⟩ := hE{i}", ind)
    rec(i + 1, present + [(v, nm)], absent, ind + 1)
    emit(f"· have hN{i} := hE{i}", ind)
    rec(i + 1, present, absent + [v], ind + 1)


pre = len(out)
rec(0, [], [], 1)
tree = out[pre:]
del out[pre:]
for (p, q), wn in used.items():
    a, b = int(p * L), int(q * L)
    g = gcd(a, b)
    kind, c, d = bezout(a, b, g)
    emit(
        f"have {wn} : ∀ u ∈ A, ∀ v ∈ A, {form(p, 'u')} → {form(q, 'v')} → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by",
        1,
    )
    emit("intro u hu v hv hu' hv'", 2)
    emit("refine ⟨u, hu, v, hv, key u v ?_⟩", 2)
    lem = "gdvd" if kind == "cv" else "gdvd'"
    emit(f"have := Nat.le_of_dvd (by omega) ({lem} u v {c} {d})", 2)
    emit("rw [hn]", 2)
    emit("omega", 2)
out.extend(tree)
sys.stderr.write(f"leaves {cnt[0]} lines {len(out)}\n")
print("\n".join(out))
```
