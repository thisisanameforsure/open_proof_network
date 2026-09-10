"""The one config module (conventions §1; C6, C8; F05-R2): what it refuses, and that nothing
else in the api reads the environment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from opn_api import config

PACKAGE = Path(config.__file__).resolve().parent
ENVIRON_READ = re.compile(r"os\.environ|os\.getenv|environ\[|getenv\(")


def test_only_the_config_module_reads_the_environment() -> None:
    """C8: secrets come through one door. A static check, so a new module cannot quietly add
    a second one — the docstring in config.py is the only place the words may appear."""
    offenders = []
    for source in sorted(PACKAGE.glob("*.py")):
        if source.name == "config.py":
            continue
        code = "\n".join(
            line for line in source.read_text().splitlines() if not line.lstrip().startswith("#")
        )
        if ENVIRON_READ.search(code):
            offenders.append(source.name)
    assert offenders == [], offenders


def test_nothing_in_the_api_imports_os_environ_by_name() -> None:
    """`from os import environ` would dodge the regex above; refuse the import form too."""
    for source in PACKAGE.glob("*.py"):
        if source.name != "config.py":
            assert "from os import" not in source.read_text(), source.name


@pytest.mark.parametrize("value", ["0", "-1", "-120"])
def test_non_positive_limits_are_refused_at_load(value: str) -> None:
    """C7: a limit of zero would refuse every write and a negative one is nonsense; both fail
    at load time, never later."""
    with pytest.raises(config.ConfigError, match="positive"):
        config.load({"OPN_API_WRITES_PER_HOUR": value})
    with pytest.raises(config.ConfigError, match="positive"):
        config.load({"OPN_API_CLAIM_TTL_MAX_H": value})


def test_float_and_blank_limits_are_refused() -> None:
    with pytest.raises(config.ConfigError, match="integer"):
        config.load({"OPN_API_ACTIVE_CLAIMS": "1.5"})
    with pytest.raises(config.ConfigError, match="integer"):
        config.load({"OPN_API_STATE_TTL_S": ""})


def test_missing_lists_every_required_secret_in_a_stable_order() -> None:
    """R13: with nothing configured, every id and secret is named, in the order the health
    check will print them; the tables are only required for the dynamodb store."""
    assert config.load({}).missing() == [
        "OPN_API_GITHUB_APP_ID",
        "OPN_API_GITHUB_CLIENT_ID",
        "OPN_API_GITHUB_CLIENT_SECRET",
        "OPN_API_GITHUB_PRIVATE_KEY",
        "OPN_API_TOKEN_SECRET",
    ]
    dynamo = config.load({"OPN_API_STORE": "dynamodb"}).missing()
    assert dynamo[:3] == [
        "OPN_API_TABLE_IDENTITIES",
        "OPN_API_TABLE_TOKENS",
        "OPN_API_TABLE_CLAIMS",
    ]


def test_blank_secret_counts_as_missing() -> None:
    """An empty string in Parameter Store must not pass as configured (C7)."""
    s = config.load({"OPN_API_TOKEN_SECRET": "", "OPN_API_GITHUB_APP_ID": ""})
    assert s.token_secret is None
    assert "OPN_API_TOKEN_SECRET" in s.missing()
    assert "OPN_API_GITHUB_APP_ID" in s.missing()


def test_public_url_trailing_slash_is_normalised() -> None:
    s = config.load({"OPN_API_PUBLIC_URL": "https://api.example.org/"})
    assert s.public_url == "https://api.example.org"


def test_parameter_store_pagination_and_prefix_scoping() -> None:
    """Every page is read, only the known names are kept, and a parameter outside the prefix
    that happens to share a suffix is not mistaken for ours."""

    class Ssm:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def get_parameters_by_path(self, **kwargs: object) -> dict[str, object]:
            self.calls.append(kwargs)
            if "NextToken" not in kwargs:
                return {
                    "Parameters": [{"Name": "/opn/api/token-secret", "Value": "s3cret"}],
                    "NextToken": "page-2",
                }
            return {
                "Parameters": [
                    {"Name": "/opn/api/github-app-id", "Value": "42"},
                    {"Name": "/other/api/github-client-id", "Value": "not-ours"},
                ]
            }

    client = Ssm()
    found = config.load_parameters("/opn/api/", client=client)
    assert found == {"OPN_API_TOKEN_SECRET": "s3cret", "OPN_API_GITHUB_APP_ID": "42"}
    assert len(client.calls) == 2
    assert all(c["WithDecryption"] is True for c in client.calls)
    assert client.calls[1]["NextToken"] == "page-2"


def test_settings_is_immutable() -> None:
    s = config.load({})
    with pytest.raises(AttributeError):
        s.writes_per_hour = 1  # type: ignore[misc]
