// The problem page's statement graph (F04-T12): clicking a pill selects its statement panel and
// records the choice in the hash (#node=<id>) so it survives reload. Without JavaScript every
// pill is a link to the statement's record page and the root's panel is shown.
// F18-T2: a proved problem offers one button per proof. The page is rendered with the first
// proof drawn (its statements .on-proof, the rest .off-proof); a button redraws the graph for
// its proof from each mark's data-proofs list, and the hash keeps both (#proof=<n>&node=<id>).
(function () {
  "use strict";
  var svg = document.querySelector("svg.dag");
  var panels = Array.prototype.slice.call(document.querySelectorAll(".panel[data-node]"));
  if (!svg || !panels.length) { return; }
  var pills = Array.prototype.slice.call(svg.querySelectorAll("g.node"));
  var marks = Array.prototype.slice.call(svg.querySelectorAll("[data-proofs]"));
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".proof-picker button[data-proof]"));
  var notes = Array.prototype.slice.call(document.querySelectorAll(".proof-note[data-proof]"));
  var state = { node: null, proof: buttons.length ? 0 : null };

  function select(id) {
    var found = false;
    panels.forEach(function (p) {
      var on = p.getAttribute("data-node") === id;
      p.hidden = !on;
      if (on) { found = true; }
    });
    if (!found) { return false; }
    pills.forEach(function (g) {
      if (g.getAttribute("data-node") === id) { g.classList.add("selected"); }
      else { g.classList.remove("selected"); }
    });
    state.node = id;
    return true;
  }

  function showProof(k) {
    if (k === null || k < 0 || k >= buttons.length) { return false; }
    var key = String(k);
    marks.forEach(function (el) {
      var on = (el.getAttribute("data-proofs") || "").split(" ").indexOf(key) !== -1;
      el.classList.toggle("on-proof", on);
      el.classList.toggle("off-proof", !on);
    });
    buttons.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-proof") === key ? "true" : "false");
    });
    notes.forEach(function (n) { n.hidden = n.getAttribute("data-proof") !== key; });
    state.proof = k;
    return true;
  }

  function writeHash() {
    var parts = [];
    if (state.proof !== null && buttons.length > 1) { parts.push("proof=" + state.proof); }
    if (state.node) { parts.push("node=" + encodeURIComponent(state.node)); }
    history.replaceState(null, "", parts.length ? "#" + parts.join("&") : location.pathname);
  }

  function fromHash() {
    var out = { node: null, proof: null };
    location.hash.replace(/^#/, "").split("&").forEach(function (part) {
      var m = /^(node|proof)=(.+)$/.exec(part);
      if (!m) { return; }
      if (m[1] === "node") { out.node = decodeURIComponent(m[2]); }
      else if (/^\d+$/.test(m[2])) { out.proof = parseInt(m[2], 10); }
    });
    return out;
  }

  pills.forEach(function (g) {
    g.addEventListener("click", function (ev) {
      if (select(g.getAttribute("data-node"))) {
        ev.preventDefault();
        writeHash();
      }
    });
  });
  buttons.forEach(function (b) {
    b.addEventListener("click", function () {
      if (showProof(parseInt(b.getAttribute("data-proof"), 10))) { writeHash(); }
    });
  });

  var initial = fromHash();
  if (initial.proof !== null) { showProof(initial.proof); }
  if (!select(initial.node || panels[0].getAttribute("data-node"))) {
    select(panels[0].getAttribute("data-node"));
  }
  // T18: a panel's "Superseded by" link is an in-page #node= link, so the hash can change
  // without a pill being clicked.
  window.addEventListener("hashchange", function () {
    var h = fromHash();
    if (h.proof !== null) { showProof(h.proof); }
    if (h.node) { select(h.node); }
  });
})();
