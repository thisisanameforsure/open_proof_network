"""Pair each annex label in two renders by the annex file it was rendered from; report growth."""

import re
import sys
from pathlib import Path

LABEL = re.compile(r'<p class="label">(Untrusted: annex \(D-31\).*?)</p>', re.S)
FILE = re.compile(r'Rendered from <a class="file" href="[^"]*">([^<]*)</a>')


def labels(site: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for page in site.rglob("*.html"):
        for lab in LABEL.findall(page.read_text(encoding="utf-8")):
            m = FILE.search(lab)
            assert m, lab
            text = re.sub(r"<[^>]+>", "", lab)
            prev = out.setdefault(m.group(1), text)
            assert prev == text, (m.group(1), prev, text)
    return out


a, b = labels(Path(sys.argv[1])), labels(Path(sys.argv[2]))
assert a.keys() == b.keys(), a.keys() ^ b.keys()
changed = {k for k in a if a[k] != b[k]}
print(f"annexes: {len(a)}; labels changed: {len(changed)}")
for k in sorted(changed):
    old, new = a[k], b[k]
    grew = len(new) > len(old) and ",," not in new
    print(f"  {'grew' if grew else 'CHECK'} {len(old)}->{len(new)} {k.rsplit('/', 3)[1]}")
print("double commas before:", sum(",," in v for v in a.values()), "after:",
      sum(",," in v for v in b.values()))
