// Words in review (F22-T19, feature request E). A node page is static and takes no input (D-36);
// this script only reads. It asks the network service, whose address the page was rendered with
// (the site's config, never a template), for the open pull requests that carry words for this
// node, and writes "In review: #N by X" into the empty slots beneath the statement's words and the
// explainer. A failed fetch, an answer it cannot read, or no script at all leaves the page exactly
// as rendered. Contributor names are set as text, never as markup; a pull request is linked only
// when its address is on the graph repository the page already links.
(function () {
  "use strict";
  var me = document.currentScript;
  if (!me || !me.dataset || !me.dataset.api || typeof fetch !== "function") { return; }
  var api = me.dataset.api.replace(/\/+$/, "");
  var target = me.dataset.target;
  var node = me.dataset.node;
  var pulls = (me.dataset.repo || "").replace(/\/+$/, "") + "/pull/";
  var slots = document.querySelectorAll(".in-review[data-in-review]");
  if (!slots.length) { return; }
  var url = api + "/submissions.json?node=" + encodeURIComponent(node) + "&kind=words";
  fetch(url, { credentials: "omit" })
    .then(function (resp) { return resp.ok ? resp.json() : null; })
    .then(function (listing) {
      var open = listing && Array.isArray(listing.open) ? listing.open : [];
      Array.prototype.forEach.call(slots, function (slot) {
        var kind = slot.dataset.inReview;
        open.forEach(function (entry) {
          if (!entry || entry.kind !== kind || entry.node_id !== node) { return; }
          if (entry.target_id !== target) { return; }
          var line = document.createElement("p");
          line.appendChild(document.createTextNode("In review: "));
          var number = "#" + String(entry.pr_number);
          var href = typeof entry.pr_url === "string" ? entry.pr_url : "";
          if (pulls !== "/pull/" && href.indexOf(pulls) === 0) {
            var link = document.createElement("a");
            link.setAttribute("href", href);
            link.textContent = number;
            line.appendChild(link);
          } else {
            line.appendChild(document.createTextNode(number));
          }
          line.appendChild(document.createTextNode(" by " + String(entry.pseudonym || "someone")));
          slot.appendChild(line);
          slot.hidden = false;
        });
      });
    })
    .catch(function () { /* the page stays as rendered */ });
})();
