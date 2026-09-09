"""The deliberately tiny prose renderer (F04-T3; R3, R4; Q2).

Contributor text becomes paragraphs and fenced code blocks; nothing else is interpreted. Every
character is escaped, so no markup a contributor writes survives as markup. Correct and safe
beats pretty at Stage 0 (Q2).
"""

from __future__ import annotations

from html import escape

FENCE = "```"


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
