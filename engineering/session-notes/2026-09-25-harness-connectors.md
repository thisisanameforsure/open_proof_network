# 2026-09-25 — harness connectors (F16) and the prover client (F17), built overnight

The owner merged the specs (network PR #13) and said "keep going" before sleeping. This note says
what was built, what it found, and what waits on the owner. Everything is on network PR #22,
test-first. Nothing touched the graph, nothing deployed, and no credential was used.

## What is built

**F16, connectors for coding agents** (T2–T8):

- The registry: `gate/clients/registry.yaml`, with Claude Code, Codex CLI, Gemini CLI, Copilot and
  Cursor.
- Level 1, static checks: each snippet against a dated copy of its harness's own documentation,
  with six research traps written in as mutants; all 30 tools against every harness's limits; the
  guide table and the Docs cards rendered from the registry; the gate shown blind to the declared
  harness.
- Level 2: the real harness binaries against the real api on loopback, decided by the server's
  own record.
- The `verify-harness` CI job and a weekly drift workflow.

**F17, the prover client `opn-prove`** (T2–T7, T9, T6 in part, T8 in part): one standard-library
file.

- `export` is byte-equal to what `/check` forwards.
- `import` is judged against an 18-shape answer corpus by the gate's own step-2 function.
- The whole chain runs against the real service.
- The site serves the client with a checksum, and the guide runs the chain.
- The drift measurement (T9), and the `whole-file` preset for OpenAI-compatible endpoints.

## What the tests found (the part worth reading)

1. **A harness's word is not a connection.**
   - `codex mcp list` and `codex doctor` connect to nothing. Only `codex exec` connects, and it
     does so before its first model call, so a placeholder key is enough to test the MCP side.
   - `copilot mcp list` prints config only.
   - Claude Code exits 0 while skipping a malformed entry.
   - Every level-2 verdict is therefore the server's record of `initialize` and `tools/list`.
2. **Gemini disables every MCP server in an untrusted folder**, user-level ones included. Its
   snippet's check trusts the folder, and the Docs card says so.
3. **Claude Code, Codex and Gemini all expand `$OPN_TOKEN` into the Authorization header.**
   Gemini's docs never said so; the server saw exactly the token that was in the environment.
   This answers half of F16-Q3. The other half, the cost of restarting after `get_token`, needs
   a real model (level 3).
4. **A committed `.mcp.json` waits at "Pending approval" in Claude Code** until someone runs
   `claude` interactively. The tested token form is `claude mcp add --header '... ${OPN_TOKEN}'`.
5. **`list_frontier` would pass Claude Code's 25,000-token result cap at about 142 entries.** The
   live frontier had 38 on 2026-09-25 (read-only probe). The fix is a paging argument, which is a
   D-28 change (F16-Q12).
6. **About a third of a Lean 4.9 prover's correct proofs break at our 4.33.1.** 47 of 73
   DeepSeek-Prover-V2 miniF2F solutions elaborate unchanged. The breaks are mostly mechanical:
   8 renames, 6 cases of `∑ i in` becoming `∑ i ∈`, 6 lines left with no goal after a stronger
   tactic (F17-Q11).
7. **`import` rescues 5 of 9 complete-proof answers** that the gate would refuse if pasted
   verbatim, and every accepted proof is byte-identical to the node's real `Proof.lean`.

## For the owner

| | Decision |
|---|---|
| F16-Q3 | A write tool accepting the token as an argument too (D-28). Headers work in three harnesses; Cursor's reported header drop is untested. |
| F16-Q4 | A one-line `CLAUDE.md` (`@AGENTS.md`) in the graph (D-35), or the snippet's first-line pointer only. |
| F16-Q5 | Model keys in CI for level 3 (new C8 secrets), or level 3 run by hand. |
| F16-Q12 | Paging on `list_frontier` before about 140 entries (D-28). |
| F17-Q6 | Aristotle's terms against the DCO, before the `aristotle` preset ships. |
| F17-Q11 | Ship `whole-file` now, with the caveat that a third of proofs break at the pin, or after a repair round. |

Also left for the owner or for CI:

- F16-T9 and T10: a real model and a fresh agent in each harness. Both spend model credentials.
- F17-T8's live model run: it needs a GPU-served prover.
- F17-T6's on-ramp half: it needs the Mathlib checkout, so CI's Lean tier has it.
- The graph's copy of `AGENTS.md` changes at the next copy, which is the owner's.

## How this container reached things

- The harness CLIs came from npm; the proxy allows it.
- Lean 4.33.1 came from the GitHub release, linked into elan with `elan toolchain link` after
  elan came from its own GitHub release. elan's own host answers 502 at times; retry.
- A Docker image build cannot reach Debian's mirrors through the proxy, so the harness image is
  pinned and built by CI's `npm ci` path instead.
- arXiv, Hugging Face and several vendor sites are refused. That is why Cursor's facts are
  unverified.
