"""F34-T45 (REMINDERS-erdos-257 item 20; handoff §3.4.1 item 7): §4 names each steward once.

On erdos-257 each steward's name appeared three times: in the steward card (with a second sentence
naming them again by login and date), in the list under it, and in the panel's member list. Now
the list is the one place a steward is named, with how they were admitted and the day they
committed; the card keeps what a steward commits to and how to join; the panel box lists only each
member's login and last act, and its motions.
"""

from __future__ import annotations

import re
from html import escape

from fixture import STEWARD_NAME, STEWARDED_TARGET
from test_finding_co_stewards import pages  # noqa: F401 — the stewarded fixture's pages


def people(page: str) -> str:
    return page[page.index('id="people"') : page.index('id="known"')]


def test_each_steward_is_named_once_in_section_4(pages: dict[str, str]) -> None:  # noqa: F811
    sec = people(pages[f"problems/{STEWARDED_TARGET}/index.html"])
    assert sec.count(escape(STEWARD_NAME)) == 1, sec.count(escape(STEWARD_NAME))
    stewards = re.search(r'<ul class="stewards">(.*?)</ul>', sec, re.S)
    assert stewards is not None
    assert "committed " in stewards.group(1)
    assert " since " not in re.sub(r"<[^>]+>", "", sec.split('<ul class="stewards">')[0])


def test_the_panel_box_lists_last_acts_not_names(pages: dict[str, str]) -> None:  # noqa: F811
    sec = people(pages[f"problems/{STEWARDED_TARGET}/index.html"])
    members = re.search(r'<ul class="panel-members">(.*?)</ul>', sec, re.S)
    assert members is not None
    assert escape(STEWARD_NAME) not in members.group(1), members.group(1)
