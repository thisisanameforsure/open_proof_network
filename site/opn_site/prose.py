"""The deliberately tiny prose renderer (F04-T3; R3, R4; Q2).

Contributor text becomes paragraphs and fenced code blocks; nothing else is interpreted. Every
character is escaped, so no markup a contributor writes survives as markup. Correct and safe
beats pretty at Stage 0 (Q2).
"""

from __future__ import annotations

import re
from html import escape

FENCE = "```"
_HEADING_RE = re.compile(r"^(?P<level>#{1,3})\s+(?P<text>.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s+(?P<text>.*)$")
_NUMBERED_RE = re.compile(r"^\d+\.\s+(?P<text>.*)$")
_CONTINUATION_RE = re.compile(r"^\s{2,}(?P<text>\S.*)$")
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_STRONG_RE = re.compile(r"\*\*([^*\n]+)\*\*")


def render(text: str) -> str:
    """Paragraphs separated by blank lines; ``` fences become <pre><code>; all text escaped."""
    out: list[str] = []
    paragraph: list[str] = []
    code: list[str] | None = None

    def flush() -> None:
        if paragraph:
            out.append("<p>" + escape(" ".join(paragraph), quote=True) + "</p>")
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if code is not None:
            if line.strip().startswith(FENCE):
                out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
                code = None
            else:
                code.append(raw)
            continue
        if line.strip().startswith(FENCE):
            flush()
            code = []
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    if code is not None:  # an unclosed fence is still just text
        out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
    return "\n".join(out)


def inline(text: str) -> str:
    """Escaped text with two inline forms: `code` and **strong**. Nothing else is markup."""
    escaped = escape(text, quote=True)
    escaped = _CODE_SPAN_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    return _STRONG_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)


def render_document(text: str) -> str:  # noqa: PLR0915 — one branch per line shape
    """The site's own documents (F10-R9): ``render``'s rules plus headings (``#`` to ``###``),
    bullet and numbered lists with indented continuation lines, and the two inline forms of
    ``inline``. Every character is still escaped; the documents are this repository's, but the
    renderer trusts nothing (F04-R3)."""
    out: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []
    list_tag: str | None = None
    code: list[str] | None = None

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if items and list_tag:
            out.append(
                f"<{list_tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{list_tag}>"
            )
        items.clear()
        list_tag = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if code is not None:
            if line.strip().startswith(FENCE):
                out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
                code = None
            else:
                code.append(raw)
            continue
        if line.strip().startswith(FENCE):
            flush_paragraph()
            flush_list()
            code = []
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group("level"))
            out.append(f"<h{level}>{inline(heading.group('text'))}</h{level}>")
            continue
        bullet = _BULLET_RE.match(line)
        numbered = _NUMBERED_RE.match(line)
        if bullet or numbered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag != tag:
                flush_list()
                list_tag = tag
            match = bullet or numbered
            assert match is not None
            items.append(match.group("text"))
            continue
        continuation = _CONTINUATION_RE.match(raw)
        if continuation and items:
            items[-1] += " " + continuation.group("text")
            continue
        flush_list()
        paragraph.append(line.strip())
    flush_paragraph()
    flush_list()
    if code is not None:  # an unclosed fence is still just text
        out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
    return "\n".join(out)
