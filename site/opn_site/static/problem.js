// The problem page's statement graph (F04-T12): clicking a pill selects its statement panel and
// records the choice in the hash (#node=<id>) so it survives reload. Without JavaScript every
// pill is a link to the statement's record page and the root's panel is shown.
(function () {
  "use strict";
  var svg = document.querySelector("svg.dag");
  var panels = Array.prototype.slice.call(document.querySelectorAll(".panel[data-node]"));
  if (!svg || !panels.length) { return; }
  var pills = Array.prototype.slice.call(svg.querySelectorAll("g.node"));

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
    return true;
  }

  pills.forEach(function (g) {
    g.addEventListener("click", function (ev) {
      var id = g.getAttribute("data-node");
      if (select(id)) {
        ev.preventDefault();
        history.replaceState(null, "", "#node=" + encodeURIComponent(id));
      }
    });
  });

  function fromHash() {
    var m = /^#node=(.+)$/.exec(location.hash);
    return m ? decodeURIComponent(m[1]) : null;
  }

  var initial = fromHash() || panels[0].getAttribute("data-node");
  if (!select(initial)) { select(panels[0].getAttribute("data-node")); }
  // T18: a panel's "Superseded by" link is an in-page #node= link, so the hash can change
  // without a pill being clicked.
  window.addEventListener("hashchange", function () {
    var id = fromHash();
    if (id) { select(id); }
  });
})();
