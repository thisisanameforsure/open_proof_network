Documented shape for the `codex-cli` connector (F16-R4), copied 2026-09-24. The docs page was
unreachable and `docs/` in the repository holds redirect stubs, so both files are built from the
source at openai/codex@61e23bc rather than copied from a prose example:

- `config.toml`: every streamable-HTTP server field `codex-rs/config/src/mcp_types.rs` declares
  (`url`, `bearer_token_env_var`, `http_headers`, `env_http_headers`, and the common `enabled`,
  `required`, `startup_timeout_sec`, `tool_timeout_sec`, `enabled_tools`, `disabled_tools`,
  `default_tools_approval_mode`).
- `commands.txt`: the flags of `codex mcp add` in `codex-rs/cli/src/mcp_cmd.rs` (`--url`,
  `--bearer-token-env-var`).
