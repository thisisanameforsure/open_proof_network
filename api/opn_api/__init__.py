"""opn_api — the protocol service: HTTP endpoints, precheck runner, MCP adapter (D-28, D-35).

F05 builds the foundation: one Starlette application (``app.py``) over three seams —
``Store`` (DynamoDB), ``GitHost`` (GitHub) and ``Clock`` — with a Lambda handler and a local
runner. The service holds no authority: it opens nothing, signs nothing evidentiary, and is
rebuildable from the graph (D-35, C9).
"""
