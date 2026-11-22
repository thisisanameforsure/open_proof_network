# 2026-11-13 — erdos-257: the repair walk, and Set 9 on variant-cce9b284

Two sittings in one conversation. The first (2026-10-31) worked through Mike's repair-walk idea
with him; the second (2026-11-13) took "work on this branch, branch #9" and proved five of the six
holes of the skeleton that had been merged on the repair-walk variant that morning.

## Part one: the repair walk, settled with Mike

- The walk is the greedy decoder of the fat Cantor set of subset sums of 1/(2^m - 1). Two readings
  of "subtract the term that failed": one copy per index, under which a failure persists forever
  (the excess over the tail is invariant, because the tail loses the same term the walk takes), so
  the repair set is always a tail and the repair sum a tail of the Erdős–Borwein constant,
  irrational; or the floor rule (take as many copies as fit), the record's rule, under which a run
  of repairs ends at the first index M with t(M) - T(M) at most the excess. Shown on 0.63 step by
  step; Mike took the floor rule.
- Which repair sets S occur: unions of runs of consecutive indices, each ending in a double take,
  with the mass after each run end M below c(M) = gap(M-1) - gap(M); the next run starts past
  roughly 2M. Checked both ways (`realise.py`). The x that realises S is forced when S is infinite.
  For the disproof idea: with finitely many repairs the route is a reduction with nothing gained;
  with infinitely many and multiplicity one the repair sum is itself an infinite subset sum, the
  original question on a sparser family.

## Part two: Set 9

Set 9 on the problem page is the second route on `variant-cce9b284` (graph #1480, merged 13:35Z by
`fable-1113-e257`): six holes claiming 2^-20 is an infinite subset sum because the greedy walk of
2^-20 never stalls. A stall at n is r(n+1) < t(n+1) with the tail after n+1 below r(n+1). The route:
no stall for n <= 1091 (h5, a computation); for n >= 1092 a stall forces a weighted divisor count
W_n(m) above 0.99 for every m in (n, 2n-10] (h3), W_n(m) is at most a walk-free count G_20(m) (h4),
and some m in that interval has G_20(m) <= 0.99 (h6); no stall gives the chosen sum equal to 2^-20
(h7); a finite set cannot sum to 2^-20 (h8).

Read before any Lean: h3, h4, h7, h8 true by elementary arguments (h3 by binary digits: the chosen
sum's digits between m and 2n are forced, so W = J - delta with J an integer and 0 < delta < 2^-11);
h5 true numerically to n = 6000; h6 true numerically to n = 2,000,000 but a prime-constellation
statement (every calm point has m+1 prime and m+2, m+3, m+5 two, three and five times a prime).

Then, through the service as `fable-1113-e257b`: witnesses for all six holes (#1481–#1483, #1486,
#1488, #1489), proofs for h8, h4, h7 (#1484, #1485, #1487), h3 and h5 (submitted by the pipeline once
their witnesses were on the record), and an annex on h6 (#1490) with the numerics and the
obstruction. Evidence: `engineering/evidence/e257-repair-walk-2026-11-13/`.

## Worth keeping

- **A hole's index convention is a fact to read off the statement, not the memory of the
  numerics.** The hole writes r(k+1) for the remainder after term k; my Python wrote r[k]. The
  witness's sixteen walk steps were all off by one, and norm_num said `False` at exactly the take
  steps, which is what pointed at it. The margin computation had used the right convention, so the
  chosen witness survived.
- **The kernel decides a 1092-step walk at 2400 bits in three seconds, if the loop is shallow.**
  `decide` hit the elaborator's recursion limit, `decide +kernel` over a `List.foldl` hit the
  kernel's; a structural loop of 300 steps needs nothing, so h5 runs in eleven chunks of 100 with
  the intermediate states as literals (49 kB of Lean) and a composition lemma. The bridge is one
  invariant: while `ok` holds, the brackets contain 2^2400 times the real remainder and no stall has
  happened; a certain skip checks the bracket's top against a lower bound of the tail,
  2^-k + 4^-(k+1), and `set_option` is never needed.
- **The fast checker's line numbers are offset by the inlined Context** (three lines for these
  nodes). Mapping errors to the file before guessing saved a round each time.
- **A stuck `Decidable` instance inside a `let` is the motive**: `Nat.rec` with the `if` on the
  accumulator needs `(motive := fun _ => ℝ)` and a typed `acc`; `classical` does nothing for it.
- **Which hole is the open core is a question the numerics answer before any proof.** The sieve
  statement h6 was never going to be proved here; proving the other five made that visible on the
  record (the route now rests on h6 alone), and the annex says what a proof needs.
