# Testers 2026-10-09b: erdos-1094, one agent told to solve it; verified findings

One black-box agent (`t1009-c`) worked through the MCP from 14:19Z to about 15:30Z (its last reads and
claim releases fell past the hour on this laptop's connect stalls). Its log is `C.md`; Lean, receipts and
texts are in `C/` (scanned for tokens and nonces: only content hashes and the gate's public signature).
Every finding below was checked by the lead against the graph history, the post-merge job's own log, the
live service or the network source at `main` (b4e4817 is the live pin).

## What landed

Seven graph pull requests merged, none needing a human: #477 (annex on `--h2--h1`), #478 (skeleton on
`--h2--h1`, child `--h2--h1--h1` born 14:47), #479 (skeleton on `--h3`, see finding 1), #480 (literature
`known` on `--h2--h1--h1`, waiting on a steward or curator), #481 (gloss), #482 (circular-decomposition
claim on `--h2--h1--h1`, ancestor `--h2--h1`), #483 (explainer for the #478 partial).

Nothing new is proved. The agent's own reading is right: the open holes are Ecklund's conjecture
(`--h2--h2`, n ≥ k³) and the residue form (`--h3--h1--*`), and Mathlib's only prime-gap tool is Bertrand.
What it added is structure: Konyagin's g(k) > k³ is now one literature node, so one formalisation of an
explicit bound closes `--h2--h1`. It does **not** close `--h3`, which is finding 1.

## Ranked

