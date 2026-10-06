"""F05-T21: the founder revokes an identity's tokens (F05 §7: "Tokens can be revoked by the
founder via a CLI against the store").

    OPN_API_STORE=dynamodb OPN_API_TABLE_IDENTITIES=... OPN_API_TABLE_TOKENS=... \\
    OPN_API_TABLE_CLAIMS=... AWS_PROFILE=... \\
        uv run python api/tools/tokens.py revoke --pseudonym <name>

Every token the identity holds is marked revoked in the tokens table; from the next request the
HTTP routes answer 401 ``invalid-token`` and the MCP verifier knows the bearer no longer. The
identity itself, its claims and its pull requests are untouched: this stops the credential, it
decides nothing about the record (C9).

Settings come from the environment only (``config.load``): the table names and the store kind,
and AWS credentials the way boto3 finds them. No secret is read — revocation needs none, since
the tokens are found by their identity, not by their hash. An in-memory store is refused: it
belongs to one process, and revoking in it would revoke nothing anyone uses.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gate"))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "site")
)  # opn_api.glosses reads opn_site.prose (F22-T5)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from opn_api import config
from opn_api import store as storemod


def revoke(store: storemod.Store, pseudonym: str) -> tuple[storemod.Identity | None, int]:
    """The identity holding ``pseudonym`` and how many of its tokens this revoked."""
    identity = store.get_identity_by_pseudonym(pseudonym)
    if identity is None:
        return None, 0
    return identity, store.revoke_tokens(identity.id)


def main(argv: list[str] | None = None, *, store: storemod.Store | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tokens.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    revoking = commands.add_parser("revoke", help="revoke every token of one identity")
    revoking.add_argument("--pseudonym", required=True, help="the identity's pseudonym (D-19)")
    args = parser.parse_args(argv)

    if store is None:
        settings = config.load()
        if settings.store != "dynamodb":
            print(
                "OPN_API_STORE is not dynamodb: an in-memory store belongs to one process, so "
                "there is nothing to revoke from here",
                file=sys.stderr,
            )
            return 2
        missing = [v for v in settings.missing() if v.startswith("OPN_API_TABLE_")]
        if missing:
            print(f"set {', '.join(missing)}", file=sys.stderr)
            return 2
        store = storemod.build(settings)

    identity, count = revoke(store, args.pseudonym)
    if identity is None:
        print(f"no identity holds the pseudonym {args.pseudonym!r}", file=sys.stderr)
        return 1
    print(f"revoked {count} token(s) of {identity.pseudonym} ({identity.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
