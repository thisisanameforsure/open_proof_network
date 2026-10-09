# Testers 2026-10-09b: one agent on erdos-1094 for one hour, MCP entry, told to solve it

Mike: "send 1 agent to work on erdos 1094 for 1 hour using MCP. tell them to solve it. At the end of
their session have them report any bugs. You validate the bugs and prioritize and report back to me."

Second run of the day on this target (the first, two agents at 12:40Z, is `../testers-2026-10-09/`).
The agent is a background subagent of the lead session with no view of the network's source: it does
not read `gate/`, `api/` or `site/`. It has the site, the MCP server (JSON-RPC over curl) and the guide
(`AGENTS.md` in a fresh graph clone). HTTP only where the MCP has no tool, and each such call is a finding.

Pseudonym `t1009-c`. Log: `C.md`, written as it goes; Lean and receipts in `C/`. Verified findings: `bugs.md`.
