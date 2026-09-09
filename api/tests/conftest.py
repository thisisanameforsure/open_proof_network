"""Shared fixtures: an app over the memory store, the fake host and the fake clock."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api_fakes import Harness, make_harness


@pytest.fixture
def harness() -> Iterator[Harness]:
    h = make_harness()
    with h.client:
        yield h
