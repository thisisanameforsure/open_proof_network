"""F14-T33: ``HttpxGitHost.list_tree`` reads the graph's whole tree in one call.

Files are grouped by their directory, as ``list_dir`` names them (files only, sorted); a tree
the host truncated is ``None``, so the caller falls back to listing one directory at a time; a
host failure is a ``GitHostError`` naming the call.
"""

from __future__ import annotations

import pytest
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    REPO,
    Script,
    clock,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)

from opn_api.githost import GitHostError, HttpxGitHost

__all__ = ["clock", "host", "pem", "rsa_key", "script"]  # pytest fixtures

TREE = f"/repos/{REPO}/git/trees/main"


def test_files_are_grouped_by_directory_and_directories_are_not_files(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on(
        "GET",
        TREE,
        json={
            "truncated": False,
            "tree": [
                {"path": "curators.json", "type": "blob"},
                {"path": "targets", "type": "tree"},
                {"path": "targets/t", "type": "tree"},
                {"path": "targets/t/stewards", "type": "tree"},
                {"path": "targets/t/stewards/2.yaml", "type": "blob"},
                {"path": "targets/t/stewards/1.yaml", "type": "blob"},
                {"path": "targets/t/gate-spec.json", "type": "blob"},
                {"path": "vendor/lib", "type": "commit"},  # a submodule is not a file
            ],
        },
    )
    assert host.list_tree(REPO, "main") == {
        "": ["curators.json"],
        "targets/t": ["gate-spec.json"],
        "targets/t/stewards": ["1.yaml", "2.yaml"],
    }
    (sent,) = script.to("GET", TREE)
    assert sent.url.params["recursive"] == "1"


def test_a_truncated_tree_is_none(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on(
        "GET", TREE, json={"truncated": True, "tree": [{"path": "a", "type": "blob"}]}
    )
    assert host.list_tree(REPO, "main") is None


def test_a_tree_that_does_not_say_it_is_whole_is_none(script: Script, host: HttpxGitHost) -> None:
    """No ``truncated`` field is not taken as "whole": the fallback is slower, never wrong."""
    install_app(script).on("GET", TREE, json={"tree": []})
    assert host.list_tree(REPO, "main") is None


def test_a_host_failure_names_the_call(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on("GET", TREE, 502, json={"message": "Bad gateway"})
    with pytest.raises(GitHostError, match=r"git/trees/main returned 502"):
        host.list_tree(REPO, "main")
