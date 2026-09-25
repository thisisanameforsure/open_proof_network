Documented examples for the `gemini-cli` connector (F16-R4), copied 2026-09-24 from
google-gemini/gemini-cli@87de0b6:

- `settings.json`: the server keys `docs/tools/mcp-server.md` documents (`httpUrl` for streamable
  HTTP, `url` for SSE, `headers`, `timeout`, `trust`, `includeTools`, `excludeTools`) and the
  `context.fileName` example of `docs/cli/gemini-md.md`. `url` is in the documented shape because
  Gemini documents it; the connector forbids it, because it means SSE.
- `commands.txt`: the two literal `gemini mcp add` examples of `docs/tools/mcp-server.md`.
