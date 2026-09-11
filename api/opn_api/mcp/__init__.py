"""The reference MCP server (F09; D-28): a lens over the git and HTTP path.

One tool per D-28 row, each reproducible with plain git and HTTP (``bijection``), served from
the F05 application at ``/mcp`` (``server``), reading graph files and service endpoints
(``reads``), forwarding writes to their endpoint with the caller's bearer (``writes``), and
wrapping contributor prose as untrusted data (``demarcate``). It holds no state of its own.
"""
