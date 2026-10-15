import os, pytest
from opn_gate import routes as r
M = os.environ["MUTANT"]
@pytest.fixture(autouse=True)
def _mutate(monkeypatch):
    if M == "no-minimal":
        monkeypatch.setattr(r, "_minimal", lambda options, rows: options)
    elif M == "always-direct":
        orig = r._Enumerator.close
        def close(self, node_id, path):
            self.cut = "any"; return orig(self, node_id, path)
        monkeypatch.setattr(r._Enumerator, "close", close)
    elif M == "no-fallback":
        orig = r._hole_nodes
        def hn(node_id, rows):
            row = rows[node_id]
            return [(str(d.get("partial")), [(str(h.get("name")), r._follow(str(h["node"]), row, rows) if h.get("node") else None) for h in d.get("holes") or []]) for d in row.get("decompositions") or []]
        monkeypatch.setattr(r, "_hole_nodes", hn)
