---
name: session-start
description: Run the Open Proof Network build-session start ritual (conventions §6) — read the constitution, find the current feature, read its spec and task ledger, then state the session plan.
---

Run the build-session start ritual, in order:

1. **Read `engineering/specs/constitution.html`** — all non-negotiables. Non-skippable.
2. **Find the current feature**: the first row in `engineering/specs/index.html` whose Status is
   not `done`, respecting dependency order (F00 → F01 → …). If no feature is specced yet, the
   session's job is to draft one — copy `engineering/specs/features/F00-template.html` and work
   from the architecture decisions (`docs/architecture_decisions_v_3_9.html`).
3. **Read that feature's spec** (`engineering/specs/features/FXX.html`) in full — requirements,
   acceptance criteria, tasks.
4. **Read the task ledger**: the **Tasks:** line in the spec's §10 Status block. Cross-check
   against `git log --oneline` (commits named `FXX-Tn:`), `engineering/evidence/FXX/`, and the
   feature's Status cell in `engineering/specs/index.html`. If a task touched the graph repo,
   check `git -C ../open_proof_network_graph log --oneline` for its matching `FXX-Tn:` commit
   too. If they disagree, stop and reconcile — fix the stale doc first.
5. **Check the `## Log` section** in `engineering/CLAUDE.md` for lessons from previous sessions.
6. **State the session plan**: which task(s) this session will do, in dependency order, each with
   its named verification command. Then wait for confirmation before writing code.

Reminders that bind this session (conventions §6 / `engineering/CLAUDE.md`):

- A task is done only when its verification command has run and passed, output captured to
  `engineering/evidence/FXX/`. Commit per verified task (`FXX-Tn: description`), evidence + ledger
  update in the same commit.
- Any commit that changes task state updates the spec's **Tasks:** ledger line AND the feature's
  Status cell in `engineering/specs/index.html` in that same commit.
- `make verify` must pass before any commit (pre-commit hook enforces it).
- Feature complete → tag `FXX-done`, update `engineering/specs/index.html` status, prune `## Log`.
- No drive-by refactors outside the current task's files.
- Specs cite architecture decisions by D-number and never restate or override one.
- This repo is `network`; `../open_proof_network_graph` is `graph` (D-35). Its history is
  mathematics only — specs, evidence and tooling never land there.
