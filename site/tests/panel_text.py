"""F04-T48: what a reader sees of a statement panel without opening anything.

``visible_text`` is the panel's text with every closed ``<details>`` reduced to its ``<summary>``
and every element marked ``hidden`` left out, the way a browser shows the panel before a click.
``hrefs`` is every link target in a fragment, for the "nothing is lost" check.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

#: Inline elements join their text to their neighbours'; every other element breaks words.
INLINE = frozenset(
    {"a", "abbr", "b", "code", "em", "i", "kbd", "small", "span", "strong", "sub", "sup"}
)
VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
)


class _Visible(HTMLParser):
    """Each open element is a frame: its tag, whether its own place is hidden (``base``) and
    whether its content is (``eff``). A closed details hides its content but not its summary."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[tuple[str, bool, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID:
            return
        names = {k for k, _v in attrs}
        own = "hidden" in names or tag in ("script", "style")
        parent_tag, parent_base, parent_eff = self.stack[-1] if self.stack else ("", False, False)
        base = parent_eff
        if tag == "summary" and parent_tag == "details":
            base = parent_base  # a closed details still shows its summary
        eff = base or own or (tag == "details" and "open" not in names)
        self.stack.append((tag, base, eff))
        if tag not in INLINE:
            self.out.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        while self.stack:
            if self.stack.pop()[0] == tag:
                break
        if tag not in INLINE:
            self.out.append(" ")

    def handle_data(self, data: str) -> None:
        if not (self.stack and self.stack[-1][2]):
            self.out.append(data)


def visible_text(fragment: str) -> str:
    p = _Visible()
    p.feed(fragment)
    p.close()
    return re.sub(r"\s+", " ", "".join(p.out)).strip()


def word_count(fragment: str) -> int:
    """Words a reader sees: whitespace-separated tokens carrying a letter or a digit."""
    return sum(1 for w in visible_text(fragment).split() if re.search(r"\w", w))


def hrefs(fragment: str) -> set[str]:
    return set(re.findall(r'href="([^"]*)"', fragment))


def unhidden(panel: str) -> str:
    """A panel as it shows once selected: the outer ``hidden`` the script lifts, lifted."""
    head, sep, rest = panel.partition(">")
    return head.removesuffix(" hidden") + sep + rest
