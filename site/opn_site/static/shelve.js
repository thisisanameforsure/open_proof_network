// Shelve, unshelve or retire from the site (F31-T11; D-14 v3.47). A page is static: a
// statement's page carries one hidden .shelve-act[data-target] slot with the node and, when it is
// shelved, who shelved it, when and why; the problem page carries one hidden
// .retire-act[data-target][data-node][data-partial] per drawn route. Only once session.js has
// the service's answer does this draw anything, and only for a signed-in steward of the target
// or a curator: Shelve opens a small form for the cause and posts
// {node_id, action: "shelved", scope: "node", route: null, cause} to POST /shelvings; Unshelve
// posts the same with action "unshelved"; Retire posts scope "route" with the partial's path.
// On 201 the pull request is shown as the receipt. Signed out, or with the service down,
// nothing is drawn (C7). Every answer is set as text; nothing a person wrote is read back into
// markup.
(function () {
  "use strict";
  var me = document.currentScript;
  if (!window.OPN) { return; }
  var O = window.OPN;
  var el = O.el;
  var pulls = ((me && me.dataset.repo) || "").replace(/\/+$/, "") + "/pull/";

  function receipt(host, text, r) {
    var p = el("span", { "class": "receipt", role: "status" }, " " + text + " ");
    if (r.data && typeof r.data.pr_url === "string" && pulls !== "/pull/" && r.data.pr_url.indexOf(pulls) === 0) {
      p.appendChild(el("a", { href: r.data.pr_url }, "#" + String(r.data.pr_number)));
    }
    host.appendChild(p);
  }

  function post(host, body, done, controls, out) {
    controls.forEach(function (c) { c.disabled = true; });
    O.call("POST", "/shelvings", body).then(function (r) {
      if (r.status === 201) {
        controls.forEach(function (c) { if (c.parentNode) { c.parentNode.removeChild(c); } });
        var form = host.querySelector(".shelve-form");
        if (form) { host.removeChild(form); }
        receipt(host, done, r);
        return;
      }
      out.textContent = O.errorText(r);
      controls.forEach(function (c) { c.disabled = false; });
    }, function () {
      out.textContent = O.errorText(null);
      controls.forEach(function (c) { c.disabled = false; });
    });
  }

  // One control: a button that opens a form for the cause, and a send that posts `shape(cause)`.
  function control(host, label, cue, shape, done) {
    var out = el("span", { "class": "form-error", role: "alert" });
    var b = el("button", { type: "button", "class": "btn btn-ghost btn-small" }, label);
    b.addEventListener("click", function () {
      if (host.querySelector(".shelve-form")) { return; }
      var form = el("div", { "class": "shelve-form ctl-box" });
      form.appendChild(el("p", { "class": "cue" }, cue));
      var cause = el("textarea", { "class": "input", name: "cause", "aria-label": "Your reasoning, published with the record" });
      cause.placeholder = "Why, in your words (published with the record)";
      var send = el("button", { type: "button", "class": "btn btn-secondary btn-small send" }, "File it");
      var cancel = el("button", { type: "button", "class": "btn btn-ghost btn-small" }, "Cancel");
      send.addEventListener("click", function () {
        var words = cause.value.trim();
        if (!words) { out.textContent = "Write the cause first."; return; }
        if (words.length > 1000) { out.textContent = "A cause is at most 1000 characters."; return; }
        out.textContent = "";
        post(host, shape(words), done, host.querySelectorAll("button"), out);
      });
      cancel.addEventListener("click", function () { host.removeChild(form); out.textContent = ""; });
      form.appendChild(cause);
      form.appendChild(send);
      form.appendChild(cancel);
      host.appendChild(form);
    });
    host.appendChild(document.createTextNode(" "));
    host.appendChild(b);
    host.appendChild(out);
  }

  var act = document.querySelector(".shelve-act[data-target]");
  var retires = Array.prototype.slice.call(document.querySelectorAll(".retire-act[data-target]"));
  if (!act && !retires.length) { return; }
  O.session.then(function (s) {
    if (!s.signed_in) { return; }
    function allowed(target) { return s.curator || s.stewards.indexOf(target) >= 0; }
    if (act && allowed(act.dataset.target)) {
      var node = act.dataset.node;
      if (act.dataset.shelved === "1") {
        control(act, "Unshelve",
          "Lift the shelving with a record of your own; the earlier record stays on the record as history.",
          function (cause) { return { node_id: node, action: "unshelved", scope: "node", route: null, cause: cause }; },
          "Unshelving filed:");
      } else {
        control(act, "Shelve",
          "Shelve this statement and every hole beneath it: off the frontier, work refused, hidden from the routes view, until an unshelve record lifts it (D-14 v3.47).",
          function (cause) { return { node_id: node, action: "shelved", scope: "node", route: null, cause: cause }; },
          "Shelving filed:");
      }
      act.hidden = false;
    }
    retires.forEach(function (r) {
      if (!allowed(r.dataset.target)) { return; }
      var node = r.dataset.node;
      var partial = r.dataset.partial;
      control(r, "Retire this route",
        "Retire this decomposition: its holes leave the frontier and the drawing; the statement it sits on is untouched (D-14 v3.47).",
        function (cause) { return { node_id: node, action: "shelved", scope: "route", route: partial, cause: cause }; },
        "Retirement filed:");
      r.hidden = false;
    });
  }).catch(function () { /* no session: the page stays read-only */ });
})();
