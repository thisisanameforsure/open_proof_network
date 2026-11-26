YOUR SCOPE: every WRITE operation (kind "write" in `search` with no arguments), the auth and kind
rules of the surface, and the legacy surface. You also have a second MCP server, "opn-legacy",
which is the same service's earlier one-tool-per-operation surface (/mcp?surface=v1): for a
sample of operations, check that the legacy tool and the new read/write call answer the same.
Check: a write through `read` and a read through `write` are refused; unknown operation names;
`arguments` missing or not an object; claim_node then release_claim on a claimable frontier node;
check_lean on a small correct and a small broken proof; precheck_submission on the tutorial node
(tutorial-and-swap) and get_precheck until done; every operation with `dry_run`, called dry.
