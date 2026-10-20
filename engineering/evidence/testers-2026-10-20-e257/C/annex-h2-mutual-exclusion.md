Mutual exclusion between two open holes on this target (filed as a relation between nodes, since no record type states one).

Node erdos-257--h2 (this node, "the greedy walk for a rational stalls"): for every rational r and every set G of positive integers that is greedy for r and sums to r, G is finite.

Node spec-a70fcca4--h4 ("1/2's walk never stalls", the open hole of the skeleton on spec-a70fcca4, "1/2 is the Mersenne reciprocal sum of some infinite set"): the greedy walk for r = 1/2 runs forever, giving an infinite greedy set that sums to 1/2.

The two cannot both hold, and exactly one of them is true: an infinite greedy set G for 1/2 with sum 1/2 is a counterexample to erdos-257--h2 at r = 1/2, while erdos-257--h2 at r = 1/2 forces every representation of 1/2 to be finite, which is impossible for an even denominator (finite sums of 1/(2^a - 1) have odd denominators), so 1/2 would have no representation at all and spec-a70fcca4--h4 would be false. Consequently:

- a proof of spec-a70fcca4--h4 (equivalently of spec-a70fcca4, through its skeleton) refutes erdos-257--h2 and, with it, the root erdos-257 (the root is false);
- a proof of erdos-257--h2 proves the root through erdos-257--h1 (already proved) and refutes spec-a70fcca4 and its hole --h4.

Neither direction is known. The experts (Kovač, erdosproblems.com/257, 2025) expect the first; the greedy walk for 1/2 has been run to depth 10^8 (Hong 2026, unrefereed) and to 10^6 exactly on 2026-10-20 without stalling.

The network has no record type for "these two open statements are mutually exclusive" and no page shows the relation; this annex is the nearest thing the guide allows. A proof of either will show up only as a status change on its own node, and the refutation of the other will have to be filed by hand as a defect claim with a Lean exhibit.