1. **C1, HIGH. A partial whose only hole restates a node under another branch merges, earns an attestation,
   and changes nothing on the record; nothing says so.** Confirmed, and it is the design meeting a case the
   design did not price.
   - **Record:** #479's merge commit `d1620beb2` adds only the attempt and its witness. The bot commit
     `4ed6ae5d8` adds `attestations/000479.json` (verdict `pass`) and the ledger line. `--h3`'s `META.yaml`
     still has `deps: [erdos-1094--h3--h1]`; no `--h3--h2` exists.
   - **Job log (run 37947404125):** the writer printed
     `{"partial": {"children": [], "holes": [{"name": "h_good_below_cube", "child": null, "reused_node":
     "erdos-1094--h2--h1--h1"}]}}`. The extractor found the hole definitionally equal to `--h2--h1--h1`.
   - **Code:** `gate/opn_gate/postmerge.py:631-640`. A reused node that is not the parent's own hole child adds
     no edge: "the restatement is recorded in the verdict's placement and nowhere else." That is F07-R22
     (D-12 v3.19, Q29: a decomposition never blocks the node it decomposes, and a hole that restates any
     other sibling adds no edge). Nothing consumes `placed` but the run log (grep: no reader in gate, api or
     tools), so no product, `get_submission 479` or `get_node --h3` can show it.
   - **Why it is HIGH:** the merged assembly is dead. `--h3`'s `Context.lean` carries only its deps, a proof
     cannot add an import, so even once `--h2--h1--h1` is proved no proof of `--h3` can draw on it, and no
     derivation closes `--h3`. The attempt counts, the attestation says pass, the agent read "merged, ok,
     no problems" six times over 37 minutes and had to infer the loss from an unchanged `deps`. The owner's
     Q22 principle applies: a pull request that can change nothing should be refused before it opens.
   - **Precheck:** the receipt said `restates: null`, which was true when it ran (the child did not exist
     until 14:47; #479 was opened at 14:38). Restatement is decided at the merge, by the gate's step 4 against
     the tree as it is then, so the precheck cannot promise the placement.
   - **Guide:** AGENTS.md line 1303 says "A hole that restates a node that already exists is that node: a
     file for it is checked and not written" and does not say that no edge is added outside the parent's
     own children.
   - **Fix options (the second is the owner's):**
     - (a) Refuse, at the gate's step 4 and in the service's pre-flight, a partial every one of whose holes
       restates a node that is neither new nor the parent's own child (`partial-adds-nothing`), and publish
       `placed` in the attestation or `get_submission` so a mixed case is legible. Guide sentence beside it.
     - (b) Let the parent draw on a restated sibling: a cross-branch entry in `deps` with a hole's standing
       (R22's "lemma the parent may draw on once proved, never waited on"). That is a D-12 amendment and
       changes what `Context.lean` carries; it is what the agent assumed the network already did.
2. **C2, MEDIUM. The server's `initialize` instructions name the tutorial node in a form no tool accepts.**
   Confirmed. `api/opn_api/mcp/auth.py:35-47` builds "the tutorial node `<target>/<node>`"
   (`tutorial/tutorial-and-swap`); every tool's `node_id` is `^[a-z0-9][a-z0-9-]*$`, so
   `get_node {node_id: "tutorial/tutorial-and-swap"}` is `arguments-invalid`. Fix: name the node id and the
   target separately in the phrase.
3. **C3, MEDIUM. `list_words_needed` cannot be answered by `submit_gloss` without a hash it does not give.**
   Confirmed. An explainer entry (`gate/opn_gate/glosses.py:893-902`) carries `kind`, `node`, `reason`,
   `file` and `outline`; the only place the artifact hash appears is inside the `outline` path. The
   `submit_gloss` subject for an explainer is `{kind: proof, node_id, proof: <64-hex>}`
   (`api/opn_api/mcp/writes.py:608-622`) and its description never says `proof` is that hash. Two 400s to
   learn it. Fix: add `lean_hash` to each words-needed entry and one clause to the subject description.
4. **C4, LOW. `get_my_submissions` reports `waiting_on: null` for a submission nobody has read yet.** Confirmed
   by design: `pending.last_read` (`api/opn_api/pending.py:501-507`) returns the per-id cache "and never a read
   of its own", so a pull request the service itself just opened shows `null` until some `get_submission`
   populates it. Fix: seed the cache on creation, or label the null (`not-yet-read`).
5. **C5, LOW (documentation). An anonymous `check_lean` record cannot be read with a token later.** By
   design (`api/opn_api/checks.py:2873-2880`, R10: an anonymous call names no identity). The guide does not
   say it; the agent learned it from a 404. One guide sentence.
6. **C6, LOW (wording). A node on `main` whose products are not rendered answers `404 node-unknown` from
   `get_node`.** Confirmed; the message names the post-merge job and the three-to-six-minute window, and
   yesterday's A log read it the same way. The service has a `409 products-pending` shape for the routes that
   take a proposal (`pending.py:170-176`); `get_node` reads the products and does not consult it. Low: the
   message is accurate, the status is the surprise.
7. **C7, duplicate. `file_defect_claim` answered `exhibit_preflight: skipped` for a circularity claim** while
   the description says the exhibit is compiled first. Yesterday's B1 (F13-Q23, known gap), not re-ranked.

## Not bugs

- **Bug 3 (defect-claim schema has no `circular-decomposition`):** `get_schema`'s own description says a
  circular claim is written as `defect-claim/v3` and every other class as v1; the agent read v1 and v2.
  v3 has the class and `ancestor` (`gate/schemas/defect-claim/v3.json:37,124`).
- **Bug 6 (explainer sections):** the `text` description says "in ## sections each naming the outline steps
  it covers"; the refusal `explainer-invalid` was right.
- **Bug 10 (`include: ["statement"]` refused):** `include` names prose sections; the statement is in every
  answer, as the description says.
- **Bug 11:** the laptop's path (19 and 35 s connects, a DNS failure, one 22-minute stall). Not the service.

## Features (from C.md)

- `get_submission` for a merged partial should say what the post-merge job did: holes created, holes
  matched to existing nodes, edges added. (This is C1's visibility half.)
- `list_words_needed` entries should carry the explainer subject's hash (C3).
- A `whoami` read.
- Frontier filters for "no literature status yet" and for `circular` labels.
- Precheck receipt: `job_id` and `nonce` at one level.
