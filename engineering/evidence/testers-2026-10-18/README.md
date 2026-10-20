# Testers 2026-10-18: five agents on erdos-1094 for one hour

Mike, 2026-10-18: "send 5 agents out to prove any of the open nodes in erdos 1094 for 1 hour. You can use aristotle
or the agents own thinking. Have subagents read notes on what have others tried. At the end have them report any bugs
or feature requests. They should also add a postmortem to the network on what they tried and why it didnt work out.
You verify their bugs, and prioritize them all."

Background subagents of one local session (the lead). Black box: no agent reads the network's source. Each has the
site, the MCP endpoint (`https://api.openproofnetwork.org/mcp`) and the guide (`AGENTS.md` in a fresh graph clone).
Aristotle available through `opn-prove run --preset aristotle` (≈4 concurrent projects across all agents).

| Agent | Pseudonym | Lean |
|---|---|---|
| A | `t1018-a` | free choice, own reasoning first |
| B | `t1018-b` | free choice, own reasoning first |
| C | `t1018-c` | free choice, Aristotle-first |
| D | `t1018-d` | free choice, Aristotle-first |
| E | `t1018-e` | free choice, literature + own reasoning |

Run window: 19:25Z to 20:25Z. Stop starting new work at 20:15Z. Laptop held awake with `caffeinate`.

Logs: `A.md` … `E.md`, files in `A/` … `E/`. Board: `COORDINATION.md`. Verified, prioritised findings: `bugs.md`.
