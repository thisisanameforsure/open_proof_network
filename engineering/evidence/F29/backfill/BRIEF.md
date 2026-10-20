# Backfill brief — statement glosses with labels and claims (F29-T8, decisions v3.44)

You are writing the words for a group of statements on the Open Proof Network's live graph: for
each node in your group, one *statement gloss* carrying a **label** (a short name) and opening with
the **claim in notation**. These become the record (attributed to a pseudonym with your model
named, unverified until a steward signs), so write what the Lean says, exactly, and nothing more.

## Where things are (read-only unless named as yours)

- Work list: `/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/bb84009c-aa81-4d0a-9824-92b8a2086c43/scratchpad/backfill/worklist.json`
  — one object per node: `target`, `node`, `status`, `origin`, `hole_name` (the name the hole bore
  in the partial that made it), `parent`, `statement` (the full `Statement.lean`), `context`
  (its `Context.lean`: the signatures of what it may use), `deps`, `lemmas`, `decompositions`,
  `statement_hash_now`, and `glosses` (existing statement glosses with `hash`, `supersedes`,
  `author`, `date`, `lean_hash`, `body`).
- Your group: `.../scratchpad/backfill/groups.json` under the key you were given.
- The live graph checkout, read-only: `.../scratchpad/g/` (`targets/<target>/defs/*.lean` for the
  `Opn.*` definitions a statement names; `targets/<target>/nodes/<node>/annex/*.md` for the prose
  the decomposition came from; `targets/<target>/target.yaml` for the problem's informal statement).
- Your output, yours alone: `.../scratchpad/backfill/drafts/<target>/<node>.md`, one file per node.
- Your running log, yours alone: `.../scratchpad/backfill/log-<group>.md` — append a line per
  node as you finish it (node, label, done/problem). Write it as you go: if you are stopped, the
  log and the drafts are what survives.
- The validator (run it after every few drafts, and at the end until it reports `0 problem(s)`):
  ```
  cd /private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/bb84009c-aa81-4d0a-9824-92b8a2086c43/scratchpad/net
  PYTHONPATH=gate uv run --project /Users/mikehiggins/Desktop/repos/open_proof_network --frozen python ../backfill/validate.py ../backfill/drafts/<target>
  ```
  It names the first problem per draft (label rules, the opening display, the `supersedes` head
  it expects, the schema). Do not edit the validator, the work list, the graph checkout or the
  network repository.

## The draft's form

```
---
label: <at most 60 characters, plain text, no $, one line>
supersedes: <the hash of the node's current head statement gloss, or null>
drafted_with: Claude Fable 5.1 (claude-fable-5-1)
licence: CC-BY-4.0
---
$$<the claim in notation: one display, standard LaTeX that KaTeX renders>$$

<one to three sentences of prose: what the statement says in words, then the conventions the Lean
uses that a reader must know (natural-number division rounds down; Nat.minFac is the least prime
factor; coercions to the reals; an inherited hypothesis named h_… is the earlier hole's claim).>
```

## Rules

1. **Translate, never improve.** The claim is the Lean statement's content in notation: the same
   quantifiers, the same domain (ℕ versus ℝ versus ℤ, with the coercions the Lean has), the same
   hypotheses in the same roles, the same conclusion. A hole's statement often carries earlier
   holes' conclusions as hypotheses (`h_bhp : …`): include them as hypotheses ("if … then …").
   If the Lean is ugly or looks like a mis-generated statement, translate what is written and say
   in the prose how it reads (for example "as written, the division is in ℕ"). Do not guess what
   was meant. Do not state a hoped-for strength.
2. **The label is a name, not a status and not a verdict.** Start from `hole_name` when it is
   descriptive (`h_bhp` → "BHP short-interval primes"; `h_strip` → "the thin strip above k²");
   name the mathematical object or step, not the position ("case k ≥ 6" is fine, "hole 3" is
   not). Keep labels distinct within a target where you can. Under 60 characters.
3. **Math first.** The body opens with exactly one `$$…$$` display on the first line, nothing before
   it. Standard LaTeX only: `\binom`, `\le`, `\ge`, `\mid`, `\nmid`, `\sum`, `\prod`, `\lfloor
   \rfloor`, `\lceil \rceil`, `\mathbb{N}`, `\mathbb{R}`, `\mathbb{Z}`, `\forall`, `\exists`,
   `\Rightarrow`, `\operatorname{minFac}`, `\log`, `\gcd`, `\text{…}` for short words. No custom
   macros, no `\label`, no `\begin{align}` (use `\\` inside a single display only if needed with
   `\begin{aligned}…\end{aligned}`, which KaTeX renders). Keep one display under ~600 characters;
   split a long statement into "if … then …" prose and put the core in the display.
4. **Existing gloss?** If `glosses` is non-empty, this draft *supersedes* its current head (the
   validator tells you the hash). Keep the existing body when it is already math-first and
   faithful, adding only the label; rewrite it only where it is wrong, not math-first, or vague,
   and say nothing about the change in the body.
5. **Prose: one to three sentences.** What it says in words; the conventions. No history, no
   "this node", no status, no references to pull requests. Name people and papers only when the
   statement itself is a named theorem ("Baker–Harman–Pintz").
6. **Read the Lean, the Context and the defs.** `Opn.*` names are defined under `targets/<t>/defs/`.
   The parent's annex (`nodes/<parent>/annex/*.md`) and the partial that made the hole
   (`nodes/<parent>/attempts/*-partial.lean`, read its comment above `have <hole_name>`) tell
   you what the author called it; use that for the label where it is good.

## Finishing

Run the validator until it reports `0 problem(s)` for your target directories. Final report (the
lead reads only this): the group key, the count written, a table of node → label, the nodes where
you were unsure of the translation and why, and anything in the Lean that looks mis-generated
(a claim over ℕ where the parent is over ℝ, a hypothesis that cannot be met). Under 80 lines.
